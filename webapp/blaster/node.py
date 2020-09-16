import functools

from flask import (
    current_app, Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)

from blaster.tasks import setup_image, remove_image
from blaster.db import get_db
from blaster.iso import get_active

import os
import pathlib
import re
import requests
from lxml import html
from . import constants

bp = Blueprint('node', __name__, url_prefix='/node')

@bp.route('/')
def menu():
    return render_template('node_menu.html')

@bp.route('/add/<id>', methods=['POST'])
def add(id=None):
    if id is None:
        flash("No id specificed for node add action")
        return redirect(url_for('node.menu'))

    db = get_db()
    active_name = get_active()
    active_row = db.execute('SELECT id FROM iso WHERE name = ?', (active_name,)).fetchone()
    # Avoid duplicates.  Assume reblasted, clear out old entry and add a new one
    db.execute('DELETE FROM node WHERE identifier = ?', (id,))
    db.execute('INSERT INTO node (identifier, iso_id)  VALUES (?, ?)', (id, active_row['id']))
    db.commit()
    return jsonify(added=id,blasted_with=active_name), 200

@bp.route('/delete/<id>')
def delete(id=None):
    if id is None:
        flash("No id specificed for node add action")
        return redirect(url_for('node.menu'))

    db = get_db()
    db.execute('DELETE FROM node WHERE identifier = ?', (id,))
    db.commit()
    return redirect(url_for('node.list'))

@bp.route('/list')
def list():
    db = get_db()
    nodes = db.execute('select n.id, n.identifier, i.name, q.conductor_name, q.router_name, q.node_name, q.asset_id FROM node n LEFT JOIN quickstart q ON n.quickstart_id = q.id LEFT JOIN iso i ON n.iso_id = i.id').fetchall()
    print(nodes)
    return render_template('node_list.html', nodes=nodes)

@bp.route('/associate', methods=('GET', 'POST'))
def associate():
    db = get_db()
    if request.method == 'POST':
        qs_id = request.form.get('qs_id')
        identifier = request.form.get('identifier')
        if qs_id is None or identifier is None:
            flash("Both a quickstart and node identifier must be selected")
            return redirect(request.url)

        db.execute('UPDATE node SET quickstart_id = ? WHERE identifier = ?', (qs_id, identifier))
        db.commit()
        flash(f"made quickstart association for node with identifier of {identifier}")
        return redirect(request.url)

    quickstarts = db.execute('SELECT id, conductor_name, node_name, router_name FROM quickstart').fetchall()
    nodes = db.execute('SELECT identifier, quickstart_id from node').fetchall()
    return render_template('node_quickstart_associate.html', quickstarts=quickstarts, nodes=nodes)
