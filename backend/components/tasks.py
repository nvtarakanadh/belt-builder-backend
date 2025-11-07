"""
Celery tasks for background CAD processing
"""
from celery import shared_task
from django.conf import settings
from pathlib import Path
from .models import Component, ConnectionPoint
from cad_processing.utils import process_cad_file
from .utils import COMPONENT_PLACEMENT_RULES
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_component_async(component_id):
    """
    Process GLB/GLTF component file asynchronously.
    Extracts geometry data from GLB file (no conversion needed).
    """
    try:
        component = Component.objects.get(id=component_id)
        
        if component.processing_status == 'completed':
            logger.warning(f"Component {component_id} already processed")
            return
        
        component.processing_status = 'processing'
        component.processing_error = None
        component.save()
        
        # Get original file path
        original_file_path = component.original_file.path
        
        # Process GLB file (no conversion needed)
        glb_output_path = Path(settings.MEDIA_ROOT) / 'components' / 'glb' / f'{component.id}.glb'
        glb_output_path.parent.mkdir(parents=True, exist_ok=True)
        
        process_result = process_cad_file(
            original_file_path,
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
        if process_result.get('glb_path') and Path(process_result['glb_path']).exists():
            glb_file_path = Path(process_result['glb_path'])
            with open(glb_file_path, 'rb') as glb_file:
                component.glb_file.save(
                    f'{component.id}.glb',
                    glb_file,
                    save=False  # Don't save yet, we'll save after setting other fields
                )
        
        # Fill from rules
        rules = COMPONENT_PLACEMENT_RULES.get(component.category_label, {})
        component.mountable_sides = rules.get('mountable_sides', [])
        component.supported_orientations = rules.get('supported_orientations', ['fixed'])
        component.compatible_types = rules.get('compatible', [])
        
        component.processing_status = 'completed'
        component.save()
        
        logger.info(f"Successfully processed component {component_id}")
        return {'status': 'completed', 'component_id': component_id}
        
    except Component.DoesNotExist:
        logger.error(f"Component {component_id} not found")
        return {'status': 'error', 'message': 'Component not found'}
    except Exception as e:
        logger.error(f"Error processing component {component_id}: {e}")
        if component:
            component.processing_status = 'failed'
            component.processing_error = str(e)
            component.save()
        return {'status': 'error', 'message': str(e)}

