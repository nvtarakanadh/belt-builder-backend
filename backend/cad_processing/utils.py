"""
GLB/GLTF file processing utilities for geometry extraction.
Only supports GLB/GLTF files directly (no CAD conversion).
"""
import logging
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    logger.warning("trimesh not available. Geometry extraction will be limited.")


class GLBProcessor:
    """Process GLB/GLTF files and extract geometry data"""
    
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.mesh = None
        self.geometry_data = {}
        
    def process(self):
        """Process GLB/GLTF file and extract geometry data"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        extension = self.file_path.suffix.lower()
        
        if extension not in ['.glb', '.gltf']:
            raise ValueError(f"Only GLB/GLTF files are supported. Got: {extension}")
        
        # Use trimesh for GLB/GLTF processing
        if TRIMESH_AVAILABLE:
            return self._process_with_trimesh()
        else:
            logger.warning("trimesh not available, using basic processing")
            return self._process_basic()
    
    def _process_with_trimesh(self):
        """Process GLB/GLTF file using trimesh"""
        try:
            self.mesh = trimesh.load(str(self.file_path))
            
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
            logger.error(f"Error processing GLB with trimesh: {e}")
            return self._process_basic()
    
    def _extract_connection_points(self):
        """Extract connection points from GLB mesh"""
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
    
    def copy_glb_file(self, output_path):
        """Copy GLB/GLTF file to output path (no conversion needed)"""
        output_path = Path(output_path)
        
        # Ensure the file is GLB/GLTF
        if self.file_path.suffix.lower() not in ['.glb', '.gltf']:
            raise ValueError(f"Expected GLB/GLTF file, got {self.file_path.suffix}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        shutil.copy(self.file_path, output_path)
        logger.info(f"Copied GLB file to {output_path}")
        return output_path


def process_glb_file(file_path, extract_geometry=True, copy_glb_to=None):
    """
    Main function to process a GLB/GLTF file (no conversion needed).
    
    Args:
        file_path: Path to GLB/GLTF file
        extract_geometry: Whether to extract geometry data
        copy_glb_to: Optional output path for GLB file copy
    
    Returns:
        dict with geometry_data and optionally glb_path
    """
    processor = GLBProcessor(file_path)
    
    result = {
        'geometry_data': None,
        'glb_path': None,
    }
    
    if extract_geometry:
        result['geometry_data'] = processor.process()
    
    if copy_glb_to:
        result['glb_path'] = processor.copy_glb_file(copy_glb_to)
    
    return result


# Backward compatibility alias (for existing code that uses process_cad_file)
def process_cad_file(file_path, extract_geometry=True, copy_glb_to=None):
    """
    Alias for process_glb_file for backward compatibility.
    Only supports GLB/GLTF files.
    """
    return process_glb_file(file_path, extract_geometry, copy_glb_to)
