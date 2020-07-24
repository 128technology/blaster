import functools

from flask import (
    current_app, Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for
)

from blaster.tasks import setup_image, remove_image
from blaster.db import get_db

import json
import os
import re
import requests

bp = Blueprint('conductor', __name__, url_prefix='/conductor')

@bp.route('/')
def menu():
    return render_template('conductor_menu.html')

@bp.route('/add',  methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
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
    nodes = get_all_nodes(name, db_res['url'], db_res['auth_key'])
    return render_template('conductor_list_nodes.html', nodes=nodes)

def get_all_nodes(name, url, token):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {token}"
    }
    try:
        routers_resp = requests.get(f"{url}/api/v1/router", headers=headers, verify=False)
    except requests.exceptions.Timeout:
        flash(f"Timeout connecting to conductor {name}")
        return None

    if not routers_resp.ok:
        flash(f"Conductor {name} returned error for /api/v1/router {routers_resp.status_code}: {routers_resp.json()}")
        return None

    router_names = []
    for router in routers_resp.json():
        router_names.append(router.get('name'))

    router_nodes = []
    for router in router_names:
        try:
            nodes_resp = requests.get(f"{url}/api/v1/router/{router}/node", headers=headers, verify=False)
        except requests.exceptions.Timeout:
            flash(f"Timeout connecting to conductor {name}")
            return None

        if not nodes_resp.ok:
            flash(f"Conductor {name} returned error for /api/v1/node {nodes_resp.status_code}: {nodes_resp.json()}")
            return None

        for node in nodes_resp.json():
            router_nodes.append((router, node.get('name')))

    return router_nodes
