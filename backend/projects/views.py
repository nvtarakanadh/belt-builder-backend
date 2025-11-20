from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Project, AssemblyItem
from .serializers import (
    ProjectSerializer, ProjectListSerializer,
    AssemblyItemSerializer, AssemblyItemCreateSerializer
)
from components.models import Component, ConnectionPoint


@method_decorator(csrf_exempt, name='dispatch')
class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for projects"""
    permission_classes = [AllowAny]  # Allow unauthenticated access for development
    authentication_classes = [SessionAuthentication]  # Enable session authentication
    pagination_class = None  # Disable pagination for projects list
    
    def get_queryset(self):
        # Filter projects by owner if authenticated, otherwise return empty queryset
        if self.request.user.is_authenticated:
            queryset = Project.objects.filter(owner=self.request.user).prefetch_related('assembly_items__component')
        else:
            # Return empty queryset for unauthenticated users (or public projects if needed)
            queryset = Project.objects.none()
        
        # Allow filtering by public projects
        if self.request.query_params.get('include_public') == 'true':
            if self.request.user.is_authenticated:
                queryset = Project.objects.filter(Q(owner=self.request.user) | Q(is_public=True)).prefetch_related('assembly_items__component')
            else:
                queryset = Project.objects.filter(is_public=True).prefetch_related('assembly_items__component')
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectSerializer
    
    def perform_create(self, serializer):
        # Only allow authenticated users to create projects
        if self.request.user.is_authenticated:
            serializer.save(owner=self.request.user)
        else:
            # Unauthenticated users cannot create projects
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Authentication required to create projects")
    
    @action(detail=True, methods=['post'])
    def add_component(self, request, pk=None):
        """
        Add a component to the project assembly.
        POST /api/projects/{id}/add_component/
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            project = self.get_object()
            logger.info(f"Adding component to project {project.id}")
            
            serializer = AssemblyItemCreateSerializer(data=request.data, context={'project': project})
            if not serializer.is_valid():
                logger.error(f"Serializer validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            component_id = serializer.validated_data['component_id']
            logger.info(f"Component ID: {component_id}")
            component = get_object_or_404(Component, id=component_id)
            logger.info(f"Component found: {component.name}, GLB file: {component.glb_file.name if component.glb_file else 'None'}")
            
            with transaction.atomic():
                assembly_item = AssemblyItem.objects.create(
                    project=project,
                    component=component,
                    custom_name=serializer.validated_data.get('custom_name', ''),
                    position_x=serializer.validated_data.get('position_x', 0.0),
                    position_y=serializer.validated_data.get('position_y', 0.0),
                    position_z=serializer.validated_data.get('position_z', 0.0),
                    rotation_x=serializer.validated_data.get('rotation_x', 0.0),
                    rotation_y=serializer.validated_data.get('rotation_y', 0.0),
                    rotation_z=serializer.validated_data.get('rotation_z', 0.0),
                    rotation_w=serializer.validated_data.get('rotation_w', 1.0),
                    scale_x=serializer.validated_data.get('scale_x', 1.0),
                    scale_y=serializer.validated_data.get('scale_y', 1.0),
                    scale_z=serializer.validated_data.get('scale_z', 1.0),
                    parent_id=serializer.validated_data.get('parent_id'),
                    attached_at_point=serializer.validated_data.get('attached_at_point', ''),
                    metadata=serializer.validated_data.get('metadata', {}),
                    order=serializer.validated_data.get('order', project.assembly_items.count()),
                )
                logger.info(f"Assembly item created: {assembly_item.id}")
            
            response_serializer = AssemblyItemSerializer(
                assembly_item,
                context={'request': request, 'project': project}
            )
            response_data = response_serializer.data
            logger.info(f"Returning assembly item data. GLB URL: {response_data.get('component', {}).get('glb_url', 'Not found')}")
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error adding component: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def placement_suggestions(self, request, pk=None):
        """
        Get smart placement suggestions for a component in the project.
        GET /api/projects/{id}/placement_suggestions/?component_id=123
        """
        project = self.get_object()
        component_id = request.query_params.get('component_id')
        
        if not component_id:
            return Response(
                {'error': 'component_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            target_component = get_object_or_404(Component, id=component_id)
        except ValueError:
            return Response(
                {'error': 'Invalid component_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all existing assembly items in the project
        existing_items = project.assembly_items.select_related('component').prefetch_related(
            'component__connection_points'
        ).all()
        
        suggestions = []
        
        # If project is empty, suggest origin placement
        if existing_items.count() == 0:
            suggestions.append({
                'position': [0.0, 0.0, 0.0],
                'rotation': [0.0, 0.0, 0.0, 1.0],
                'type': 'origin',
                'description': 'Place at origin',
                'confidence': 1.0,
            })
        else:
            # Analyze connection points from existing components
            for item in existing_items:
                existing_component = item.component
                
                # Get world transform of existing item
                world_transform = item.get_world_transform()
                world_pos = world_transform['position']
                
                # Get connection points from existing component
                connection_points = existing_component.connection_points.all()
                
                for cp in connection_points:
                    # Calculate world position of connection point
                    # (simplified - would need proper rotation/transform in production)
                    cp_world_pos = [
                        world_pos[0] + cp.position_x,
                        world_pos[1] + cp.position_y,
                        world_pos[2] + cp.position_z,
                    ]
                    
                    # Check compatibility
                    compatible = self._check_compatibility(target_component, cp)
                    
                    if compatible:
                        # Calculate suggested position for target component
                        # Place target component so one of its connection points aligns
                        target_cp = self._find_best_matching_connection_point(
                            target_component, cp
                        )
                        
                        if target_cp:
                            # Calculate offset to align connection points
                            suggested_pos = [
                                cp_world_pos[0] - target_cp.position_x,
                                cp_world_pos[1] - target_cp.position_y,
                                cp_world_pos[2] - target_cp.position_z,
                            ]
                            
                            suggestions.append({
                                'position': suggested_pos,
                                'rotation': item.rotation,  # Match rotation of existing item
                                'type': 'connection',
                                'description': f'Connect to {existing_component.name} at {cp.name}',
                                'confidence': 0.9,
                                'target_item_id': item.id,
                                'connection_point': {
                                    'id': cp.id,
                                    'name': cp.name,
                                    'position': cp_world_pos,
                                    'normal': cp.normal,
                                },
                                'component_connection_point': {
                                    'id': target_cp.id,
                                    'name': target_cp.name,
                                },
                            })
            
            # Also suggest placements near existing components (snap positions)
            for item in existing_items:
                # Suggest placements around the bounding box
                component = item.component
                world_transform = item.get_world_transform()
                world_pos = world_transform['position']
                
                bbox = component.bounding_box
                dims = component.dimensions
                
                # Suggest positions on top, bottom, sides
                suggestions.extend([
                    {
                        'position': [
                            world_pos[0],
                            world_pos[1],
                            world_pos[2] + dims['height'] / 2 + target_component.dimensions['height'] / 2
                        ],
                        'rotation': item.rotation,
                        'type': 'snap_top',
                        'description': f'Place on top of {component.name}',
                        'confidence': 0.7,
                        'target_item_id': item.id,
                    },
                    {
                        'position': [
                            world_pos[0],
                            world_pos[1],
                            world_pos[2] - dims['height'] / 2 - target_component.dimensions['height'] / 2
                        ],
                        'rotation': item.rotation,
                        'type': 'snap_bottom',
                        'description': f'Place below {component.name}',
                        'confidence': 0.7,
                        'target_item_id': item.id,
                    },
                ])
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return Response({
            'component_id': component_id,
            'suggestions': suggestions[:20],  # Limit to top 20
            'count': len(suggestions),
        })
    
    def _check_compatibility(self, component, connection_point):
        """Check if component is compatible with connection point"""
        # Simplified compatibility check
        # In production, would check connection types, sizes, etc.
        
        # Check if component has compatible connection points
        compatible_cps = component.connection_points.filter(
            connection_type=connection_point.connection_type
        )
        
        if compatible_cps.exists():
            return True
        
        # Also check if component is mountable and connection point accepts mounts
        if component.is_mountable and connection_point.connection_type == 'mount':
            return True
        
        return False
    
    def _find_best_matching_connection_point(self, component, target_cp):
        """Find the best matching connection point on component for target connection point"""
        # Get connection points with matching type
        matching = component.connection_points.filter(
            connection_type=target_cp.connection_type
        )
        
        if matching.exists():
            # Return first match (could be improved with geometry matching)
            return matching.first()
        
        # Fallback: return any mount point if component is mountable
        if component.is_mountable:
            mount_points = component.connection_points.filter(connection_type='mount')
            if mount_points.exists():
                return mount_points.first()
        
        return None
    
    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        """
        Save/update assembly state.
        POST /api/projects/{id}/save/
        Updates existing items and deletes items that are no longer in the scene.
        Does not create new items - use add_component for that.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        project = self.get_object()
        
        # Update assembly items if provided
        items_data = request.data.get('assembly_items', [])
        
        updated_count = 0
        skipped_count = 0
        deleted_count = 0
        errors = []
        
        try:
            with transaction.atomic():
                # Get all existing item IDs for this project
                existing_items = AssemblyItem.objects.filter(project=project)
                existing_item_ids = set(existing_items.values_list('id', flat=True))
                
                # Get IDs from the save request
                requested_item_ids = set()
                for item_data in items_data:
                    item_id = item_data.get('id')
                    if item_id:
                        requested_item_ids.add(item_id)
                
                # Find items to delete (exist in backend but not in save request)
                items_to_delete = existing_item_ids - requested_item_ids
                
                # Safety check: Only delete if we're not deleting ALL items
                # This prevents accidental deletion of everything if save is called with empty/invalid data
                if items_to_delete:
                    # If we're trying to delete all items, require explicit confirmation
                    if len(items_to_delete) == len(existing_item_ids) and len(existing_item_ids) > 0:
                        # Check if this is an intentional "clear all" operation
                        # Only allow if items_data is explicitly empty (not just missing IDs)
                        if len(items_data) == 0:
                            # Explicit empty array - user wants to clear all
                            deleted_items = existing_items.filter(id__in=items_to_delete)
                            deleted_count = deleted_items.count()
                            deleted_items.delete()
                            logger.info(f"Cleared all {deleted_count} items from the scene (explicit empty save)")
                        else:
                            # This looks like an error - we have items_data but all IDs are invalid
                            # Don't delete anything, just log a warning
                            logger.warning(f"Attempted to delete all {len(existing_item_ids)} items, but save request contains {len(items_data)} items with invalid IDs. Aborting deletion for safety.")
                            skipped_count += len(items_data)
                    else:
                        # Partial deletion - safe to proceed
                        deleted_items = existing_items.filter(id__in=items_to_delete)
                        deleted_count = deleted_items.count()
                        deleted_items.delete()
                        logger.info(f"Deleted {deleted_count} items that are no longer in the scene: {items_to_delete}")
                
                # Track which items we're updating to detect duplicates
                processed_ids = set()
                
                # Update existing items
                for item_data in items_data:
                    item_id = item_data.get('id')
                    
                    if not item_id:
                        skipped_count += 1
                        logger.warning(f"Item data missing ID, skipping: {item_data}")
                        continue
                    
                    # Check for duplicate IDs in the request
                    if item_id in processed_ids:
                        skipped_count += 1
                        logger.warning(f"Duplicate ID in save request: {item_id}, skipping")
                        continue
                    
                    # Only update items that exist in the database
                    if item_id not in existing_item_ids:
                        skipped_count += 1
                        logger.warning(f"Item ID {item_id} does not exist in project {project.id}, skipping")
                        continue
                    
                    try:
                        item = AssemblyItem.objects.get(id=item_id, project=project)
                        item.position_x = item_data.get('position_x', item.position_x)
                        item.position_y = item_data.get('position_y', item.position_y)
                        item.position_z = item_data.get('position_z', item.position_z)
                        item.rotation_x = item_data.get('rotation_x', item.rotation_x)
                        item.rotation_y = item_data.get('rotation_y', item.rotation_y)
                        item.rotation_z = item_data.get('rotation_z', item.rotation_z)
                        item.rotation_w = item_data.get('rotation_w', item.rotation_w)
                        item.scale_x = item_data.get('scale_x', item.scale_x)
                        item.scale_y = item_data.get('scale_y', item.scale_y)
                        item.scale_z = item_data.get('scale_z', item.scale_z)
                        item.metadata = item_data.get('metadata', item.metadata)
                        item.save()
                        processed_ids.add(item_id)
                        updated_count += 1
                    except AssemblyItem.DoesNotExist:
                        skipped_count += 1
                        logger.warning(f"Item {item_id} not found during update")
                    except Exception as e:
                        errors.append(f"Error updating item {item_id}: {str(e)}")
                        logger.error(f"Error updating item {item_id}: {str(e)}", exc_info=True)
            
            response_data = {
                'status': 'saved',
                'updated': updated_count,
                'deleted': deleted_count,
                'skipped': skipped_count,
            }
            if errors:
                response_data['errors'] = errors
            
            logger.info(f"Save completed: {updated_count} updated, {deleted_count} deleted, {skipped_count} skipped")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Save failed: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['delete'])
    def remove_component(self, request, pk=None):
        """Remove a component from the assembly"""
        project = self.get_object()
        item_id = request.query_params.get('item_id')
        
        if not item_id:
            return Response(
                {'error': 'item_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            item = get_object_or_404(AssemblyItem, id=item_id, project=project)
            item.delete()
            return Response({'status': 'removed'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AssemblyItemViewSet(viewsets.ModelViewSet):
    """ViewSet for assembly items"""
    permission_classes = [AllowAny]  # Allow unauthenticated access for development
    serializer_class = AssemblyItemSerializer
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        queryset = AssemblyItem.objects.all().select_related(
            'component', 'project', 'parent', 'connected_to', 'connection_point'
        )
        
        # Filter by project_id if provided (for list operations)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        return queryset
    
    def get_object(self):
        """
        Override to allow deletion/retrieval by ID without requiring project_id.
        For list operations, project_id filtering is still applied in get_queryset.
        """
        # For detail operations (GET, PUT, PATCH, DELETE), allow access by ID
        # The queryset will include all items, but we can still filter if project_id is provided
        queryset = self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        
        # Try to get the object - if project_id was provided, it's already filtered
        # If not, we'll get it by ID (which is unique)
        try:
            obj = queryset.get(**{self.lookup_field: lookup_value})
        except AssemblyItem.DoesNotExist:
            # If not found in filtered queryset, try without project filter
            obj = AssemblyItem.objects.get(**{self.lookup_field: lookup_value})
        
        self.check_object_permissions(self.request, obj)
        return obj
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            try:
                context['project'] = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                pass
        return context

