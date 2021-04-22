from blaster import factory
import blaster
if __name__ == "__main__":
    app = factory.create_app(celery=blaster.celery)
    app.run(host='0.0.0.0', port=80)
