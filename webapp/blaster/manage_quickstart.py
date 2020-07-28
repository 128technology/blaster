import functools

from flask import (
    current_app, Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)

from blaster.db import get_db

import json

from . import constants

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

        file = request.files['file']
        data = file.read().decode()
        password = request.form.get('password')
        router = request.form.get('router')
        node = request.form.get('node')
        conductor = request.form.get('conductor')
        description = request.form.get('description')

        db.execute('INSERT INTO quickstart (router_name, node_name, conductor_name, description, password, quickstart_data) VALUES (?, ?, ?, ?, ?, ?)',
           (router, node, conductor, description, password, data))
        db.commit()

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

    db = get_db()
    # Get rid of any existing defaults
    db.execute('UPDATE quickstart SET default_quickstart = 0 WHERE default_quickstart > 0')
    db.execute('UPDATE quickstart SET default_quickstart = 1 WHERE id = ?', (id,))
    db.commit()
    flash("Updated default quickstart")
    return redirect(url_for('manage_quickstart.menu'))
