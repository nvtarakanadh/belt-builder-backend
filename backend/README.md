# CAD Builder Backend API

Django REST Framework backend for an interactive CAD-based engineering builder platform.

## Features

- **GLB Component Management**: Upload and store GLB/GLTF files directly
- **Geometry Extraction**: Automatic extraction of bounding boxes, volumes, and connection points from GLB files
- **No Conversion Needed**: GLB/GLTF files are used directly (no CAD conversion required)
- **Project Management**: Create and manage user projects/workspaces
- **Assembly Building**: Combine components into 3D assemblies with positioning and hierarchy
- **Smart Placement**: Intelligent placement suggestions based on connection points and geometry
- **REST API**: Comprehensive RESTful API with OpenAPI documentation

## Tech Stack

- **Django 4.2** + **Django REST Framework**
- **PostgreSQL** for data storage
- **Trimesh** / **pythonocc-core** for CAD processing
- **Redis** + **Celery** (optional) for background tasks
- **Docker** for containerization

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository and navigate to the backend directory:
```bash
cd backend
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Build and start services:
```bash
docker-compose up --build
```

4. Create a superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

5. Access the API:
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- API Docs: http://localhost:8000/api/docs/

### Manual Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up PostgreSQL database:
```bash
createdb cadbuilder
```

3. Configure environment variables (copy `.env.example` to `.env`)

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Start development server:
```bash
python manage.py runserver
```

## API Endpoints

### Components

- `GET /api/components/` - List all components
- `POST /api/components/upload_component/` - Upload a new GLB/GLTF component
- `GET /api/components/{id}/` - Get component details
- `PUT/PATCH /api/components/{id}/` - Update component
- `DELETE /api/components/{id}/` - Delete component
- `GET /api/component-categories/` - List component categories

### Projects

- `GET /api/projects/` - List user's projects
- `POST /api/projects/` - Create a new project
- `GET /api/projects/{id}/` - Get project details with assembly items
- `PUT/PATCH /api/projects/{id}/` - Update project
- `DELETE /api/projects/{id}/` - Delete project
- `POST /api/projects/{id}/add_component/` - Add component to assembly
- `GET /api/projects/{id}/placement_suggestions/?component_id=123` - Get smart placement suggestions
- `POST /api/projects/{id}/save/` - Save assembly state
- `DELETE /api/projects/{id}/remove_component/?item_id=123` - Remove component from assembly

### Assembly Items

- `GET /api/assembly-items/?project_id=123` - List assembly items for a project
- `GET /api/assembly-items/{id}/` - Get assembly item details
- `PUT/PATCH /api/assembly-items/{id}/` - Update assembly item
- `DELETE /api/assembly-items/{id}/` - Delete assembly item

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## GLB File Processing

The backend accepts GLB/GLTF files directly and processes them using:

1. **Trimesh**: Extracts geometry data (bounding boxes, volumes, connection points) from GLB/GLTF files
2. **No Conversion**: GLB files are used directly for web visualization

### Supported File Formats

- **GLB** (.glb) - Binary GLTF format (recommended)
- **GLTF** (.gltf) - Text-based GLTF format

## Smart Placement System

The smart placement system analyzes:
- Connection points from existing components
- Component compatibility (connection types, sizes)
- Geometric relationships (bounding boxes, orientations)
- Hierarchy and parent-child relationships

### How It Works

1. User selects a component to place
2. Frontend calls `/api/projects/{id}/placement_suggestions/?component_id=123`
3. Backend analyzes existing assembly and returns:
   - Valid connection points
   - Snap positions (top, bottom, sides)
   - Confidence scores for each suggestion
4. Frontend highlights suggested positions
5. User confirms placement → backend saves the assembly item

## Project Structure

```
backend/
├── cadbuilder/          # Django project settings
├── components/          # CAD component management app
│   ├── models.py       # Component, Category, ConnectionPoint models
│   ├── views.py        # Component API endpoints
│   └── serializers.py  # Component serializers
├── projects/           # Project and assembly management app
│   ├── models.py       # Project, AssemblyItem models
│   ├── views.py        # Project API endpoints
│   └── serializers.py  # Project serializers
├── cad_processing/     # CAD file processing utilities
│   └── utils.py        # Geometry extraction, GLB conversion
├── manage.py
├── requirements.txt
└── docker-compose.yml
```

## Development

### Running Tests

```bash
python manage.py test
```

### Code Style

Follow PEP 8 and Django coding standards.

### Adding New Features

1. Create migrations after model changes:
```bash
python manage.py makemigrations
python manage.py migrate
```

2. Update API documentation will be auto-generated from serializers and views.

## Deployment

### Production Settings

1. Set `DEBUG=False`
2. Configure proper `ALLOWED_HOSTS`
3. Use environment variables for secrets
4. Set up proper database backups
5. Configure static file serving (Nginx, S3, etc.)
6. Set up SSL/TLS certificates
7. Configure Celery workers for background CAD processing

### Environment Variables

Key environment variables for production:
- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `False`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`: Database configuration
- `USE_S3`, `AWS_*`: AWS S3 configuration for file storage

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

