REM venv directory was named script_server in this install
call script_server\Scripts\activate.bat
celery -A server.celery worker --loglevel=info
