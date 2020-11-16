import functools

from flask import (
    current_app, Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for, jsonify
)

from blaster.conductor import get_all_nodes, get_quickstart_work
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
    # Avoid duplicates.  Assume reblasted, clear out old entry and add a new one
    db.execute('DELETE FROM node WHERE identifier = ?', (id,))
    db.execute('INSERT INTO node (identifier, iso_id, status)  VALUES (?, ?, ?)', (id, active_name, 'Blasted'))
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
    nodes = db.execute('select n.id, n.identifier, n.status, n.iso_id, q.conductor_name, q.router_name, q.node_name, q.asset_id FROM node n LEFT JOIN quickstart q ON n.quickstart_id = q.id').fetchall()
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

        associate_quickstart_to_node(qs_id, identifier)
        flash(f"made quickstart association for node with identifier of {identifier}")
        return redirect(request.url)

    quickstarts = db.execute('SELECT id, conductor_name, node_name, router_name FROM quickstart').fetchall()
    nodes = db.execute('SELECT identifier, quickstart_id from node').fetchall()
    return render_template('node_quickstart_associate.html', quickstarts=quickstarts, nodes=nodes)

def associate_quickstart_to_node(qs_id, identifier):
    db = get_db()
    db.execute('UPDATE node SET quickstart_id = ? WHERE identifier = ?', (qs_id, identifier))
    db.commit()

@bp.route('/fetch', methods=('POST',))
def fetch():
    db = get_db()
    blasted_nodes = db.execute('SELECT id, identifier FROM node WHERE status = "Blasted" and quickstart_id is null').fetchall()
    blasted_list = []
    for node in blasted_nodes:
        blasted_list.append(node[1])

    conductors = db.execute('SELECT name, url, auth_key FROM conductor').fetchall()
    errors = []
    for conductor in conductors:
        nodes, error = get_all_nodes(conductor[0], conductor[1], conductor[2])
        if error:
            errors.append(error)
            continue

        for node in nodes:
            if node['assetId'] in blasted_list:
                router_name = node['router']['name']
                node_name = node['name']
                assetId = node['assetId']
                success, qs_id_or_error = get_quickstart_work(conductor[0], router_name, node_name, assetId)
                if success:
                    associate_quickstart_to_node(qs_id_or_error, assetId)

                else:
                    errors.append(qs_id_or_error)

    flash('\n'.join(errors))
    return redirect(url_for('node.list'))
