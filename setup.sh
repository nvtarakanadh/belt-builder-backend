#!/bin/bash
# Setup script for CAD Builder Backend

echo "Setting up CAD Builder Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

# Create media directories
echo "Creating media directories..."
mkdir -p media/components/original
mkdir -p media/components/glb
mkdir -p media/temp
mkdir -p staticfiles

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser (optional)
echo "Do you want to create a superuser? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    python manage.py createsuperuser
fi

echo "Setup complete!"
echo "Run 'python manage.py runserver' to start the development server"

