.PHONY: help install migrate run test clean docker-up docker-down

help:
	@echo "CAD Builder Backend - Available commands:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make migrate     - Run database migrations"
	@echo "  make run         - Start development server"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean Python cache files"
	@echo "  make docker-up   - Start Docker services"
	@echo "  make docker-down - Stop Docker services"

install:
	pip install -r requirements.txt

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

run:
	python manage.py runserver

test:
	python manage.py test

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

superuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput

