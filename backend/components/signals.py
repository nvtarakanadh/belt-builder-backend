from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from pathlib import Path
import logging
from .models import Component
from cad_processing.utils import process_cad_file
from .utils import COMPONENT_PLACEMENT_RULES

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Component)
def handle_component_post_save(sender, instance: Component, created, **kwargs):
    if not created:
        return
    try:
        instance.processing_status = 'processing'
        instance.processing_error = None
        instance.save(update_fields=['processing_status', 'processing_error'])

        temp_path = Path(instance.original_file.path)
        glb_output_path = Path(settings.MEDIA_ROOT) / 'components' / 'glb' / f'{instance.id}.glb'
        glb_output_path.parent.mkdir(parents=True, exist_ok=True)

        process_result = process_cad_file(
            temp_path,
            extract_geometry=True,
            copy_glb_to=str(glb_output_path)
        )

        geometry_data = process_result.get('geometry_data', {})
        bbox = geometry_data.get('bounding_box', {})
        center = geometry_data.get('center', {})

        instance.bounding_box = bbox or instance.bounding_box
        if isinstance(center, list):
            instance.center = {'x': center[0], 'y': center[1], 'z': center[2]}
        elif isinstance(center, dict):
            instance.center = center
        instance.volume = geometry_data.get('volume', instance.volume)

        glb_path = process_result.get('glb_path')
        if glb_path:
            glb_path_obj = Path(glb_path)
            # Check if GLB file was actually created and save it properly
            if glb_path_obj.exists() and glb_path_obj.stat().st_size > 0:
                with open(glb_path_obj, 'rb') as glb_file:
                    instance.glb_file.save(
                        f'{instance.id}.glb',
                        glb_file,
                        save=False  # Don't save yet, we'll save after setting other fields
                    )
                logger.info(f"GLB file saved for component {instance.id}: {instance.glb_file.name}")
            else:
                logger.warning(f"GLB conversion returned path but file doesn't exist or is empty: {glb_path}")

        rules = COMPONENT_PLACEMENT_RULES.get(instance.category_label, {})
        instance.mountable_sides = rules.get('mountable_sides', [])
        instance.supported_orientations = rules.get('supported_orientations', ['fixed'])
        instance.compatible_types = rules.get('compatible', [])

        instance.processing_status = 'completed'
        instance.save()
    except Exception as e:
        instance.processing_status = 'failed'
        instance.processing_error = str(e)
        instance.save()


