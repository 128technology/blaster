import functools

from flask import (
    current_app,
    Blueprint,
    flash,
    Flask,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from blaster.tasks import (
    download_image,
    stage_image,
    remove_image
)

from blaster.db import get_db

import os
import pathlib
import re
import requests
from lxml import html
from . import constants

bp = Blueprint('script', __name__, url_prefix='/script')

@bp.route('/')
def menu():
    return render_template('script_menu.html')

@bp.route('/list')
def list():
    db = get_db()
    scripts = db.execute('SELECT name, description FROM script').fetchall()
    return render_template('script_list.html', scripts=scripts)

@bp.route('/delete/<name>')
def delete(name=None):
    if name is None:
        flash("No script specificed for delete action")
        return redirect(url_for('script.list'))

    db = get_db()

    try:
        os.remove(pathlib.Path(constants.SCRIPT_FOLDER) / name)
    except OSError:
        pass

    db.execute('DELETE FROM script WHERE name = ?', (name,))
    db.commit()

    flash(f"Removed script {name}")
    return redirect(url_for('script.menu'))

@bp.route('/add', methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        name = request.form.get('name')
        description = request.form.get('description')

        if file:
            try:
                os.mkdir(constants.SCRIPT_FOLDER)
            except OSError:
                pass

            file.save(pathlib.Path(constants.SCRIPT_FOLDER) / name)
            db = get_db()
            db.execute('INSERT INTO script (name, description)  VALUES (?, ?)', (name, description))
            db.commit()
            flash(f"Added script {name}")
            return redirect(url_for('script.menu'))

    return render_template('script_add.html')

@bp.route('/view/<name>')
def view(name=None):
    if not name:
        flash('No script name specified')
        return redirect(url_for('script.list'))

    try:
      with open(pathlib.Path(constants.SCRIPT_FOLDER) / name) as fh:
        contents = fh.read()
    except OSError:
        contents = ''

    return render_template('script_view.html', contents=contents)
