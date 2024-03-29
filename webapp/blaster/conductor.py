import functools

from flask import (
    current_app, Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for
)

from blaster.db import get_db

import json
import os
import re
import requests

NODE_QUERY = '{"query":"query{allNodes{nodes{router{name}, name, role, assetId}}}"}'

bp = Blueprint('conductor', __name__, url_prefix='/conductor')

@bp.route('/')
def menu():
    return render_template('conductor_menu.html')

@bp.route('/add',  methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url').strip('/')
        username = request.form.get('username')
        password = request.form.get('password')

        if name is None or url is None or username is None or password is None:
            flash("Required information is missing")
            return redirect(request.url)

        try:
            resp = requests.post(
                f"{url}/api/v1/login",
                headers={'Content-Type':'application/json'},
                data=json.dumps({'username':username, 'password':password}),
                verify=False
            )
        except requests.exceptions.Timeout:
            flash("Timeout connecting to conductor")
            return redirect(request.url)

        if not resp.ok:
            flash(f"Conductor returned an error: {resp.status_code} {resp.json()}")
            return redirect(request.url)

        token = resp.json()['token']
        db = get_db()
        print(f"name: {name}")
        print(f"url: {url}")
        print(f"token: {token}")
        db.execute('INSERT INTO conductor (name, url, auth_key) VALUES (?, ?, ?)', (name, url, token))
        db.commit()
        flash(f"Conductor {name} added successfully")
        return redirect(url_for('conductor.menu'))

    return render_template('conductor_add.html')

@bp.route('/list')
def list():
    db = get_db()
    conductors = db.execute('SELECT name FROM conductor').fetchall()
    return render_template('conductor_list.html', conductors=conductors)

@bp.route('/delete/<name>')
def delete(name=None):
    if name is None:
        flash("No Conductor specificed for delete action")
        return redirect(url_for('conductor.menu'))

    db = get_db()
    db.execute('DELETE FROM conductor WHERE name = ?', (name,))
    db.commit()
    flash(f"Deleted Conductor {name}")
    return redirect(url_for('conductor.list'))

@bp.route('list_nodes/<name>')
def list_nodes(name=None):
    if name is None:
        flash("No Conductor specificed for delete action")
        return redirect(url_for('conductor.menu'))

    db = get_db()
    db_res = db.execute('SELECT url, auth_key FROM conductor WHERE name = ?', (name,)).fetchone()
    nodes, error = get_all_nodes(name, db_res[0], db_res[1])
    print("Test123")
    print(nodes)
    if nodes:
        return render_template('conductor_list_nodes.html', nodes=nodes, conductor=name)

    flash(error)
    return redirect(url_for('conductor.menu'))

def get_all_nodes(name, url, token):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {token}"
    }
    try:
        nodes_resp = requests.get(f"{url}/api/v1/graphql", data=NODE_QUERY, headers=headers, verify=False)
    except requests.exceptions.Timeout:
        return False, f"Timeout connecting to conductor {name}"
    except OSError as e:
        return False, f"OSException connecting to conductor {name}: {e}"
    except Exception as e:
        return False, f"There was an unspecified Exception connecing to conductor {name}: {e}"

    if not nodes_resp.ok:
        return False, f"Conductor {name} returned error for node query {nodes_resp.status_code}: {nodes_resp.json()}"

    try:
        nodes = nodes_resp.json()['data']['allNodes']['nodes']
    except KeyError:
        return False, f"There was an error attempting to parse the return data from conductor {name}"
        
    return nodes, None

@bp.route('/get_quickstart/<conductor>/<router>/<node>/<assetId>')
def get_quickstart(conductor=None, router=None, node=None, assetId=None):
    if conductor is None or router is None or node is None:
        flash("A required parameter (conductor, router, or node) was not specified")
        return redirect(url_for('conductor.menu'))

    success, error = get_quickstart_work(conductor, router, node, assetId)
    if not success:
        flash(error)
        return redirect(url_for('conductor.list'))

    flash(f"Added quickstart data returned from conductor {conductor} for router {router} node {node}")
    return redirect(url_for('conductor.list'))

def get_quickstart_work(conductor, router, node, assetId):
    db = get_db()
    conductor_data = db.execute('SELECT url, auth_key FROM conductor WHERE name = ?', (conductor,)).fetchone()

    token = conductor_data['auth_key']
    qs_url = conductor_data['url'] + '/api/v1/quickStart'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {token}"
    }

    node_data = {
        'router': router,
        'node': node,
        'assetId': assetId,
        'password': None
    }

    try:
        qs_resp = requests.post(qs_url, headers=headers, data=json.dumps(node_data), verify=False)
    except requests.exceptions.Timeout:
        error = f"Timeout connecting to conductor {name}"
        return False, error

    if not qs_resp.ok:
        error = f"Conductor {name} returned error for quickstart query {qs_resp.status_code}: {qs_resp.json()}"
        return False, error

    try:
        qs_json = qs_resp.json()
        qs_node = qs_json['n']
        qs_asset = qs_json['a']
        qs_config = qs_json['c']

        cursor = db.cursor()
        cursor.execute('INSERT INTO quickstart (' \
                       'conductor_name, ' \
                       'router_name, ' \
                       'node_name, ' \
                       'asset_id, ' \
                       'config, ' \
                       'description) VALUES (?, ?, ?, ?, ?, ?)',
           (conductor, router, qs_node, qs_asset, qs_config, 'Retrieved by blaster'))
        qs_id = cursor.lastrowid
        db.commit()
    except KeyError:
        error = f"Error parsing quickstart data returned from conductor {conductor} for router {router} node {node}"
        return False, error

    return True, qs_id
