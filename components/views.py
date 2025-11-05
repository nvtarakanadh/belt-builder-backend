from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django.conf import settings
from pathlib import Path
import os
import logging
from django.db.models.signals import post_save
from .signals import handle_component_post_save

logger = logging.getLogger(__name__)

from .models import Component, ComponentCategory, ConnectionPoint
from .serializers import (
    ComponentSerializer, ComponentCategorySerializer,
    ComponentUploadSerializer, ConnectionPointSerializer
)
from cad_processing.utils import process_cad_file

# Try to import Celery task for async processing
try:
    from .tasks import process_component_async
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False


class ComponentCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for component categories"""
    queryset = ComponentCategory.objects.all()
    serializer_class = ComponentCategorySerializer
    pagination_class = None


class ComponentViewSet(viewsets.ModelViewSet):
    """Simplified components API"""
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category (support both legacy id and new label)
        category = self.request.query_params.get('category', None)
        if category:
            # Accept both friendly UI labels and our internal choices; ignore unknowns
            if queryset.filter(category_label=category).exists():
                queryset = queryset.filter(category_label=category)
        
        # Filter by processing status
        status_filter = self.request.query_params.get('processing_status', None)
        if status_filter:
            queryset = queryset.filter(processing_status=status_filter)
        
        # Search by name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action in ['upload', 'upload_component']:
            return ComponentUploadSerializer
        return ComponentSerializer
    
    @action(detail=False, methods=['post'], url_path='upload_component', parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """
        Upload a new component with GLB/GLTF file; extracts geometry data.
        Only GLB/GLTF files are accepted (no CAD conversion needed).
        """
        serializer = ComponentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file extension
        uploaded_file = request.FILES.get('original_file')
        if not uploaded_file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_ext = Path(uploaded_file.name).suffix.lower()
        if file_ext not in settings.CAD_ALLOWED_EXTENSIONS:
            return Response(
                {'error': f'Invalid file type. Allowed: {", ".join(settings.CAD_ALLOWED_EXTENSIONS)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size
        if uploaded_file.size > settings.CAD_UPLOAD_MAX_SIZE:
            return Response(
                {'error': f'File too large. Maximum size: {settings.CAD_UPLOAD_MAX_SIZE / (1024*1024)} MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if async processing is requested and available
        use_async = request.data.get('async', 'false').lower() == 'true' and CELERY_AVAILABLE
        
        try:
            with transaction.atomic():
                component = serializer.save(processing_status='pending' if use_async else 'processing')
            
            if use_async:
                # Process asynchronously with Celery
                process_component_async.delay(component.id)
                component.processing_status = 'processing'
                component.save()
            else:
                # Process synchronously - disable signal to avoid double processing
                post_save.disconnect(handle_component_post_save, sender=Component)
                try:
                    # Process synchronously
                    with transaction.atomic():
                        # Save uploaded file temporarily for processing
                        temp_file_path = Path(settings.MEDIA_ROOT) / 'temp' / f'{component.id}_{uploaded_file.name}'
                        temp_file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(temp_file_path, 'wb+') as temp_file:
                            for chunk in uploaded_file.chunks():
                                temp_file.write(chunk)
                        
                        try:
                            # Process GLB file (no conversion needed)
                            # Since we're uploading GLB directly, we can use the original file
                            # But we still need to extract geometry and save a copy for glb_file field
                            glb_output_path = Path(settings.MEDIA_ROOT) / 'components' / 'glb' / f'{component.id}.glb'
                            glb_output_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            process_result = process_cad_file(
                                temp_file_path,
                                extract_geometry=True,
                                copy_glb_to=str(glb_output_path)
                            )
                            
                            geometry_data = process_result.get('geometry_data', {})
                            bbox = geometry_data.get('bounding_box', {})
                            center = geometry_data.get('center', {})
                            component.bounding_box = bbox
                            component.center = {'x': center[0], 'y': center[1], 'z': center[2]} if isinstance(center, list) else center
                            component.volume = geometry_data.get('volume', 0.0)
                            
                            # Save GLB file properly using Django FileField
                            # Use the copied GLB file or the original if it's already GLB
                            glb_file_path = None
                            if process_result.get('glb_path') and Path(process_result['glb_path']).exists():
                                glb_file_path = Path(process_result['glb_path'])
                            elif temp_file_path.exists() and temp_file_path.suffix.lower() in ['.glb', '.gltf']:
                                # Original file is already GLB, use it
                                glb_file_path = temp_file_path
                            
                            if glb_file_path and glb_file_path.exists():
                                with open(glb_file_path, 'rb') as glb_file:
                                    component.glb_file.save(
                                        f'{component.id}.glb',
                                        glb_file,
                                        save=False  # Don't save yet, we'll save after setting other fields
                                    )
                                logger.info(f"GLB file saved for component {component.id}: {component.glb_file.name}")
                            else:
                                logger.warning(f"GLB file not found for component {component.id}")
                            
                            # Auto-fill mountable_sides and compatibility via rules
                            from .utils import COMPONENT_PLACEMENT_RULES
                            rules = COMPONENT_PLACEMENT_RULES.get(component.category_label, {})
                            component.mountable_sides = rules.get('mountable_sides', [])
                            component.supported_orientations = rules.get('supported_orientations', ['fixed'])
                            component.compatible_types = rules.get('compatible', [])
                            
                            component.processing_status = 'completed'
                            component.save()
                            
                        except Exception as e:
                            component.processing_status = 'failed'
                            component.processing_error = str(e)
                            component.save()
                            raise
                        
                        finally:
                            # Clean up temp file
                            if temp_file_path.exists():
                                os.remove(temp_file_path)
                finally:
                    # Re-enable signal
                    post_save.connect(handle_component_post_save, sender=Component)
            
            # Return created component
            response_serializer = ComponentSerializer(component, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': f'Error processing file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    @action(detail=False, methods=['get'])
    def placement_suggestions(self, request):
        comp_type = request.query_params.get('component')
        if not comp_type:
            return Response({'error': 'component parameter is required'}, status=400)
        from .utils import COMPONENT_PLACEMENT_RULES
        rules = COMPONENT_PLACEMENT_RULES.get(comp_type, {})
        sides = rules.get('mountable_sides', ['bottom'])
        suggestions = []
        # Simple default snap positions relative to origin
        for side in sides:
            if side == 'bottom':
                coord = [0, 0, -5]
            elif side == 'top':
                coord = [0, 5, 0]
            else:
                coord = [0, 0, 0]
            suggestions.append({'side': side, 'coordinates': coord})
        return Response({'component': comp_type, 'suggested_positions': suggestions})

