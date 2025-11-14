#!/usr/bin/env python3
"""
FreeCAD headless STEP to STL/OBJ converter
Can be run as a standalone service or called via subprocess
"""
import sys
import os
import argparse
from pathlib import Path

# Add FreeCAD Python modules to path
# FreeCAD installs its Python modules in different locations depending on installation
freecad_paths = [
    '/usr/lib/freecad/lib',
    '/usr/lib/freecad-python3/lib',
    '/usr/lib/freecad-daily/lib',
    '/opt/freecad/lib',
]

for path in freecad_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)

# Try to import FreeCAD modules
try:
    import FreeCAD
    import Part
    import Mesh
    FREECAD_AVAILABLE = True
except ImportError:
    # Try alternative import method
    try:
        # FreeCAD might be installed as a system package
        import freecad
        import freecad.Part
        import freecad.Mesh
        FREECAD_AVAILABLE = True
    except ImportError:
        FREECAD_AVAILABLE = False
        print("ERROR: FreeCAD Python modules not available", file=sys.stderr)
        print(f"Python path: {sys.path}", file=sys.stderr)
        print(f"Tried paths: {freecad_paths}", file=sys.stderr)
        sys.exit(1)


def convert_step_to_stl(step_file, output_file, mesh_deviation=0.1):
    """
    Convert STEP file to STL using FreeCAD
    
    Args:
        step_file: Path to input STEP file
        output_file: Path to output STL file
        mesh_deviation: Mesh quality (smaller = higher quality, default 0.1)
    """
    try:
        # Open FreeCAD document
        doc = FreeCAD.newDocument("Conversion")
        
        # Import STEP file - Part.read() returns a shape or list of shapes
        import_result = Part.read(str(step_file))
        
        # Handle single shape or list of shapes
        if isinstance(import_result, list):
            shapes = import_result
        else:
            shapes = [import_result]
        
        # Create mesh from all shapes
        mesh_objects = []
        for i, shape in enumerate(shapes):
            if shape.isNull():
                continue
            
            # Create part object
            part = doc.addObject("Part::Feature", f"ImportedPart{i}")
            part.Shape = shape
            
            # Create mesh from shape using tessellate
            # tessellate returns (vertices, faces) where faces are indices
            vertices, face_indices = part.Shape.tessellate(mesh_deviation)
            
            # Convert face indices to triangle list for Mesh.Mesh()
            # Each face is a list of vertex indices, convert to triangles
            triangles = []
            for face in face_indices:
                # Triangulate polygon face (fan triangulation)
                if len(face) >= 3:
                    for j in range(1, len(face) - 1):
                        triangles.append([face[0], face[j], face[j+1]])
            
            # Create mesh object
            mesh_obj = doc.addObject("Mesh::Feature", f"Mesh{i}")
            # Mesh.Mesh() takes list of triangles (each triangle is 3 vertex indices)
            mesh_obj.Mesh = Mesh.Mesh([(vertices[v[0]], vertices[v[1]], vertices[v[2]]) for v in triangles])
            mesh_objects.append(mesh_obj)
        
        if not mesh_objects:
            raise ValueError("No valid shapes found in STEP file")
        
        # Export all meshes to single STL file
        if len(mesh_objects) == 1:
            mesh_objects[0].Mesh.write(str(output_file))
        else:
            # Combine multiple meshes
            combined_mesh = mesh_objects[0].Mesh
            for mesh_obj in mesh_objects[1:]:
                combined_mesh.addMesh(mesh_obj.Mesh)
            combined_mesh.write(str(output_file))
        
        # Close document
        FreeCAD.closeDocument(doc.Name)
        
        print(f"SUCCESS: Converted {step_file} to {output_file}")
        return True
        
    except Exception as e:
        print(f"ERROR: Conversion failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        if 'doc' in locals():
            try:
                FreeCAD.closeDocument(doc.Name)
            except:
                pass
        return False


def convert_step_to_obj(step_file, output_file, mesh_deviation=0.1):
    """
    Convert STEP file to OBJ using FreeCAD
    
    Args:
        step_file: Path to input STEP file
        output_file: Path to output OBJ file
        mesh_deviation: Mesh quality (smaller = higher quality, default 0.1)
    """
    try:
        # Open FreeCAD document
        doc = FreeCAD.newDocument("Conversion")
        
        # Import STEP file
        shape = Part.Shape()
        shape.read(str(step_file))
        part = doc.addObject("Part::Feature", "ImportedPart")
        part.Shape = shape
        
        # Create mesh from shape
        mesh = part.Shape.tessellate(mesh_deviation)
        mesh_obj = doc.addObject("Mesh::Feature", "Mesh")
        mesh_obj.Mesh = Mesh.Mesh(mesh)
        
        # Export to OBJ (FreeCAD can export mesh to OBJ)
        import Mesh
        Mesh.export([mesh_obj], str(output_file))
        
        # Close document
        FreeCAD.closeDocument(doc.Name)
        
        print(f"SUCCESS: Converted {step_file} to {output_file}")
        return True
        
    except Exception as e:
        print(f"ERROR: Conversion failed: {e}", file=sys.stderr)
        if 'doc' in locals():
            try:
                FreeCAD.closeDocument(doc.Name)
            except:
                pass
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert STEP files to STL or OBJ using FreeCAD')
    parser.add_argument('input', help='Input STEP file path')
    parser.add_argument('output', help='Output STL or OBJ file path')
    parser.add_argument('--format', choices=['stl', 'obj'], default='stl', help='Output format (default: stl)')
    parser.add_argument('--quality', type=float, default=0.1, help='Mesh quality (0.01-1.0, smaller = higher quality)')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert based on format
    if args.format == 'stl':
        success = convert_step_to_stl(input_path, output_path, args.quality)
    else:
        success = convert_step_to_obj(input_path, output_path, args.quality)
    
    sys.exit(0 if success else 1)


