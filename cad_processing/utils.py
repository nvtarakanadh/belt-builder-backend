"""
CAD processing utilities for geometry extraction and file conversion.
Supports multiple backends: pythonocc, trimesh, FreeCAD (if available).
"""
import os
import logging
from pathlib import Path
try:
    import numpy as np  # optional; not required for basic processing
except Exception:  # pragma: no cover
    np = None

logger = logging.getLogger(__name__)

try:
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.IFSelect import IFSelect_ItemsByEntity
    from OCC.Core.STEPControl_Reader import STEPControl_Reader
    from OCC.Core.Interface import Interface_Static_SetCVal
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Vec
    from OCC.Core.BRepTools import breptools
    PYTHONOCC_AVAILABLE = True
except ImportError:
    PYTHONOCC_AVAILABLE = False
    logger.warning("pythonocc-core not available. Using alternative CAD processing.")

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    logger.warning("trimesh not available.")

try:
    import pygltflib
    PYGLTF_AVAILABLE = True
except ImportError:
    PYGLTF_AVAILABLE = False
    logger.warning("pygltflib not available.")


class CADProcessor:
    """Main CAD processing class with multiple backend support"""
    
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.mesh = None
        self.geometry_data = {}
        
    def process(self):
        """Process CAD file and extract geometry data"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        extension = self.file_path.suffix.lower()
        
        # Try pythonocc for STEP files
        if extension in ['.step', '.stp'] and PYTHONOCC_AVAILABLE:
            return self._process_with_pythonocc()
        
        # Use trimesh for STL, OBJ, GLB
        if extension in ['.stl', '.obj', '.glb', '.gltf'] and TRIMESH_AVAILABLE:
            return self._process_with_trimesh()
        
        # Fallback to basic processing
        return self._process_basic()
    
    def _process_with_pythonocc(self):
        """Process STEP file using pythonocc"""
        try:
            reader = STEPControl_Reader()
            status = reader.ReadFile(str(self.file_path))
            
            if status != IFSelect_RetDone:
                raise ValueError(f"Error reading STEP file: {status}")
            
            reader.TransferRoots()
            shape = reader.OneShape()
            
            # Calculate bounding box
            bbox = Bnd_Box()
            brepbndlib.Add(shape, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            
            # Calculate volume and center
            props = GProp_GProps()
            brepgprop.VolumeProperties(shape, props)
            mass_center = props.CentreOfMass()
            volume = props.Mass()
            
            self.geometry_data = {
                'bounding_box': {
                    'min': [xmin, ymin, zmin],
                    'max': [xmax, ymax, zmax],
                    'center': [mass_center.X(), mass_center.Y(), mass_center.Z()],
                },
                'volume': volume,
                'center': [mass_center.X(), mass_center.Y(), mass_center.Z()],
                'connection_points': self._extract_connection_points_pythonocc(shape),
            }
            
            return self.geometry_data
            
        except Exception as e:
            logger.error(f"Error processing with pythonocc: {e}")
            if TRIMESH_AVAILABLE:
                return self._process_with_trimesh()
            raise
    
    def _process_with_trimesh(self):
        """Process mesh files using trimesh"""
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
                'connection_points': self._extract_connection_points_trimesh(),
            }
            
            return self.geometry_data
            
        except Exception as e:
            logger.error(f"Error processing with trimesh: {e}")
            return self._process_basic()
    
    def _process_basic(self):
        """Basic fallback processing"""
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
    
    def _extract_connection_points_pythonocc(self, shape):
        """Extract potential connection points from STEP geometry"""
        connection_points = []
        try:
            # Explore faces
            explorer = TopExp_Explorer(shape, TopAbs_FACE)
            face_count = 0
            
            while explorer.More() and face_count < 20:  # Limit to first 20 faces
                face = explorer.Current()
                # Get face center and normal (simplified)
                # In production, would use BRepGProp_SurfaceProperties
                face_count += 1
                explorer.Next()
            
            # For now, extract bounding box corners as potential connection points
            if self.geometry_data.get('bounding_box'):
                bbox = self.geometry_data['bounding_box']
                min_pt = bbox['min']
                max_pt = bbox['max']
                
                # Add corner points
                connection_points.extend([
                    {'position': min_pt, 'normal': [0, 0, -1], 'side': 'bottom'},
                    {'position': max_pt, 'normal': [0, 0, 1], 'side': 'top'},
                    {'position': [min_pt[0], min_pt[1], bbox['center'][2]], 'normal': [-1, 0, 0], 'side': 'left'},
                    {'position': [max_pt[0], max_pt[1], bbox['center'][2]], 'normal': [1, 0, 0], 'side': 'right'},
                ])
                
        except Exception as e:
            logger.error(f"Error extracting connection points: {e}")
        
        return connection_points
    
    def _extract_connection_points_trimesh(self):
        """Extract connection points from mesh"""
        connection_points = []
        try:
            if self.mesh and hasattr(self.mesh, 'bounds'):
                bounds = self.mesh.bounds
                center = self.mesh.centroid
                
                # Extract face normals (simplified - would analyze actual faces in production)
                # Add bounding box connection points
                connection_points = [
                    {'position': bounds[0].tolist(), 'normal': [0, 0, -1], 'side': 'bottom'},
                    {'position': bounds[1].tolist(), 'normal': [0, 0, 1], 'side': 'top'},
                    {'position': [bounds[0][0], bounds[0][1], center[2]], 'normal': [-1, 0, 0], 'side': 'left'},
                    {'position': [bounds[1][0], bounds[1][1], center[2]], 'normal': [1, 0, 0], 'side': 'right'},
                ]
        except Exception as e:
            logger.error(f"Error extracting connection points from mesh: {e}")
        
        return connection_points
    
    def _try_freecad_convert(self, output_path: Path):
        """Attempt STEP->STL->GLB via FreeCAD command if available."""
        try:
            import shutil
            freecad_cmd = shutil.which('freecadcmd') or shutil.which('FreeCADCmd')
            if not freecad_cmd:
                return None
            temp_stl = output_path.with_suffix('.stl')
            # Create a small FreeCAD script to convert STEP->STL
            script = f"""
import FreeCAD
import Mesh
import Import
shape = Import.insert(r'{str(self.file_path)}', 'Unnamed')
doc = FreeCAD.getDocument('Unnamed')
objs = doc.Objects
__objs__=[]
for o in objs:
    __objs__.append(o)
Mesh.export(__objs__, r'{str(temp_stl)}')
"""
            script_path = output_path.with_suffix('.py')
            script_path.write_text(script)
            import subprocess
            subprocess.run([freecad_cmd, str(script_path)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if temp_stl.exists():
                # Load STL and export GLB via trimesh
                if TRIMESH_AVAILABLE:
                    self.file_path = temp_stl
                    self.mesh = None
                    self._process_with_trimesh()
                    self.mesh.export(str(output_path), file_type='glb')
                    return output_path
        except Exception as e:
            logger.error(f"FreeCAD conversion failed: {e}")
        return None

    def copy_glb_file(self, output_path):
        """Copy GLB/GLTF file to output path (no conversion needed)"""
        output_path = Path(output_path)
        
        # Ensure the file is GLB/GLTF
        if self.file_path.suffix.lower() not in ['.glb', '.gltf']:
            raise ValueError(f"Expected GLB/GLTF file, got {self.file_path.suffix}")
        
        import shutil
        shutil.copy(self.file_path, output_path)
        logger.info(f"Copied GLB file to {output_path}")
        return output_path
    
    def _create_placeholder_glb(self, output_path):
        """Create a simple placeholder GLB file using trimesh"""
        try:
            if TRIMESH_AVAILABLE:
                # Create a simple box as placeholder
                import trimesh
                box = trimesh.creation.box(extents=[1, 1, 1])
                box.export(str(output_path), file_type='glb')
                if Path(output_path).exists():
                    logger.info(f"Created placeholder GLB at {output_path}")
                    return output_path
        except Exception as e:
            logger.error(f"Failed to create placeholder GLB: {e}")
        logger.warning("Placeholder GLB creation failed, returning path anyway")
        return output_path


def process_cad_file(file_path, extract_geometry=True, copy_glb_to=None):
    """
    Main function to process a GLB/GLTF file (no conversion needed).
    
    Args:
        file_path: Path to GLB/GLTF file
        extract_geometry: Whether to extract geometry data
        copy_glb_to: Optional output path for GLB file copy
    
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
        result['glb_path'] = processor.copy_glb_file(copy_glb_to)
    
    return result


def convert_step_to_glb(step_path: str, glb_path: str = None) -> str:
    """
    Convert a STEP (.step/.stp) file to GLB using FreeCAD command line.

    Args:
        step_path: input STEP file path
        glb_path: optional output GLB path; if not provided, same name with .glb

    Returns:
        Path to created GLB file
    """
    import subprocess
    import tempfile
    import shutil
    from pathlib import Path

    step_path = str(Path(step_path).resolve())
    if glb_path is None:
        glb_path = str(Path(step_path).with_suffix('.glb'))
    else:
        glb_path = str(Path(glb_path).resolve())

    # locate freecad command
    freecad_cmd = shutil.which('freecadcmd') or shutil.which('FreeCADCmd')
    if not freecad_cmd:
        raise RuntimeError('FreeCAD command not found (freecadcmd/FreeCADCmd)')

    # Write temp script
    script_content = f"""
import FreeCAD, Part, ImportGui, Import, Mesh
doc = FreeCAD.newDocument()
ImportGui.insert(r"{step_path}", "Unnamed")
objs = FreeCAD.getDocument("Unnamed").Objects
Mesh.export(objs, r"{glb_path}")
FreeCAD.closeDocument("Unnamed")
"""
    temp_script = Path(tempfile.gettempdir()) / 'convert_fc.py'
    temp_script.write_text(script_content)

    completed = subprocess.run([freecad_cmd, str(temp_script)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if Path(glb_path).exists():
        return glb_path
    raise RuntimeError('GLB not created by FreeCAD')

