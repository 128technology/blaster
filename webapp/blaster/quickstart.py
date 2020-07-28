import functools

from flask import (
    current_app, Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)

from blaster.db import get_db

from . import constants

bp = Blueprint('quickstart', __name__, url_prefix='/quickstart')

@bp.route('/<instance>')
def instantiate(instance=None):
    db = get_db()
    default_row = db.execute('SELECT quickstart_data, password FROM quickstart where default_quickstart > 0').fetchone()
    if default_row:
        response = {}
        response['quickstart'] = default_row['quickstart_data']
        response['password'] = default_row['password']
        return jsonify(response)
    else:
        return jsonify(error="Not Found"), 404
