call script_server\Scripts\activate.bat
celery -A server.celery worker --loglevel=info