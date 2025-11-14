# STEP to GLB Converter API

A Django-based API endpoint that converts STEP (.step, .stp) CAD files to GLB (binary glTF) format for web visualization.

## Features

- ✅ **Free & Open Source**: Uses only open-source libraries (pythonocc-core, trimesh, pygltflib)
- ✅ **Self-Hosted**: Everything runs locally, no external APIs
- ✅ **Production Ready**: Handles errors, cleanup, and file management
- ✅ **Three.js Compatible**: Output GLB files work with Three.js GLTFLoader

## Architecture

The conversion process follows these steps:

1. **STEP → STL**: Uses `pythonocc-core` (OpenCASCADE) to read STEP files and tessellate to STL
2. **STL → GLB**: Uses `trimesh` to load STL and export as GLB (binary glTF)

## Installation

### Prerequisites

#### Linux (Ubuntu/Debian)

```bash
# Install OpenCASCADE libraries (required for pythonocc-core)
sudo apt-get update
sudo apt-get install -y \
    libocct-foundation-dev \
    libocct-modeling-dev \
    libocct-visualization-dev \
    libocct-data-exchange-dev \
    libocct-ocaf-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libx11-dev \
    libxext-dev \
    libxrender-dev \
    libgl1-mesa-glx \
    libglu1-mesa
```

#### Windows

pythonocc-core is difficult to install on Windows. Options:

1. **Use WSL2 (Recommended)**: Install Ubuntu in WSL2 and follow Linux instructions
2. **Use Conda**: `conda install -c conda-forge pythonocc-core`
3. **Use Docker**: Use the provided Dockerfile (recommended for production)

#### macOS

```bash
# Install OpenCASCADE via Homebrew
brew install opencascade

# Then install pythonocc-core
pip install pythonocc-core
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `pythonocc-core>=7.7.0` - STEP file reading and STL export
- `trimesh>=3.23.5` - STL to GLB conversion
- `pygltflib>=1.15.5` - GLB file format support
- `numpy>=1.26.2` - Numerical operations

## Usage

### API Endpoint

**POST** `/api/convert/step/`

### Request

- **Content-Type**: `multipart/form-data`
- **Field**: `file` (STEP file with `.step` or `.stp` extension)

### Example with curl

```bash
curl -X POST \
  -F "file=@sample.step" \
  http://127.0.0.1:8000/api/convert/step/
```

### Example with Python requests

```python
import requests

url = "http://127.0.0.1:8000/api/convert/step/"
files = {"file": open("sample.step", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

### Response (Success)

```json
{
  "ok": true,
  "message": "Converted successfully",
  "glb_url": "/media/converted/model_a1b2c3d4.glb",
  "sizeMB": 3.5
}
```

### Response (Error)

```json
{
  "ok": false,
  "error": "Error message here"
}
```

## Using the GLB in Three.js

Once you have the `glb_url`, you can load it in Three.js:

```javascript
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
const glbUrl = 'http://your-server.com/media/converted/model_a1b2c3d4.glb';

loader.load(glbUrl, (gltf) => {
  const model = gltf.scene;
  scene.add(model);
  
  // Optional: Auto-fit camera
  const box = new THREE.Box3().setFromObject(model);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  
  camera.position.set(
    center.x + size.x,
    center.y + size.y,
    center.z + size.z
  );
  camera.lookAt(center);
}, undefined, (error) => {
  console.error('Error loading GLB:', error);
});
```

## Docker Deployment

For production deployment, use the provided Dockerfile:

```bash
# Build image
docker build -f Dockerfile.converter -t step-converter:latest .

# Run container
docker run -p 8000:8000 \
  -v $(pwd)/media:/app/media \
  -e SECRET_KEY=your-secret-key \
  step-converter:latest
```

The Dockerfile includes all system dependencies for pythonocc-core.

## Configuration

### Media Storage

Converted GLB files are saved to `MEDIA_ROOT/converted/` by default.

To use S3 storage, configure in `settings.py`:

```python
USE_S3 = True
AWS_STORAGE_BUCKET_NAME = 'your-bucket'
# ... other S3 settings
```

### File Size Limits

Default max file size is 100MB. Adjust in `settings.py`:

```python
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 MB
```

## Troubleshooting

### pythonocc-core Installation Fails

**Linux**: Make sure all OpenCASCADE development libraries are installed (see Prerequisites)

**Windows**: Use WSL2 or Docker instead

**macOS**: Install OpenCASCADE via Homebrew first

### Conversion Fails with "No valid geometry"

- The STEP file might be corrupted
- The STEP file might use unsupported features
- Try opening the STEP file in FreeCAD or another CAD viewer to verify it's valid

### GLB File is Too Large

- Adjust mesh quality in `converter/views.py`:
  ```python
  mesh_deviation = 0.1  # Lower = higher quality (larger file)
  ```
- Lower values (0.05) = higher quality, larger files
- Higher values (0.2) = lower quality, smaller files

### Memory Issues

For large STEP files, consider:
- Increasing Docker container memory limits
- Processing files asynchronously with Celery
- Using a more powerful server

## Performance

- **Small files (< 10MB)**: ~2-5 seconds
- **Medium files (10-50MB)**: ~5-15 seconds
- **Large files (> 50MB)**: ~15-60 seconds

Performance depends on:
- File complexity (number of faces)
- Server CPU/RAM
- Mesh quality settings

## License

This converter uses open-source libraries:
- pythonocc-core: LGPL-3.0
- trimesh: MIT
- pygltflib: MIT

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed correctly
3. Check Django logs for detailed error messages


