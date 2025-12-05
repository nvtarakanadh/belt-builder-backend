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
    
    def update(self, request, *args, **kwargs):
        """
        Update component, including handling original_file and glb_file updates.
        When original_file is updated, regenerate GLB file and geometry data.
        When glb_file is updated directly, use it without processing.
        """
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        
        # Check if files are being updated
        uploaded_original_file = request.FILES.get('original_file')
        uploaded_glb_file = request.FILES.get('glb_file')
        original_file_updated = uploaded_original_file is not None
        glb_file_updated = uploaded_glb_file is not None
        
        # Handle GLB file upload (optional, direct upload)
        if glb_file_updated and not original_file_updated:
            # Direct GLB file upload - just save it without processing
            file_ext = Path(uploaded_glb_file.name).suffix.lower()
            if file_ext not in ['.glb', '.gltf']:
                return Response(
                    {'error': 'GLB file must be a .glb or .gltf file'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if uploaded_glb_file.size > settings.CAD_UPLOAD_MAX_SIZE:
                return Response(
                    {'error': f'File too large. Maximum size: {settings.CAD_UPLOAD_MAX_SIZE / (1024*1024)} MB'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update name and category_label if provided
            if 'name' in request.data:
                instance.name = request.data['name']
            if 'category_label' in request.data:
                instance.category_label = request.data['category_label']
            
            # Save the GLB file directly
            instance.glb_file = uploaded_glb_file
            instance.save(update_fields=['name', 'category_label', 'glb_file'])
            
            # Return updated component
            response_serializer = ComponentSerializer(instance, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        # Handle original file upload (processes and generates GLB)
        if original_file_updated:
            # Validate file extension
            file_ext = Path(uploaded_original_file.name).suffix.lower()
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
            
            # Process the file update synchronously
            post_save.disconnect(handle_component_post_save, sender=Component)
            try:
                with transaction.atomic():
                    # Update name and category_label if provided
                    if 'name' in request.data:
                        instance.name = request.data['name']
                    if 'category_label' in request.data:
                        instance.category_label = request.data['category_label']
                    
                    # Save the original_file and other fields
                    instance.original_file = uploaded_original_file
                    instance.processing_status = 'processing'
                    instance.processing_error = None
                    instance.save(update_fields=['name', 'category_label', 'original_file', 'processing_status', 'processing_error'])
                    
                    # Process the new file
                    temp_file_path = Path(settings.MEDIA_ROOT) / 'temp' / f'{instance.id}_{uploaded_original_file.name}'
                    temp_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(temp_file_path, 'wb+') as temp_file:
                        for chunk in uploaded_original_file.chunks():
                            temp_file.write(chunk)
                    
                    try:
                        # Process CAD file and regenerate GLB
                        glb_output_path = Path(settings.MEDIA_ROOT) / 'components' / 'glb' / f'{instance.id}.glb'
                        glb_output_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        process_result = process_cad_file(
                            temp_file_path,
                            extract_geometry=True,
                            copy_glb_to=str(glb_output_path)
                        )
                        
                        geometry_data = process_result.get('geometry_data', {})
                        bbox = geometry_data.get('bounding_box', {})
                        center = geometry_data.get('center', {})
                        instance.bounding_box = bbox
                        instance.center = {'x': center[0], 'y': center[1], 'z': center[2]} if isinstance(center, list) else center
                        instance.volume = geometry_data.get('volume', 0.0)
                        
                        # Update GLB file
                        glb_file_path = None
                        if process_result.get('glb_path') and Path(process_result['glb_path']).exists():
                            glb_file_path = Path(process_result['glb_path'])
                        elif temp_file_path.exists() and temp_file_path.suffix.lower() in ['.glb', '.gltf']:
                            # Fallback: Original file is already GLB/GLTF, use it
                            glb_file_path = temp_file_path
                        
                        if glb_file_path and glb_file_path.exists():
                            with open(glb_file_path, 'rb') as glb_file:
                                instance.glb_file.save(
                                    f'{instance.id}.glb',
                                    glb_file,
                                    save=False
                                )
                            logger.info(f"GLB file updated for component {instance.id}: {instance.glb_file.name}")
                        else:
                            logger.warning(f"GLB file not found for component {instance.id}. Conversion may have failed.")
                        
                        instance.processing_status = 'completed'
                        instance.save()
                        
                    except Exception as e:
                        error_message = str(e)
                        instance.processing_status = 'failed'
                        instance.processing_error = error_message
                        instance.save()
                        logger.error(f"Component update processing failed: {error_message}", exc_info=True)
                        return Response(
                            {'error': f'Error processing file: {error_message}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                    finally:
                        # Clean up temp file
                        if temp_file_path.exists():
                            os.remove(temp_file_path)
            finally:
                # Re-enable signal
                post_save.connect(handle_component_post_save, sender=Component)
            
            # Return updated component
            response_serializer = ComponentSerializer(instance, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            # Standard update without file change
            return super().update(request, *args, **kwargs)
    
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
        Upload a new component with CAD file (GLB/GLTF, STEP, STL, OBJ).
        Extracts geometry data and converts to GLB for web visualization.
        
        STEP files are converted using FreeCAD Docker (deployment-friendly).
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
        
        # Check STEP file conversion availability
        if file_ext in ['.step', '.stp']:
            # Check if STEP conversion is available
            step_conversion_available = False
            
            # Check for pythonocc-core
            try:
                from OCC.Core.STEPControl_Reader import STEPControl_Reader
                step_conversion_available = True
            except ImportError:
                pass
            
            # Check for FreeCAD Docker
            if not step_conversion_available:
                freecad_docker_url = getattr(settings, 'FREECAD_DOCKER_URL', None)
                if freecad_docker_url:
                    try:
                        import requests
                        response = requests.get(f"{freecad_docker_url}/health", timeout=2)
                        if response.status_code == 200:
                            step_conversion_available = True
                    except:
                        pass
            
            # Check for Docker command (for FreeCAD Docker subprocess)
            if not step_conversion_available:
                try:
                    import subprocess
                    subprocess.run(['docker', '--version'], capture_output=True, check=True, timeout=2)
                    # Docker is available, but we still need the FreeCAD image
                    # This is not a guarantee, but we'll let it try
                    step_conversion_available = True
                except:
                    pass
            
            if not step_conversion_available:
                return Response(
                    {
                        'error': 'STEP file conversion is not available',
                        'message': (
                            'STEP file conversion requires pythonocc-core or FreeCAD Docker, which are not currently available.\n\n'
                            'SOLUTIONS:\n'
                            '1. Use Docker (Recommended):\n'
                            '   docker build -f Dockerfile.converter -t step-converter:latest .\n'
                            '   docker run -d -p 8001:8001 --name freecad-service step-converter:latest\n'
                            '   Then set FREECAD_DOCKER_URL=http://localhost:8001 in your environment\n\n'
                            '2. Use Python 3.10-3.12:\n'
                            '   Install Python 3.12, create a new virtual environment, and install pythonocc-core\n\n'
                            '3. Pre-convert STEP files:\n'
                            '   Convert your STEP file to STL or OBJ using FreeCAD (free): https://www.freecad.org/\n'
                            '   Then upload the STL or OBJ file instead.\n\n'
                            'For detailed instructions, see: backend/INSTALL_PYTHONOCC.md'
                        ),
                        'allowed_formats': settings.CAD_ALLOWED_EXTENSIONS
                    },
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
                            # Process CAD file (GLB/GLTF, STL, OBJ)
                            # Extract geometry and convert to GLB for web visualization
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
                            # The process_result should contain the converted/copied GLB file
                            glb_file_path = None
                            if process_result.get('glb_path') and Path(process_result['glb_path']).exists():
                                glb_file_path = Path(process_result['glb_path'])
                            elif temp_file_path.exists() and temp_file_path.suffix.lower() in ['.glb', '.gltf']:
                                # Fallback: Original file is already GLB/GLTF, use it
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
                                logger.warning(f"GLB file not found for component {component.id}. Conversion may have failed.")
                            
                            # Auto-fill mountable_sides and compatibility via rules
                            from .utils import COMPONENT_PLACEMENT_RULES
                            rules = COMPONENT_PLACEMENT_RULES.get(component.category_label, {})
                            component.mountable_sides = rules.get('mountable_sides', [])
                            component.supported_orientations = rules.get('supported_orientations', ['fixed'])
                            component.compatible_types = rules.get('compatible', [])
                            
                            component.processing_status = 'completed'
                            component.save()
                            
                        except Exception as e:
                            error_message = str(e)
                            # Provide more helpful error messages for STEP conversion failures
                            if 'STEP' in error_message or 'step' in error_message.lower() or 'conversion' in error_message.lower():
                                error_message = (
                                    f"STEP file conversion failed: {error_message}\n\n"
                                    "SOLUTIONS:\n"
                                    "1. Pre-convert STEP to STL/OBJ:\n"
                                    "   - Use FreeCAD (free): https://www.freecad.org/\n"
                                    "   - Or use online converters\n"
                                    "   - Then upload the STL or OBJ file instead\n\n"
                                    "2. Set up FreeCAD Docker service:\n"
                                    "   - Build the FreeCAD Docker container\n"
                                    "   - Set FREECAD_DOCKER_URL environment variable\n"
                                    "   - See backend/README.md for details\n\n"
                                    "3. For development, use Python 3.10-3.12:\n"
                                    "   - Install pythonocc-core: pip install pythonocc-core"
                                )
                            component.processing_status = 'failed'
                            component.processing_error = error_message
                            component.save()
                            logger.error(f"Component processing failed: {error_message}", exc_info=True)
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

