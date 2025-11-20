# Conveyor Belt Builder

A 3D CAD-based engineering builder platform for designing and configuring conveyor belt systems.

## Features

- 🎨 **3D Visualization** - Interactive 3D scene with Three.js
- 📦 **Component Library** - Drag-and-drop component system
- 🔧 **Real-time Editing** - Adjust dimensions, positions, and rotations
- 💾 **Project Management** - Save and load projects
- 🎯 **Precise Placement** - Grid-based positioning system
- 🌓 **Light/Dark Mode** - Theme support
- 📊 **BOM Generation** - Bill of Materials export

## Tech Stack

### Backend
- Django 4.2
- Django REST Framework
- PostgreSQL (Neon)
- Celery (optional)
- FreeCAD Docker (for STEP conversion)

### Frontend
- React + TypeScript
- Vite
- Three.js / React Three Fiber
- Tailwind CSS
- shadcn/ui

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL database (Neon recommended)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd "Conveyor Belt Builder"
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Copy and configure environment variables
   cp .env.example .env
   # Edit .env with your database credentials
   
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   
   # Create .env file
   echo "VITE_API_BASE=http://localhost:8000" > .env
   
   npm run dev
   ```

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin

## Database Setup

This project uses Neon PostgreSQL. See:
- `backend/NEON_DATABASE_SETUP.md` - Neon database setup
- `backend/DATABASE_SETUP.md` - General database setup

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy to Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

## Project Structure

```
.
├── backend/          # Django backend
│   ├── cadbuilder/   # Main Django app
│   ├── components/   # Component models and API
│   ├── projects/     # Project management
│   └── converter/    # CAD file conversion
├── frontend/         # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   └── lib/         # Utilities
└── docs/            # Documentation
```

## Environment Variables

### Backend (.env)

See `backend/.env.example` for all available variables.

Required:
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string
- `ALLOWED_HOSTS` - Allowed hostnames

### Frontend (.env)

- `VITE_API_BASE` - Backend API URL

## Development

### Running Tests

```bash
# Backend
cd backend
python manage.py test

# Frontend
cd frontend
npm test
```

### Code Style

- Backend: Follow PEP 8
- Frontend: ESLint + Prettier

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions:
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for deployment issues
- Check `backend/RAILWAY_TROUBLESHOOTING.md` for Railway-specific issues
- Open an issue on GitHub

## Acknowledgments

- Three.js for 3D rendering
- Django REST Framework for API
- shadcn/ui for UI components
