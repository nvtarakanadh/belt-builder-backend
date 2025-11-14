"""
STEP to GLB Converter API
Converts STEP files to GLB format using pythonocc-core, trimesh, and pygltflib
"""
import logging
import os
import tempfile
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# Try to import required libraries
try:
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.STEPControl_Reader import STEPControl_Reader
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.StlAPI import StlAPI_Writer
    PYTHONOCC_AVAILABLE = True
except ImportError:
    PYTHONOCC_AVAILABLE = False
    logger.warning("pythonocc-core not available. STEP conversion will not work.")

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    logger.warning("trimesh not available. STL to GLB conversion will not work.")

try:
    import pygltflib
    PYGLTF_AVAILABLE = True
except ImportError:
    PYGLTF_AVAILABLE = False
    logger.warning("pygltflib not available. GLB export may be limited.")


@csrf_exempt
@require_http_methods(["POST"])
def convert_step_to_glb(request):
    """
    Convert STEP file to GLB format.
    
    Endpoint: POST /api/convert/step/
    Input: multipart/form-data with "file" field (.step or .stp)
    Output: JSON with glb_url and sizeMB
    """
    # Check if required libraries are available
    if not PYTHONOCC_AVAILABLE:
        return JsonResponse({
            "ok": False,
            "error": "pythonocc-core is not installed. Please install it: pip install pythonocc-core"
        }, status=500)
    
    if not TRIMESH_AVAILABLE:
        return JsonResponse({
            "ok": False,
            "error": "trimesh is not installed. Please install it: pip install trimesh"
        }, status=500)
    
    # Check if file was uploaded
    if 'file' not in request.FILES:
        return JsonResponse({
            "ok": False,
            "error": "No file provided. Please upload a STEP file using the 'file' field."
        }, status=400)
    
    uploaded_file = request.FILES['file']
    file_name = uploaded_file.name
    file_ext = Path(file_name).suffix.lower()
    
    # Validate file extension
    if file_ext not in ['.step', '.stp']:
        return JsonResponse({
            "ok": False,
            "error": f"Invalid file type. Expected .step or .stp, got {file_ext}"
        }, status=400)
    
    # Create temporary directory for processing
    temp_dir = None
    step_file_path = None
    stl_file_path = None
    glb_file_path = None
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='step_converter_')
        logger.info(f"Created temp directory: {temp_dir}")
        
        # Save uploaded STEP file to temp directory
        step_file_path = os.path.join(temp_dir, f"input{file_ext}")
        with open(step_file_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        
        logger.info(f"Saved STEP file: {step_file_path}")
        
        # Step 1: Convert STEP → STL using pythonocc-core
        stl_file_path = os.path.join(temp_dir, "output.stl")
        logger.info("Starting STEP → STL conversion...")
        
        # Read STEP file
        step_reader = STEPControl_Reader()
        status = step_reader.ReadFile(step_file_path)
        
        if status != IFSelect_RetDone:
            return JsonResponse({
                "ok": False,
                "error": f"Failed to read STEP file. Status: {status}"
            }, status=400)
        
        # Transfer all roots
        step_reader.TransferRoots()
        shape = step_reader.OneShape()
        
        if shape.IsNull():
            return JsonResponse({
                "ok": False,
                "error": "STEP file contains no valid geometry"
            }, status=400)
        
        # Mesh the shape (tessellate to triangles)
        # Lower deviation = higher quality (0.1 is a good default)
        mesh_deviation = 0.1
        mesh = BRepMesh_IncrementalMesh(shape, mesh_deviation, False, mesh_deviation, True)
        mesh.Perform()
        
        # Write STL file
        stl_writer = StlAPI_Writer()
        stl_writer.SetASCIIMode(False)  # Use binary STL
        success = stl_writer.Write(shape, stl_file_path)
        
        if not success:
            return JsonResponse({
                "ok": False,
                "error": "Failed to write STL file"
            }, status=500)
        
        logger.info(f"STEP → STL conversion complete: {stl_file_path}")
        
        # Step 2: Convert STL → GLB using trimesh
        logger.info("Starting STL → GLB conversion...")
        
        # Load STL with trimesh
        mesh_obj = trimesh.load(stl_file_path)
        
        # Handle scene (multiple meshes)
        if isinstance(mesh_obj, trimesh.Scene):
            # Combine all meshes into one
            mesh_list = []
            for node_name in mesh_obj.graph.nodes_geometry:
                transform, geometry_name = mesh_obj.graph[node_name]
                geometry = mesh_obj.geometry[geometry_name]
                if isinstance(geometry, trimesh.Trimesh):
                    mesh_list.append(geometry.copy())
            if mesh_list:
                mesh_obj = trimesh.util.concatenate(mesh_list)
        
        # Ensure we have a Trimesh object
        if not isinstance(mesh_obj, trimesh.Trimesh):
            return JsonResponse({
                "ok": False,
                "error": f"Failed to extract mesh from STL. Got type: {type(mesh_obj)}"
            }, status=500)
        
        # Export to GLB
        glb_file_path = os.path.join(temp_dir, "output.glb")
        mesh_obj.export(glb_file_path, file_type='glb')
        
        logger.info(f"STL → GLB conversion complete: {glb_file_path}")
        
        # Step 3: Save GLB file to media storage
        output_filename = f"{Path(file_name).stem}_{os.urandom(4).hex()}.glb"
        media_path = os.path.join("converted", output_filename)
        
        # Read the GLB file
        with open(glb_file_path, 'rb') as f:
            glb_content = f.read()
        
        # Save to media storage
        saved_path = default_storage.save(media_path, ContentFile(glb_content))
        
        # Get file size in MB
        file_size_mb = len(glb_content) / (1024 * 1024)
        
        # Build URL
        if hasattr(settings, 'MEDIA_URL'):
            glb_url = f"{settings.MEDIA_URL}{saved_path}"
        else:
            glb_url = f"/media/{saved_path}"
        
        # If using S3, construct full URL
        if getattr(settings, 'USE_S3', False):
            aws_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', '')
            if aws_domain:
                glb_url = f"https://{aws_domain}/{saved_path}"
        
        logger.info(f"GLB file saved: {saved_path}, size: {file_size_mb:.2f} MB")
        
        return JsonResponse({
            "ok": True,
            "message": "Converted successfully",
            "glb_url": glb_url,
            "sizeMB": round(file_size_mb, 2)
        })
        
    except Exception as e:
        logger.error(f"Error converting STEP to GLB: {str(e)}", exc_info=True)
        return JsonResponse({
            "ok": False,
            "error": f"Conversion failed: {str(e)}"
        }, status=500)
    
    finally:
        # Cleanup temporary files
        try:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")
