import functools

from flask import (
    current_app, Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)

import json

from blaster.db import get_db

from . import constants

bp = Blueprint('quickstart', __name__, url_prefix='/quickstart')

@bp.route('/<instance>')
def instantiate(instance=None):
    db = get_db()

    node_row = db.execute('SELECT quickstart_id from node WHERE identifier = ?', (instance,)).fetchone()
    if node_row is None:
        qs_row = db.execute('SELECT node_name, asset_id, config FROM quickstart WHERE default_quickstart > 0').fetchone()
    else:
        qs_row = db.execute('SELECT node_name, asset_id, config FROM quickstart WHERE id = ?', (node_row['quickstart_id'],)).fetchone()

    if qs_row is None:
        return jsonify(error="Could not find a specific or default quickstart"), 404

    response = {}
    quickstart = {
        'a': qs_row['asset_id'],
        'n': qs_row['node_name'],
        'c': qs_row['config']
    }
    response['quickstart'] = json.dumps(quickstart)
    response['password'] = None
    db.execute('UPDATE node SET status = ? WHERE identifier = ?', ('Bootstrapped', instance))
    db.commit()
    return jsonify(response)
