# API Usage Examples

This document provides examples of how to use the CAD Builder API.

## Authentication

For now, the API uses Django's session authentication or you can use token authentication. For production, consider using JWT tokens.

## 1. Upload a CAD Component

```bash
curl -X POST http://localhost:8000/api/components/upload/ \
  -H "Content-Type: multipart/form-data" \
  -F "name=Motor" \
  -F "description=Stepper motor component" \
  -F "category_id=1" \
  -F "original_file=@/path/to/motor.step"
```

**Response:**
```json
{
  "id": 1,
  "name": "Motor",
  "description": "Stepper motor component",
  "category": {
    "id": 1,
    "name": "Motor",
    "description": "Motor components"
  },
  "processing_status": "processing",
  "bounding_box": {
    "min": [0, 0, 0],
    "max": [10, 10, 10],
    "center": [5, 5, 5]
  },
  "original_file_url": "http://localhost:8000/media/components/original/motor.step",
  "glb_file_url": "http://localhost:8000/media/components/glb/1.glb"
}
```

## 2. List All Components

```bash
curl http://localhost:8000/api/components/
```

**Query Parameters:**
- `category`: Filter by category ID
- `processing_status`: Filter by status (pending, processing, completed, failed)
- `search`: Search by name

```bash
curl "http://localhost:8000/api/components/?category=1&processing_status=completed&search=motor"
```

## 3. Create a Project

```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Conveyor System",
    "description": "A conveyor belt assembly",
    "is_public": false
  }'
```

## 4. Add Component to Project Assembly

```bash
curl -X POST http://localhost:8000/api/projects/1/add_component/ \
  -H "Content-Type: application/json" \
  -d '{
    "component_id": 1,
    "custom_name": "Motor 1",
    "position_x": 0.0,
    "position_y": 0.0,
    "position_z": 0.0,
    "rotation_x": 0.0,
    "rotation_y": 0.0,
    "rotation_z": 0.0,
    "rotation_w": 1.0,
    "scale_x": 1.0,
    "scale_y": 1.0,
    "scale_z": 1.0
  }'
```

## 5. Get Smart Placement Suggestions

```bash
curl "http://localhost:8000/api/projects/1/placement_suggestions/?component_id=2"
```

**Response:**
```json
{
  "component_id": "2",
  "suggestions": [
    {
      "position": [10.0, 0.0, 0.0],
      "rotation": [0.0, 0.0, 0.0, 1.0],
      "type": "connection",
      "description": "Connect to Motor at top",
      "confidence": 0.9,
      "target_item_id": 1,
      "connection_point": {
        "id": 5,
        "name": "top",
        "position": [5.0, 5.0, 10.0],
        "normal": [0.0, 0.0, 1.0]
      }
    },
    {
      "position": [0.0, 0.0, 15.0],
      "rotation": [0.0, 0.0, 0.0, 1.0],
      "type": "snap_top",
      "description": "Place on top of Motor",
      "confidence": 0.7,
      "target_item_id": 1
    }
  ],
  "count": 2
}
```

## 6. Update Assembly Item Position

```bash
curl -X PATCH http://localhost:8000/api/assembly-items/1/ \
  -H "Content-Type: application/json" \
  -d '{
    "position_x": 5.0,
    "position_y": 10.0,
    "position_z": 0.0
  }'
```

## 7. Save Assembly State

```bash
curl -X POST http://localhost:8000/api/projects/1/save/ \
  -H "Content-Type: application/json" \
  -d '{
    "assembly_items": [
      {
        "id": 1,
        "position_x": 5.0,
        "position_y": 10.0,
        "position_z": 0.0,
        "rotation_x": 0.0,
        "rotation_y": 0.0,
        "rotation_z": 0.0,
        "rotation_w": 1.0
      }
    ]
  }'
```

## 8. Get Project with Assembly

```bash
curl http://localhost:8000/api/projects/1/
```

**Response:**
```json
{
  "id": 1,
  "name": "My Conveyor System",
  "description": "A conveyor belt assembly",
  "owner_username": "admin",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "assembly_items": [
    {
      "id": 1,
      "component": {
        "id": 1,
        "name": "Motor",
        "category": {...},
        "glb_file_url": "..."
      },
      "custom_name": "Motor 1",
      "position": [0.0, 0.0, 0.0],
      "rotation": [0.0, 0.0, 0.0, 1.0],
      "scale": [1.0, 1.0, 1.0],
      "world_transform": {
        "position": [0.0, 0.0, 0.0],
        "rotation": [0.0, 0.0, 0.0, 1.0],
        "scale": [1.0, 1.0, 1.0]
      }
    }
  ]
}
```

## 9. Remove Component from Assembly

```bash
curl -X DELETE "http://localhost:8000/api/projects/1/remove_component/?item_id=1"
```

## 10. Get Component Connection Points

Component connection points are included in the component detail response:

```bash
curl http://localhost:8000/api/components/1/
```

**Response includes:**
```json
{
  "connection_points": [
    {
      "id": 1,
      "name": "top",
      "connection_type": "mount",
      "position": [5.0, 5.0, 10.0],
      "normal": [0.0, 0.0, 1.0],
      "diameter": 0.0,
      "side_label": "top"
    }
  ]
}
```

## JavaScript/Fetch Examples

### Upload Component

```javascript
const formData = new FormData();
formData.append('name', 'Motor');
formData.append('description', 'Stepper motor');
formData.append('category_id', '1');
formData.append('original_file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/components/upload/', {
  method: 'POST',
  body: formData,
  credentials: 'include' // For session auth
});

const component = await response.json();
```

### Get Placement Suggestions

```javascript
const projectId = 1;
const componentId = 2;

const response = await fetch(
  `http://localhost:8000/api/projects/${projectId}/placement_suggestions/?component_id=${componentId}`,
  { credentials: 'include' }
);

const { suggestions } = await response.json();

// Highlight suggested positions in 3D scene
suggestions.forEach(suggestion => {
  highlightPosition(suggestion.position, suggestion.confidence);
});
```

### Add Component with Smart Placement

```javascript
async function addComponentToProject(projectId, componentId, suggestion) {
  const response = await fetch(
    `http://localhost:8000/api/projects/${projectId}/add_component/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        component_id: componentId,
        position_x: suggestion.position[0],
        position_y: suggestion.position[1],
        position_z: suggestion.position[2],
        rotation_x: suggestion.rotation[0],
        rotation_y: suggestion.rotation[1],
        rotation_z: suggestion.rotation[2],
        rotation_w: suggestion.rotation[3],
      })
    }
  );
  
  return await response.json();
}
```

## Integration with React Three Fiber

```javascript
// Fetch component library
const { data: components } = await fetch('/api/components/').then(r => r.json());

// Fetch project assembly
const { data: project } = await fetch(`/api/projects/${projectId}/`).then(r => r.json());

// Render components
project.assembly_items.forEach(item => {
  <mesh
    position={item.position}
    rotation={item.rotation}
    scale={item.scale}
  >
    <primitive object={gltfScene} />
  </mesh>
});

// Get placement suggestions on drag
const handleDragOver = async (componentId) => {
  const { suggestions } = await fetch(
    `/api/projects/${projectId}/placement_suggestions/?component_id=${componentId}`
  ).then(r => r.json());
  
  setSuggestedPositions(suggestions);
};
```

