import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

import os
import subprocess
from . import constants

bp = Blueprint('certificate', __name__, url_prefix='/certificate')

@bp.route('/')
def menu():
    return render_template('certificate_menu.html')

@bp.route('/show')
def show():
    cert_info = None
    try:
        cert_info = subprocess.check_output(
            ['openssl',
             'x509',
             '-text',
             '-in',
             os.path.join(constants.CERTIFICATE_FOLDER, constants.CERT_FILE),
             '-noout']
        ).decode()
    except subprocess.CalledProcessError:
        pass

    if cert_info:
        cert_info = cert_info.split('\n')

    return render_template('certificate_show.html', cert_info=cert_info)

@bp.route('/add', methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        if file:
            try:
                os.mkdir(constants.CERTIFICATE_FOLDER)
            except OSError:
                pass

            file.save(os.path.join(constants.CERTIFICATE_FOLDER, constants.CERT_FILE))
            return redirect(url_for('menu.home'))

    return render_template('certificate_add.html')
