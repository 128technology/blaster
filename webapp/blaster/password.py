import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from crypt import crypt, mksalt, METHOD_SHA512

import os
import pathlib
import re
from . import constants

from blaster.db import get_db

bp = Blueprint('password', __name__, url_prefix='/password')

@bp.route('/')
def menu():
    db = get_db()
    passwords = db.execute('SELECT username, password_hash FROM passwords').fetchall()
    return render_template('passwords_manage.html', passwords=passwords)

@bp.route('/modify', methods=['POST'])
def modify():
    username = request.form.get('username')
    password = request.form.get('password')
    verify_password = request.form.get('VerifyPassword')
    if password != verify_password:
        flash(f"Passwords did not match, no update made")
        return redirect(url_for('password.menu'))

    hashed_password = crypt(password, mksalt(METHOD_SHA512))
    db = get_db()
    entry = db.execute('SELECT * FROM passwords WHERE username = ?', (username,)).fetchone()
    if entry:
        db.execute('UPDATE passwords SET password_hash = ? WHERE username = ?', 
            (hashed_password, username))
        db.commit()
        flash(f"Password for {username} updated")
        return redirect(url_for('password.menu'))

    db.execute('INSERT INTO passwords (username, password_hash) VALUES (?, ?)',
        (username, hashed_password))
    db.commit()
    flash(f"Password for {username} added")
    return redirect(url_for('password.menu'))

@bp.route('/delete/<username>')
def delete(username=None):
    if username is None:
        flash("No username specified for password delete action")
        return redirect(url_for('password.menu'))

    db = get_db()
    db.execute('DELETE FROM passwords WHERE username = ?', (username,))
    db.commit()
    flash(f"Password entry for {username} updated")
    return redirect(url_for('password.menu'))

@bp.route('/update_isos', methods=['POST'])
def update_isos():
    db = get_db()
    isos = db.execute('SELECT name FROM iso').fetchall()
    for iso in isos:
        update_password(iso[0])
        flash(f"Passwords updated for ISO {iso[0]}")
    return redirect(url_for('password.menu'))

def update_password(iso_name):
    users_file = pathlib.Path(constants.IMAGE_FOLDER) / iso_name / constants.SETUP_USERS_FILE
    with open(users_file) as fh:
        curr_users = fh.read()

    db = get_db()
    passwords = db.execute('SELECT username, password_hash FROM passwords').fetchall()
    pass_dict = {}
    for password in passwords:
        pass_dict[password[0]] = password[1]

    new_user_lines = []
    for line in curr_users.split('\n'):
        if re.match('^rootpw .+$', line):
            try:
                phash = pass_dict['root']
                line = re.sub(r'--iscrypted .+', f'--iscrypted {phash}', line)
            except KeyError:
                pass
        elif re.match('^user .+$', line):
            username = re.match('^user.* --name=([a-z0-9_-]+) .*$', line).group(1)
            try:
                phash = pass_dict[username]
                line = re.sub(r'--password=[aA-zZ0-9$+/.]+ ', f'--password={phash} ', line)
            except KeyError:
                pass
        new_user_lines.append(line)

    with open(users_file, 'w') as fh:
        fh.write('\n'.join(new_user_lines))
