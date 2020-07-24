from blaster import celery
from blaster.factory import create_app
from blaster.celery_utils import init_celery
app = create_app()
init_celery(celery, app)
