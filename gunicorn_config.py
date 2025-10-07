bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
timeout = 120
accesslog = "/var/www/projects/LabLedger-Backend/logs/gunicorn-access.log"
errorlog = "/var/www/projects/LabLedger-Backend/logs/gunicorn-error.log"
loglevel = "info"
