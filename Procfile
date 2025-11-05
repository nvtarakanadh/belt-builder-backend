web: python wait_for_db.py && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn cadbuilder.wsgi:application --bind 0.0.0.0:$PORT

