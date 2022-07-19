from multiprocessing import cpu_count

# Socket Path
bind = 'unix:/home/admin/neshkola/gunicorn.sock'

# Worker Options
workers = cpu_count() + 1
worker_class = 'uvicorn.workers.UvicornWorker'

# Logging Options
loglevel = 'debug'
accesslog = '/home/admin/neshkola/access_log'
errorlog =  '/home/admin/neshkola/error_log'