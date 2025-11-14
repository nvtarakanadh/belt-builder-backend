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

# CloudConvert API for STEP conversion (NOT SUPPORTED - CloudConvert doesn't support STEP)
# This is kept for reference but STEP conversion is not available
CLOUDCONVERT_API_KEY = getattr(settings, 'CLOUDCONVERT_API_KEY', None)
CLOUDCONVERT_API_URL = 'https://api.cloudconvert.com/v2'


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
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        raise ValueError(
            "STEP file conversion requires FreeCAD Docker container.\n\n"
            "Setup options:\n"
            "1. Deploy FreeCAD Docker service (see Dockerfile.freecad)\n"
            "2. Set FREECAD_DOCKER_URL environment variable to point to the service\n"
            "3. Or pre-convert STEP files to STL/OBJ before uploading\n\n"
            "For now, please convert your STEP file to STL or OBJ format before uploading."
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
            raise ValueError(f"FreeCAD Docker conversion failed: {result.stderr}")
        
        if not output_path.exists():
            raise ValueError(f"Converted file not found: {output_path}")
        
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
    
    NOTE: CloudConvert does NOT support STEP format conversion.
    This function is kept for reference but will not work.
    """
    # CloudConvert does not support STEP format
    raise ValueError(
        "CloudConvert does not support STEP format conversion.\n"
        "Please use FreeCAD Docker service or pre-convert STEP files."
    )


def convert_step_file(step_file_path, output_format='stl'):
    """
    Convert STEP file to STL/OBJ using FreeCAD Docker (deployment-friendly).
    
    This function attempts to use FreeCAD in a Docker container for conversion.
    The Docker container can be deployed alongside the main application.
    
    Args:
        step_file_path: Path to STEP file
        output_format: 'stl' or 'obj'
    
    Returns:
        Path to converted file (temporary location)
    """
    # Try FreeCAD Docker first (deployment-friendly)
    try:
        return convert_step_via_freecad_docker(step_file_path, output_format)
    except Exception as e:
        logger.error(f"FreeCAD Docker conversion failed: {e}")
        # If Docker is not available, provide helpful error message
        raise ValueError(
            f"STEP file conversion is not available.\n\n"
            f"Error: {str(e)}\n\n"
            f"SOLUTION: Please pre-convert your STEP file to STL or OBJ format before uploading.\n\n"
            f"You can use:\n"
            f"1. FreeCAD (free): https://www.freecad.org/\n"
            f"2. Online converters (search for 'STEP to STL converter')\n"
            f"3. Other CAD software\n\n"
            f"After conversion, upload the STL or OBJ file instead of the STEP file."
        )


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
        """Convert loaded mesh to GLB format"""
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
        
        # Export to GLB
        try:
            extension = self.file_path.suffix.lower()
            # Trimesh can export to GLB directly
            self.mesh.export(str(output_path), file_type='glb')
            logger.info(f"Converted {extension} file to GLB: {output_path}")
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
