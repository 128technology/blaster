import functools

from flask import (
    current_app, Blueprint, flash, Flask, g, redirect, render_template, request, session, url_for
)

from blaster.tasks import setup_image, remove_image
from blaster.db import get_db

import os
import pathlib
import re
import requests
from lxml import html
from . import constants

bp = Blueprint('iso', __name__, url_prefix='/iso')

@bp.route('/')
def menu():
    return render_template('iso_menu.html')

@bp.route('/list_available')
def list_available():
    try:
        resp = requests.get(
            constants.ISO_REPO_URL, 
            cert=os.path.join(constants.CERTIFICATE_FOLDER, constants.CERT_FILE)
        )
    except OSError:
        flash("Certificate file not found!")
        return redirect(url_for('iso.menu'))

    if resp.ok:
        try:
            images = parse_iso_list(resp.text)
            return render_template('iso_add.html', images=images)
        except lookupparseerror:
            flash("Error parsing data returned from yum server, please try again")
            return redirect(url_for('iso.menu'))

    flash("Error {resp.status_code} while retreiving ISO list")
    return redirect(request.url)

def parse_iso_list(text):
    iso_list_page = html.fromstring(text)
    image_elements = iso_list_page.xpath('//body/table/tr/td/a')
    images = []
    iso_name = re.compile(constants.ISO_RE)
    for elem in image_elements:
        if iso_name.match(elem.text):
            images.append(iso_name.match(elem.text).group(1))

    return images

@bp.route('/add/<name>')
def add(name=None):
    if name is None:
        flash("No image specificed for add action")
        return redirect(url_for('iso.menu'))

    db = get_db()
    if db.execute('SELECT id FROM iso WHERE name = ?', (name,)).fetchone() is not None:
        flash(f"An ISO by the name {name} currently exists in the database.  If you wish to overwrite, please remove it first")
        return redirect(url_for('iso.menu'))

    print(f"setting up {name}")
    setup_image.delay(name)
    flash(f"Beginning download of {name}, please check back later for status")
    return redirect(url_for('iso.menu'))

@bp.route('/list')
def list():
    db = get_db()
    statuses = db.execute('SELECT id, status FROM iso_status_enum').fetchall()
    iso_status = {}
    for status in statuses:
        iso_status[status[0]] = status[1]
    isos = db.execute('SELECT name, status_id FROM iso').fetchall()
    active = get_active()
    return render_template('iso_list.html', isos=isos, iso_status=iso_status, active=active)

@bp.route('/delete/<name>')
def delete(name=None):
    if name is None:
        flash("No image specificed for delete action")
        return redirect(url_for('iso.menu'))

    remove_image.delay(name)
    flash(f"Beginning process to remove image {name}, please check back later for status")
    return redirect(url_for('iso.list'))

def get_active():
    uefi_active = None
    bios_active = None
    try:
        uefi_active = os.readlink(pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
    except FileNotFoundError:
        pass
    except OSError:
        os.remove(pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")

    try:
        bios_active = os.readlink(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
    except FileNotFoundError:
        pass
    except OSError:
        os.remove(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")

    if bios_active != uefi_active:
        print(f"Somehow, active image does not match between BIOS and UEFI, deleting both")
        if bios_active:
            os.remove(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
        if uefi_active:
            os.remove(pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
        return None

    active = bios_active

    # Remove any dangling links
    if bios_active and not os.path.exists(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / bios_active):
        os.remove(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
        active = None
    if uefi_active and not os.path.exists(pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / uefi_active):
        os.remove(pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
        active = None

    return active

@bp.route('/update_active/<name>')
def update_active(name=None):
    if name is None:
        flash("No image specificed for update_active action")
        return redirect(url_for('iso.menu'))

    try:
        os.remove(pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
    except (OSError, FileNotFoundError):
        pass

    try:
        os.remove(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
    except (OSError, FileNotFoundError):
        pass

    try:
        os.symlink(name, pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
        os.symlink(name, pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
        flash(f"{name} is now the active ISO for blasting")
        return redirect(url_for('iso.menu'))
    except Error:
        flash("There was an unspecified error updating the active ISO")
        return redirect(url_for('iso.menu'))
