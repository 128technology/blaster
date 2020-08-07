import os

from flask import Flask

from .celery_utils import init_celery

PKG_NAME = os.path.dirname(os.path.realpath(__file__)).split("/")[-1]

def create_app(app_name=PKG_NAME, **kwargs):
    app = Flask(app_name)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'blaster.sqlite'),
    )

    if kwargs.get("celery"):
        init_celery(kwargs.get("celery"), app)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from . import certificate
    app.register_blueprint(certificate.bp)

    from . import menu
    app.register_blueprint(menu.bp)

    from . import iso
    app.register_blueprint(iso.bp)

    from . import conductor
    app.register_blueprint(conductor.bp)

    from . import manage_quickstart
    app.register_blueprint(manage_quickstart.bp)

    from . import quickstart
    app.register_blueprint(quickstart.bp)

    from . import node
    app.register_blueprint(node.bp)

    # This is ugly but it seems like NFS gives us problems
    # after a container rebuild until we restart it
    os.system("systemctl restart nfs")

    return app
