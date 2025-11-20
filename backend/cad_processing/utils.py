"""
CAD file processing utilities for geometry extraction and conversion.
Supports GLB/GLTF, STEP, STL, and OBJ files. Converts all formats to GLB for web visualization.

STEP files are converted using FreeCAD in a Docker container (deployment-friendly).
The FreeCAD Docker service can be deployed alongside the main application.
"""
import logging
from pathlib import Path
import shutil
import tempfile
import requests
import time
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    logger.warning("trimesh not available. Geometry extraction will be limited.")

try:
    import pygltflib
    PYGLTF_AVAILABLE = True
except ImportError:
    PYGLTF_AVAILABLE = False
    logger.warning("pygltflib not available. GLB export may be limited.")

# Check for pythonocc-core for STEP conversion
try:
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.STEPControl_Reader import STEPControl_Reader
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.StlAPI import StlAPI_Writer
    PYTHONOCC_AVAILABLE = True
except ImportError:
    PYTHONOCC_AVAILABLE = False
    logger.warning("pythonocc-core not available. STEP conversion via pythonocc-core will not work.")

# CloudConvert API for STEP conversion
CLOUDCONVERT_API_KEY = getattr(settings, 'CLOUDCONVERT_API_KEY', None)
CLOUDCONVERT_API_URL = 'https://api.cloudconvert.com/v2'


def convert_step_via_freecad_local(step_file_path, output_format='stl'):
    """
    Convert STEP file to STL/OBJ using FreeCAD installed locally (not Docker).
    
    Args:
        step_file_path: Path to STEP file
        output_format: 'stl' or 'obj'
    
    Returns:
        Path to converted file (temporary location)
    """
    import subprocess
    
    step_file_path = Path(step_file_path)
    if not step_file_path.exists():
        raise FileNotFoundError(f"STEP file not found: {step_file_path}")
    
    try:
        # Create temporary output file
        temp_dir = Path(tempfile.gettempdir()) / 'step_converter'
        temp_dir.mkdir(exist_ok=True)
        output_path = temp_dir / f"{step_file_path.stem}_converted.{output_format}"
        
        # Try to use the freecad_converter.py script directly
        # First, find the script path
        script_path = Path(__file__).parent.parent / 'freecad_converter.py'
        if not script_path.exists():
            # Try alternative location
            script_path = Path(__file__).parent.parent.parent / 'freecad_converter.py'
        
        if not script_path.exists():
            raise ValueError("freecad_converter.py script not found")
        
        # Run the converter script
        python_cmd = ['python', str(script_path), str(step_file_path), str(output_path), '--format', output_format]
        
        result = subprocess.run(
            python_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode != 0:
            error_detail = result.stderr or result.stdout or "Unknown error"
            raise ValueError(f"FreeCAD local conversion failed: {error_detail}")
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValueError(f"Converted file not found or is empty: {output_path}")
        
        logger.info(f"Successfully converted STEP to {output_format.upper()} using local FreeCAD: {output_path}")
        return output_path
        
    except FileNotFoundError:
        raise ValueError("FreeCAD Python modules not found. FreeCAD must be installed on the system.")
    except subprocess.TimeoutExpired:
        raise ValueError("STEP conversion timed out (exceeded 5 minutes)")
    except Exception as e:
        logger.error(f"Error converting STEP via local FreeCAD: {e}")
        raise ValueError(f"STEP conversion via local FreeCAD failed: {str(e)}")


def convert_step_via_freecad_docker(step_file_path, output_format='stl'):
    """
    Convert STEP file to STL/OBJ using FreeCAD in Docker container (deployment-friendly).
    
    This function calls a FreeCAD Docker container to perform the conversion.
    The Docker container can be deployed alongside the main application.
    
    Args:
        step_file_path: Path to STEP file
        output_format: 'stl' or 'obj'
    
    Returns:
        Path to converted file (temporary location)
    """
    import subprocess
    import shutil
    
    step_file_path = Path(step_file_path)
    if not step_file_path.exists():
        raise FileNotFoundError(f"STEP file not found: {step_file_path}")
    
    # Check if FreeCAD Docker container is available
    freecad_docker_image = getattr(settings, 'FREECAD_DOCKER_IMAGE', 'freecad-converter:latest')
    freecad_docker_url = getattr(settings, 'FREECAD_DOCKER_URL', None)  # e.g., 'http://freecad-service:8001'
    
    # Option 1: Use FreeCAD Docker container via HTTP API (if available)
    if freecad_docker_url:
        try:
            logger.info(f"Converting STEP via FreeCAD Docker service: {freecad_docker_url}")
            # Upload file to FreeCAD service
            with open(step_file_path, 'rb') as f:
                files = {'file': (step_file_path.name, f, 'application/octet-stream')}
                data = {'output_format': output_format}
                response = requests.post(
                    f"{freecad_docker_url}/convert",
                    files=files,
                    data=data,
                    timeout=300
                )
                response.raise_for_status()
                
                # Save converted file
                temp_dir = Path(tempfile.gettempdir()) / 'step_converter'
                temp_dir.mkdir(exist_ok=True)
                output_path = temp_dir / f"{step_file_path.stem}_converted.{output_format}"
                
                with open(output_path, 'wb') as out_file:
                    out_file.write(response.content)
                
                logger.info(f"Successfully converted STEP to {output_format.upper()}: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"FreeCAD Docker service conversion failed: {e}")
            raise ValueError(f"FreeCAD Docker service conversion failed: {e}")
    
    # Option 2: Use FreeCAD Docker container via subprocess (if Docker is available)
    try:
        # Check if docker command is available
        subprocess.run(['docker', '--version'], capture_output=True, check=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        error_detail = "Docker is not installed or not accessible" if isinstance(e, FileNotFoundError) else "Docker check failed"
        raise ValueError(
            f"STEP file conversion requires FreeCAD Docker container, but {error_detail}.\n\n"
            "SOLUTIONS:\n"
            "1. Install Docker Desktop (https://www.docker.com/products/docker-desktop/)\n"
            "   Then build and run the FreeCAD Docker container\n\n"
            "2. Set up FreeCAD Docker service:\n"
            "   - Build: docker build -f Dockerfile.freecad -t freecad-converter:latest .\n"
            "   - Run: docker run -d -p 8001:8001 --name freecad-service freecad-converter:latest\n"
            "   - Set FREECAD_DOCKER_URL=http://localhost:8001\n\n"
            "3. Pre-convert STEP files to STL/OBJ before uploading:\n"
            "   - Use FreeCAD (free): https://www.freecad.org/\n"
            "   - Or use online converters\n"
            "   - Then upload the STL or OBJ file instead\n\n"
            "4. For development, use Python 3.10-3.12 and install pythonocc-core:\n"
            "   pip install pythonocc-core"
        )
    
    # Use Docker to run FreeCAD conversion
    try:
        logger.info(f"Converting STEP via FreeCAD Docker container: {freecad_docker_image}")
        
        # Create temporary output file
        temp_dir = Path(tempfile.gettempdir()) / 'step_converter'
        temp_dir.mkdir(exist_ok=True)
        output_path = temp_dir / f"{step_file_path.stem}_converted.{output_format}"
        
        # Run FreeCAD conversion in Docker
        # Mount the file and output directory
        docker_cmd = [
            'docker', 'run', '--rm',
            '-v', f'{step_file_path.parent.absolute()}:/input:ro',
            '-v', f'{temp_dir.absolute()}:/output:rw',
            freecad_docker_image,
            'python3', '/app/freecad_converter.py',
            f'/input/{step_file_path.name}',
            f'/output/{output_path.name}',
            '--format', output_format
        ]
        
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode != 0:
            error_detail = result.stderr or result.stdout or "Unknown error"
            raise ValueError(
                f"FreeCAD Docker conversion failed.\n"
                f"Error: {error_detail}\n\n"
                f"Make sure:\n"
                f"1. The FreeCAD Docker image '{freecad_docker_image}' exists\n"
                f"2. Build it with: docker build -f Dockerfile.freecad -t {freecad_docker_image} .\n"
                f"3. Or use a pre-converted STL/OBJ file instead"
            )
        
        if not output_path.exists():
            raise ValueError(
                f"Converted file not found: {output_path}\n"
                f"The Docker container may have failed silently. Check Docker logs."
            )
        
        logger.info(f"Successfully converted STEP to {output_format.upper()}: {output_path}")
        return output_path
        
    except subprocess.TimeoutExpired:
        raise ValueError("STEP conversion timed out (exceeded 5 minutes)")
    except Exception as e:
        logger.error(f"Error converting STEP via FreeCAD Docker: {e}")
        raise ValueError(
            f"STEP file conversion failed: {e}\n\n"
            "Please ensure:\n"
            "1. FreeCAD Docker container is built and available\n"
            "2. Docker is running and accessible\n"
            "3. Or pre-convert STEP files to STL/OBJ before uploading"
        )


def convert_step_via_cloudconvert(step_file_path, output_format='stl'):
    """
    Convert STEP file to STL/OBJ using CloudConvert API.
    
    Args:
        step_file_path: Path to STEP file
        output_format: 'stl' or 'obj'
    
    Returns:
        Path to converted file (temporary location)
    """
    if not CLOUDCONVERT_API_KEY:
        raise ValueError("CloudConvert API key not configured. Set CLOUDCONVERT_API_KEY environment variable.")
    
    step_file_path = Path(step_file_path)
    if not step_file_path.exists():
        raise FileNotFoundError(f"STEP file not found: {step_file_path}")
    
    try:
        # Create temporary output file
        temp_dir = Path(tempfile.gettempdir()) / 'step_converter'
        temp_dir.mkdir(exist_ok=True)
        output_path = temp_dir / f"{step_file_path.stem}_converted.{output_format}"
        
        logger.info(f"Converting STEP to {output_format.upper()} via CloudConvert...")
        
        # Map output format
        output_format_map = {'stl': 'stl', 'obj': 'obj'}
        target_format = output_format_map.get(output_format, 'stl')
        
        headers = {
            'Authorization': f'Bearer {CLOUDCONVERT_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Step 1: Create a job with tasks (import, convert, export)
        job_url = f"{CLOUDCONVERT_API_URL}/jobs"
        job_payload = {
            'tasks': {
                'import-step': {
                    'operation': 'import/upload'
                },
                'convert-step': {
                    'operation': 'convert',
                    'input': 'import-step',
                    'input_format': 'step',
                    'output_format': target_format
                },
                'export-result': {
                    'operation': 'export/url',
                    'input': 'convert-step'
                }
            }
        }
        
        job_response = requests.post(job_url, headers=headers, json=job_payload, timeout=30)
        
        if not job_response.ok:
            error_text = job_response.text
            logger.error(f"CloudConvert job creation failed: {job_response.status_code} - {error_text}")
            raise ValueError(f"CloudConvert API error: {job_response.status_code} - {error_text}")
        
        job_response.raise_for_status()
        job_data = job_response.json()
        
        logger.debug(f"CloudConvert job response: {job_data}")
        
        # Extract job ID - try different response structures
        job_id = None
        if 'data' in job_data:
            job_id = job_data['data'].get('id')
        elif 'id' in job_data:
            job_id = job_data['id']
        
        if not job_id:
            raise ValueError(f"Failed to create CloudConvert job. Response: {job_response.text}")
        
        logger.info(f"CloudConvert job created, job ID: {job_id}")
        
        # Step 2: Upload the file for the import task
        # Find the import task in the response
        tasks_data = job_data.get('data', {}).get('tasks') if 'data' in job_data else job_data.get('tasks')
        import_task = None
        
        # Try list structure
        if isinstance(tasks_data, list):
            for task in tasks_data:
                if task.get('operation') == 'import/upload' or task.get('name') == 'import-step':
                    import_task = task
                    break
        # Try dict structure
        elif isinstance(tasks_data, dict):
            import_task = tasks_data.get('import-step')
        
        if not import_task:
            raise ValueError(f"Failed to find import task in CloudConvert job response. Tasks: {tasks_data}")
        
        # Get upload URL and form fields
        task_result = import_task.get('result', {})
        if not task_result:
            raise ValueError(f"Import task has no result. Task: {import_task}")
        
        # Try different structures for upload URL
        upload_url = None
        upload_fields = {}
        
        if 'form' in task_result:
            upload_url = task_result['form'].get('url')
            upload_fields = task_result['form'].get('parameters', {})
        elif 'url' in task_result:
            upload_url = task_result['url']
        
        if not upload_url:
            raise ValueError(f"Failed to get upload URL from CloudConvert job. Task result: {task_result}")
        
        # Upload file using the form URL and fields
        with open(step_file_path, 'rb') as f:
            files = {'file': (step_file_path.name, f, 'application/octet-stream')}
            # If upload_fields is empty, don't send it
            upload_data = upload_fields if upload_fields else None
            upload_response = requests.post(upload_url, data=upload_data, files=files, timeout=300)
            upload_response.raise_for_status()
        
        logger.info(f"File uploaded to CloudConvert")
        
        # Step 3: Wait for job to complete
        max_wait = 300  # 5 minutes
        start_time = time.time()
        download_url = None
        
        while time.time() - start_time < max_wait:
            status_url = f"{CLOUDCONVERT_API_URL}/jobs/{job_id}"
            status_response = requests.get(status_url, headers=headers, timeout=30)
            
            if not status_response.ok:
                error_text = status_response.text
                logger.error(f"CloudConvert job status check failed: {status_response.status_code} - {error_text}")
                raise ValueError(f"CloudConvert API error: {status_response.status_code} - {error_text}")
            
            status_response.raise_for_status()
            status_data = status_response.json()
            
            # Extract job status - try different response structures
            job_data = status_data.get('data', {}) if 'data' in status_data else status_data
            job_status = job_data.get('status')
            
            if job_status == 'finished':
                # Find the export task result
                tasks = job_data.get('tasks', [])
                
                # Try list structure
                if isinstance(tasks, list):
                    for task in tasks:
                        if task.get('operation') == 'export/url' or task.get('name') == 'export-result':
                            result = task.get('result', {})
                            files = result.get('files', [])
                            if files and len(files) > 0:
                                download_url = files[0].get('url')
                            break
                # Try dict structure
                elif isinstance(tasks, dict):
                    export_task = tasks.get('export-result')
                    if export_task:
                        result = export_task.get('result', {})
                        files = result.get('files', [])
                        if files and len(files) > 0:
                            download_url = files[0].get('url')
                
                if download_url:
                    break
            elif job_status == 'error':
                error_msg = job_data.get('message', 'Unknown error')
                raise ValueError(f"CloudConvert conversion failed: {error_msg}")
            elif job_status in ['waiting', 'processing']:
                # Still processing, wait and check again
                time.sleep(2)
            else:
                raise ValueError(f"Unexpected job status: {job_status}")
        
        if not download_url:
            raise ValueError("CloudConvert conversion timed out or failed to get download URL")
        
        # Step 4: Download the converted file
        download_response = requests.get(download_url, timeout=300)
        download_response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(download_response.content)
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValueError(f"Downloaded file is empty or not found: {output_path}")
        
        logger.info(f"Successfully converted STEP to {output_format.upper()} via CloudConvert: {output_path}")
        return output_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"CloudConvert API error: {e}")
        raise ValueError(f"CloudConvert API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error converting STEP via CloudConvert: {e}", exc_info=True)
        raise ValueError(f"STEP conversion via CloudConvert failed: {str(e)}")


def convert_step_via_pythonocc(step_file_path, output_format='stl'):
    """
    Convert STEP file to STL using pythonocc-core (OpenCASCADE).
    
    Args:
        step_file_path: Path to STEP file
        output_format: 'stl' (pythonocc only supports STL export)
    
    Returns:
        Path to converted file (temporary location)
    """
    if not PYTHONOCC_AVAILABLE:
        raise ValueError("pythonocc-core is not available")
    
    if output_format != 'stl':
        raise ValueError(f"pythonocc-core only supports STL output, got: {output_format}")
    
    step_file_path = Path(step_file_path)
    if not step_file_path.exists():
        raise FileNotFoundError(f"STEP file not found: {step_file_path}")
    
    try:
        # Create temporary output file
        temp_dir = Path(tempfile.gettempdir()) / 'step_converter'
        temp_dir.mkdir(exist_ok=True)
        output_path = temp_dir / f"{step_file_path.stem}_converted.stl"
        
        # Read STEP file
        reader = STEPControl_Reader()
        status = reader.ReadFile(str(step_file_path))
        
        if status != IFSelect_RetDone:
            raise ValueError(f"Failed to read STEP file: {step_file_path}")
        
        # Transfer all roots
        reader.TransferRoots()
        nb_shapes = reader.NbShapes()
        
        if nb_shapes == 0:
            raise ValueError("No shapes found in STEP file")
        
        # Get the first shape (or combine all shapes)
        shape = reader.OneShape()
        
        # Mesh the shape with lower precision for simpler meshes
        # Lower linear deflection = coarser mesh (1.0 for even simpler meshes)
        # This reduces polygon count significantly for better web performance
        # Higher value = fewer polygons = better performance
        mesh = BRepMesh_IncrementalMesh(shape, 1.0, False, 1.0, True)
        mesh.Perform()
        
        # Write to STL
        writer = StlAPI_Writer()
        writer.SetASCIIMode(False)  # Binary STL
        success = writer.Write(shape, str(output_path))
        
        if not success:
            raise ValueError(f"Failed to write STL file: {output_path}")
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValueError(f"STL file was not created or is empty: {output_path}")
        
        logger.info(f"Successfully converted STEP to STL using pythonocc-core: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"pythonocc-core conversion failed: {e}", exc_info=True)
        raise ValueError(f"STEP conversion via pythonocc-core failed: {str(e)}")


def convert_step_file(step_file_path, output_format='stl'):
    """
    Convert STEP file to STL/OBJ using CloudConvert API.
    
    Args:
        step_file_path: Path to STEP file
        output_format: 'stl' or 'obj'
    
    Returns:
        Path to converted file (temporary location)
    """
    # Only use CloudConvert if API key is configured
    if not CLOUDCONVERT_API_KEY:
        raise ValueError(
            "CloudConvert API key not configured. Set CLOUDCONVERT_API_KEY environment variable.\n"
            "Get your API key from: https://cloudconvert.com/"
        )
    
    logger.info("Converting STEP file via CloudConvert...")
    return convert_step_via_cloudconvert(step_file_path, output_format)


class CADProcessor:
    """Process CAD files (GLB/GLTF, STEP, STL, OBJ) and extract geometry data"""
    
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.mesh = None
        self.geometry_data = {}
        self._converted_step_file = None  # Store converted OBJ/STL from STEP
        
    def process(self):
        """Process CAD file and extract geometry data"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        extension = self.file_path.suffix.lower()
        
        # Supported formats
        supported_formats = ['.glb', '.gltf', '.step', '.stp', '.stl', '.obj']
        if extension not in supported_formats:
            raise ValueError(f"Unsupported file format. Supported: {', '.join(supported_formats)}. Got: {extension}")
        
        # For STEP files, convert using pythonocc-core or FreeCAD first
        if extension in ['.step', '.stp']:
            self._convert_step_file()
            # After conversion, process the OBJ/STL file
            if self._converted_step_file and self._converted_step_file.exists():
                # Temporarily replace file_path with converted file for processing
                original_path = self.file_path
                self.file_path = self._converted_step_file
                try:
                    result = self._process_with_trimesh() if TRIMESH_AVAILABLE else self._process_basic()
                    return result
                finally:
                    self.file_path = original_path
            else:
                raise ValueError("STEP file conversion failed - no converted file available")
        
        # Use trimesh for processing other formats
        if TRIMESH_AVAILABLE:
            return self._process_with_trimesh()
        else:
            logger.warning("trimesh not available, using basic processing")
            return self._process_basic()
    
    def _convert_step_file(self):
        """Convert STEP file using available method (pythonocc-core or FreeCAD)"""
        try:
            # Convert STEP to STL (works with both pythonocc and FreeCAD)
            logger.info(f"Starting STEP to STL conversion for: {self.file_path}")
            self._converted_step_file = convert_step_file(self.file_path, 'stl')
            if not self._converted_step_file or not self._converted_step_file.exists():
                raise ValueError(f"STEP conversion completed but output file not found: {self._converted_step_file}")
            logger.info(f"STEP file converted to STL: {self._converted_step_file} ({self._converted_step_file.stat().st_size / 1024:.2f} KB)")
        except Exception as e:
            logger.error(f"Failed to convert STEP file: {e}", exc_info=True)
            raise ValueError(f"STEP file conversion failed: {str(e)}")
    
    def _process_with_trimesh(self):
        """Process CAD file using trimesh (supports GLB/GLTF, STL, OBJ)"""
        try:
            extension = self.file_path.suffix.lower()
            
            # Load mesh with trimesh
            # Trimesh can handle: GLB/GLTF, STL, OBJ natively
            # STEP files are converted via CloudConvert or pre-converted before reaching here
            try:
                self.mesh = trimesh.load(str(self.file_path))
            except Exception as load_error:
                logger.error(f"Failed to load file with trimesh: {load_error}")
                raise ValueError(f"Failed to load {extension} file: {load_error}")
            
            # Handle scene (multiple meshes)
            if isinstance(self.mesh, trimesh.Scene):
                # Combine all meshes
                mesh_list = []
                for node_name in self.mesh.graph.nodes_geometry:
                    transform, geometry_name = self.mesh.graph[node_name]
                    geometry = self.mesh.geometry[geometry_name]
                    if isinstance(geometry, trimesh.Trimesh):
                        mesh_list.append(geometry.copy())
                if mesh_list:
                    self.mesh = trimesh.util.concatenate(mesh_list)
            
            # Handle single mesh
            if not isinstance(self.mesh, trimesh.Trimesh):
                raise ValueError(f"Could not extract mesh from file. Got type: {type(self.mesh)}")
            
            # Simplify mesh early for better performance
            # Target: 500 faces for maximum smoothness
            target_faces = 500
            if len(self.mesh.faces) > target_faces:
                try:
                    logger.info(f"Simplifying mesh during processing: {len(self.mesh.faces)} -> {target_faces} faces")
                    simplified = self.mesh.simplify_quadric_decimation(face_count=target_faces)
                    if simplified is not None and len(simplified.faces) > 0:
                        self.mesh = simplified
                        logger.info(f"Mesh simplified to {len(self.mesh.faces)} faces")
                except Exception as e:
                    logger.warning(f"Early simplification failed: {e}, continuing with original")
            
            if not hasattr(self.mesh, 'bounds'):
                raise ValueError("Could not extract mesh bounds")
            
            bounds = self.mesh.bounds
            center = self.mesh.centroid
            volume = self.mesh.volume if hasattr(self.mesh, 'volume') else 0.0
            
            self.geometry_data = {
                'bounding_box': {
                    'min': bounds[0].tolist(),
                    'max': bounds[1].tolist(),
                    'center': center.tolist(),
                },
                'volume': abs(volume),
                'center': center.tolist(),
                'connection_points': self._extract_connection_points(),
            }
            
            return self.geometry_data
            
        except Exception as e:
            logger.error(f"Error processing file with trimesh: {e}")
            return self._process_basic()
    
    def _extract_connection_points(self):
        """Extract connection points from CAD mesh"""
        connection_points = []
        try:
            if self.mesh and hasattr(self.mesh, 'bounds'):
                bounds = self.mesh.bounds
                center = self.mesh.centroid
                
                # Extract bounding box connection points
                connection_points = [
                    {'position': bounds[0].tolist(), 'normal': [0, 0, -1], 'side': 'bottom'},
                    {'position': bounds[1].tolist(), 'normal': [0, 0, 1], 'side': 'top'},
                    {'position': [bounds[0][0], bounds[0][1], center[2]], 'normal': [-1, 0, 0], 'side': 'left'},
                    {'position': [bounds[1][0], bounds[1][1], center[2]], 'normal': [1, 0, 0], 'side': 'right'},
                    {'position': [center[0], bounds[0][1], center[2]], 'normal': [0, -1, 0], 'side': 'front'},
                    {'position': [center[0], bounds[1][1], center[2]], 'normal': [0, 1, 0], 'side': 'back'},
                ]
        except Exception as e:
            logger.error(f"Error extracting connection points from mesh: {e}")
        
        return connection_points
    
    def _process_basic(self):
        """Basic fallback processing when trimesh is not available"""
        logger.warning(f"Using basic processing for {self.file_path}")
        # Return default values
        self.geometry_data = {
            'bounding_box': {
                'min': [0, 0, 0],
                'max': [1, 1, 1],
                'center': [0.5, 0.5, 0.5],
            },
            'volume': 1.0,
            'center': [0.5, 0.5, 0.5],
            'connection_points': [],
        }
        return self.geometry_data
    
    def convert_to_glb(self, output_path):
        """Convert CAD file to GLB format for web visualization"""
        output_path = Path(output_path)
        extension = self.file_path.suffix.lower()
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # If already GLB/GLTF, just copy
        if extension in ['.glb', '.gltf']:
            shutil.copy(self.file_path, output_path)
            logger.info(f"Copied GLB/GLTF file to {output_path}")
            return output_path

        # For STEP files, use the converted OBJ/STL file if available
        if extension in ['.step', '.stp'] and self._converted_step_file and self._converted_step_file.exists():
            # Use the converted file for GLB conversion
            original_path = self.file_path
            original_mesh = self.mesh
            self.file_path = self._converted_step_file
            try:
                # Load mesh from converted file if not already loaded
                if self.mesh is None:
                    if not TRIMESH_AVAILABLE:
                        raise ValueError("trimesh is required for format conversion")
                    try:
                        self.mesh = trimesh.load(str(self._converted_step_file))
                    except Exception as e:
                        raise ValueError(f"Failed to load converted file for GLB conversion: {e}")
                result = self._convert_mesh_to_glb(output_path)
                return result
            finally:
                self.file_path = original_path
                self.mesh = original_mesh
        
        # For other formats (STL, OBJ), convert to GLB using trimesh
        if not TRIMESH_AVAILABLE:
            raise ValueError("trimesh is required for format conversion")
        
        if self.mesh is None:
            # Load mesh if not already loaded
            try:
                self.mesh = trimesh.load(str(self.file_path))
            except Exception as e:
                raise ValueError(f"Failed to load file for conversion: {e}")
        
        return self._convert_mesh_to_glb(output_path)
    
    def _convert_mesh_to_glb(self, output_path):
        """Convert loaded mesh to GLB format with simplification for web performance"""
        if not TRIMESH_AVAILABLE:
            raise ValueError("trimesh is required for GLB conversion")
        
        if self.mesh is None:
            raise ValueError("No mesh loaded for conversion")
        
        # Handle scene (multiple meshes)
        if isinstance(self.mesh, trimesh.Scene):
            # Combine all meshes
            mesh_list = []
            for node_name in self.mesh.graph.nodes_geometry:
                transform, geometry_name = self.mesh.graph[node_name]
                geometry = self.mesh.geometry[geometry_name]
                if isinstance(geometry, trimesh.Trimesh):
                    mesh_list.append(geometry.copy())
            if mesh_list:
                self.mesh = trimesh.util.concatenate(mesh_list)
        
        # Ensure we have a Trimesh object
        if not isinstance(self.mesh, trimesh.Trimesh):
            raise ValueError(f"Cannot convert to GLB. Got type: {type(self.mesh)}")
        
        # Simplify mesh for web performance
        # Target face count: 500 faces for maximum smoothness
        # This provides acceptable visual quality while ensuring very smooth rendering
        target_face_count = 500
        original_face_count = len(self.mesh.faces)
        
        if original_face_count > target_face_count:
            try:
                logger.info(f"Simplifying mesh: {original_face_count} faces -> target: {target_face_count} faces")
                
                # Use quadric decimation for high-quality simplification
                # Simplify the mesh
                simplified = self.mesh.simplify_quadric_decimation(face_count=target_face_count)
                
                if simplified is not None and len(simplified.faces) > 0:
                    self.mesh = simplified
                    logger.info(f"Mesh simplified: {original_face_count} -> {len(self.mesh.faces)} faces ({len(self.mesh.faces)/original_face_count*100:.1f}% of original)")
                else:
                    logger.warning(f"Simplification failed, using original mesh with {original_face_count} faces")
            except Exception as e:
                logger.warning(f"Mesh simplification failed: {e}, using original mesh")
                # Continue with original mesh if simplification fails
        
        # Export to GLB
        try:
            extension = self.file_path.suffix.lower()
            # Trimesh can export to GLB directly
            self.mesh.export(str(output_path), file_type='glb')
            logger.info(f"Converted {extension} file to GLB: {output_path} ({len(self.mesh.faces)} faces)")
            return output_path
        except Exception as e:
            logger.error(f"Failed to export to GLB: {e}")
            raise ValueError(f"Failed to convert to GLB: {e}")


def process_cad_file(file_path, extract_geometry=True, copy_glb_to=None):
    """
    Main function to process a CAD file (GLB/GLTF, STEP, STL, OBJ).
    Converts all formats to GLB for web visualization.
    
    Args:
        file_path: Path to CAD file (GLB/GLTF, STEP, STL, OBJ)
        extract_geometry: Whether to extract geometry data
        copy_glb_to: Optional output path for GLB file (converted if needed)
    
    Returns:
        dict with geometry_data and optionally glb_path
    """
    processor = CADProcessor(file_path)
    
    result = {
        'geometry_data': None,
        'glb_path': None,
    }
    
    if extract_geometry:
        result['geometry_data'] = processor.process()
    
    if copy_glb_to:
        result['glb_path'] = processor.convert_to_glb(copy_glb_to)
    
    return result


# Backward compatibility alias
def process_glb_file(file_path, extract_geometry=True, copy_glb_to=None):
    """
    Alias for process_cad_file for backward compatibility.
    Now supports all CAD formats, not just GLB/GLTF.
    """
    return process_cad_file(file_path, extract_geometry, copy_glb_to)
