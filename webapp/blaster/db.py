import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext
import logging
import pathlib

LOG_DIRECTORY = pathlib.Path('/var') / 'log' / 'blaster'
pathlib.Path(LOG_DIRECTORY).mkdir(parents=True, exist_ok=True)
log_file = LOG_DIRECTORY / 'blaster.log'

handler = logging.handlers.RotatingFileHandler(
    log_file
)

LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)
LOG.addHandler(handler)
LOG.setLevel(logging.DEBUG)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

def init_app(app):
    app.teardown_appcontext(close_db)

    with app.app_context():
        db_file = current_app.config['DATABASE']
        if not pathlib.Path(db_file).exists():
            LOG.info("DB file not found, creating initial DB...")
            # Setup initial schema as found in v1.0
            init_db()
 
        db = get_db()
        user_version = db.execute('pragma user_version').fetchall()[0][0]
        LOG.info(f"Found DB with user_version {user_version}")
        if user_version < 1:
            # passwords table added in v1.1 before schema versioning
            pw_table = db.execute('SELECT count(name) FROM sqlite_master WHERE type="table" AND name="passwords"').fetchone()[0]
            if pw_table == 0:
                LOG.info("Password table missing from DB, creating it...")
                with current_app.open_resource('passwords_table.sql') as f:
                    db.executescript(f.read().decode('utf8'))


            LOG.info("Updating DB schema to v1...")
            with current_app.open_resource('schema_v1.sql') as f:
                db.executescript(f.read().decode('utf8'))

        if user_version < 2:
            LOG.info("Updating DB schema to v2...")
            with current_app.open_resource('schema_v2.sql') as f:
                db.executescript(f.read().decode('utf8'))

        db.commit()
