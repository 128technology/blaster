import functools

from flask import (
    current_app, Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)

from blaster.db import get_db

import json

from blaster import constants

bp = Blueprint('manage_quickstart', __name__, url_prefix='/manage_quickstart')

@bp.route('/')
def menu():
    return render_template('quickstart_menu.html')

@bp.route('/add', methods=('GET', 'POST'))
def add(name=None):
    db = get_db()

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        router = request.form.get('router')
        conductor = request.form.get('conductor')
        description = request.form.get('description')
        # Not supported yet
        #password = request.form.get('password')

        file = request.files['file']
        try:
            qs_contents = file.read()
        except UnicodeDecodeError:
            flash("Quickstart file appears to be encrypted, which is not supported at this time")
            return redirect(url_for('manage_quickstart.menu'))

        try:
            qs_data = json.loads(qs_contents)
        except json.decoder.JSONDecodeError:
            flash("Quickstart does not appear to have valid JSON, please check contents")
            return redirect(url_for('manage_quickstart.menu'))

        node = qs_data.get('n')
        asset = qs_data.get('a')
        config = qs_data.get('c')

        db.execute('INSERT INTO quickstart (' \
                       'conductor_name, ' \
                       'router_name, ' \
                       'node_name, ' \
                       'asset_id, ' \
                       'config, ' \
                       'description) VALUES (?, ?, ?, ?, ?, ?)',
           (conductor, router, node, asset, config, description))
        db.commit()

        flash("Quickstart uploaded successfully")
        return redirect(url_for('manage_quickstart.menu'))

    elif request.method == 'GET':
        return render_template('quickstart_add.html')

@bp.route('/list')
def list():
    db = get_db()
    quickstarts = db.execute('SELECT * FROM quickstart').fetchall()
    return render_template('quickstart_list.html', quickstarts=quickstarts)

@bp.route('/delete/<id>')
def delete(id=None):
    if id is None:
        flash("No quickstart specificed for delete action")
        return redirect(url_for('manage_quickstart.menu'))

    db = get_db()
    db.execute('DELETE FROM quickstart where id = ?', (id,))
    db.commit()
    flash(f"Deleted quickstart")
    return redirect(url_for('manage_quickstart.list'))

@bp.route('/set_as_default/<id>')
def set_as_default(id=None):
    if id is None:
        flash("No quickstart specified for set as default action")
        return redirect(url_for('manage_quickstart.list'))

    clear_default_qs()
    db = get_db()
    db.execute('UPDATE quickstart SET default_quickstart = 1 WHERE id = ?', (id,))
    db.commit()
    flash("Updated default quickstart")
    return redirect(url_for('manage_quickstart.menu'))

@bp.route('/clear_default')
def clear_default():
    clear_default_qs()
    flash("Cleared default quickstart")
    return redirect(url_for('manage_quickstart.menu'))

def clear_default_qs():
    db = get_db()
    # Get rid of any existing defaults
    db.execute('UPDATE quickstart SET default_quickstart = 0 WHERE default_quickstart > 0')
    db.commit()

@bp.route('/remove_asset/<id>')
def remove_asset(id=None):
    if id is None:
        flash("No quickstart specified for set as default action")
        return redirect(url_for('manage_quickstart.list'))

    db = get_db()
    db.execute('UPDATE quickstart SET asset_id = NULL WHERE id = ?', (id,))
    db.commit()
    flash("Removed asset_id from quickstart")
    return redirect(url_for('manage_quickstart.menu'))
