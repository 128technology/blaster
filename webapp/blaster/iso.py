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
import stat
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
    download_image.delay(name)
    flash(f"Beginning download of {name}, please check back later for status")
    return redirect(url_for('iso.menu'))

@bp.route('/list')
def list():
    db = get_db()
    isos = db.execute('SELECT id, name, pre_bootstrap_script, post_bootstrap_script, status FROM iso').fetchall()
    scripts = db.execute('SELECT name FROM script').fetchall()
    active = get_active()
    pias={}
    for iso in isos:
        pias[iso[1]] = get_post_install_action(iso[1])

    return render_template('iso_list.html', isos=isos, active=active, scripts=scripts, post_install_actions=pias)

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
    if bios_active and not os.path.exists(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg" / bios_active):
        os.remove(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg" / "default")
        active = None
    if uefi_active and not os.path.exists(pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "pxelinux.cfg" / uefi_active):
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

@bp.route('/upload', methods=('GET', 'POST'))
def upload():
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
                os.mkdir(constants.IMAGE_FOLDER)
            except OSError:
                pass

            file.save(pathlib.Path(constants.IMAGE_FOLDER) / file.filename)
            name = os.path.splitext(file.filename)[0]
            db = get_db()
            db.execute('INSERT INTO iso (name, status)  VALUES (?, ?)', (name, 'Processing'))
            db.commit()
            stage_image.delay(name)
            return redirect(url_for('menu.home'))

    return render_template('iso_upload.html')

@bp.route('/update_iso_options', methods=('POST',))
def update_iso_options():
    jd = request.json
    with open('/tmp/test', 'w') as fh:
        fh.write(str(jd))

    scripts = jd["scripts"]
    pias = jd["post_install_actions"]
    
    for identifier, script_name in scripts.items():
        id_split = identifier.split('_')
        success = associate_script_to_iso(id_split[0], id_split[1], script_name)
        if success:
            flash(f"Made {id_split[1]}-bootstrap script association for iso id {id_split[0]} and script {script_name}")
        else:
            flash(f"Cannot make script association unless ISO status is 'Ready'")

    for identifier, state in pias.items():
        id_split = identifier.split('_')
        success = set_post_install_action(id_split[0], state)
        if success:
            flash(f"Changed ISO {id_split[0]} post install action to {state}")
        else:
            flash(f"Cannot change post install action unless ISO status is 'Ready'")

    return redirect(url_for('iso.list'))

def associate_script_to_iso(iso_id, script_type, script_name):
    db = get_db()
    entry = db.execute('SELECT name,status FROM iso WHERE id = ?', (iso_id,)).fetchone()
    if not entry:
        flash(f"Error: no ISO found with specified id {iso_id}")
        return redirect(url_for('iso.list'))

    iso_status = entry['status']
    if iso_status != 'Ready':
        return False

    iso_name = entry['name']
    if script_type == constants.PRE_BOOTSTRAP:
        setup_iso_script(iso_name, constants.PRE_BOOTSTRAP, script_name, 'ADD')
        db.execute('UPDATE iso SET pre_bootstrap_script = ? WHERE id = ?', (script_name, iso_id))
    elif script_type == constants.POST_BOOTSTRAP:
        setup_iso_script(iso_name, constants.POST_BOOTSTRAP, script_name, 'ADD')
        db.execute('UPDATE iso SET post_bootstrap_script = ? WHERE id = ?', (script_name, iso_id))
    db.commit()
    return True

@bp.route('/clear_script/<iso_id>/<script_type>')
def clear_script(iso_id, script_type):
    db = get_db()
    entry = db.execute('SELECT name FROM iso WHERE id = ?', (iso_id,)).fetchone()
    if not entry:
        flash(f"Error: no ISO found with specified id {iso_id}")
        return redirect(url_for('iso.list'))

    iso_name = entry['name']
    if script_type == constants.PRE_BOOTSTRAP:
        setup_iso_script(iso_name, constants.PRE_BOOTSTRAP, None, 'DELETE')
        db.execute('UPDATE iso SET pre_bootstrap_script = null WHERE id = ?', (iso_id,))
    elif script_type == constants.POST_BOOTSTRAP:
        setup_iso_script(iso_name, constants.POST_BOOTSTRAP, None, 'DELETE')
        db.execute('UPDATE iso SET post_bootstrap_script = null WHERE id = ?', (iso_id,))
    db.commit()

    flash(f"Removed {script_type}-bootstrap-script from iso {iso_name}")
    return redirect(url_for('iso.list'))

def setup_iso_script(iso_name, script_type, script_name, action):
    iso_script_file = '/dev/null'
    if script_type == constants.PRE_BOOTSTRAP:
        iso_script_file = pathlib.Path(constants.IMAGE_FOLDER) / iso_name / constants.PRE_BOOTSTRAP_FILENAME
    elif script_type == constants.POST_BOOTSTRAP:
        iso_script_file = pathlib.Path(constants.IMAGE_FOLDER) / iso_name / constants.POST_BOOTSTRAP_FILENAME

    if action == 'ADD':
        saved_script_file = pathlib.Path(constants.SCRIPT_FOLDER) / script_name
        with open(saved_script_file, 'r') as fh:
            script_contents = fh.read()

        with open(iso_script_file, 'w') as fh:
            fh.write(script_contents)

        os.chmod(iso_script_file, stat.S_IXUSR)
    elif action == 'DELETE':
        try:
            os.remove(iso_script_file)
        except OSError:
            pass

def _list_equal(_list):
    iterator = iter(_list)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(first == x for x in iterator)

def get_post_install_action(iso_name):
    ks_files = [
        constants.COMBINED_ISO_OTP_KS_FILE,
        constants.COMBINED_ISO_OTP_UEFI_KS_FILE,
        constants.LEGACY_OTP_KICKSTART_FILE,
        constants.LEGACY_STANDARD_KICKSTART_FILE,
    ]

    actions = []
    for ks_filename in ks_files:
        ks_file = pathlib.Path(constants.IMAGE_FOLDER) / iso_name / ks_filename
        if ks_file.exists():
            if 'shutdown' in ks_file.read_text():
                actions.append('shutdown')
            elif 'reboot' in ks_file.read_text():
                actions.append('reboot')
            else:
                actions.append('undefined')

    if _list_equal(actions):
        return actions[0]

    return 'undefined'

def set_post_install_action(iso_id, action):
    db = get_db()
    entry = db.execute('SELECT name,status FROM iso WHERE id = ?', (iso_id,)).fetchone()
    if not entry:
        flash(f"Error: no ISO found with specified id {iso_id}")
        return redirect(url_for('iso.list'))

    iso_status = entry['status']
    if iso_status != 'Ready':
        return False

    iso_name = entry['name']

    ACTION_FLIP = {
        'reboot': 'shutdown',
        'shutdown': 'reboot',
    }

    ks_files = [
        constants.COMBINED_ISO_OTP_KS_FILE,
        constants.COMBINED_ISO_OTP_UEFI_KS_FILE,
        constants.LEGACY_OTP_KICKSTART_FILE,
        constants.LEGACY_STANDARD_KICKSTART_FILE,
    ]

    for ks_filename in ks_files:
        ks_file = pathlib.Path(constants.IMAGE_FOLDER) / iso_name / ks_filename
        if ks_file.exists():
            new_contents = ks_file.read_text().replace(ACTION_FLIP[action], action)
            ks_file.write_text(new_contents)

    return True
