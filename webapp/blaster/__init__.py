from celery import Celery
def make_celery(app_name=__name__):
    redis_uri = 'redis://localhost:6379'
    return Celery(app_name, backend=redis_uri, broker=redis_uri)

celery = make_celery()
