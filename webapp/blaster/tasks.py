import os
import pathlib
import shutil

from celery import Celery
import requests
from blaster.db import get_db
from blaster import constants

celery = Celery('tasks', broker='redis://localhost:6379/0')

OTP_KICKSTART_FILE = 'ks.cfg'
STANDARD_KICKSTART_FILE = '128T-ks.cfg'

def iso_file(name):
    return pathlib.Path(constants.IMAGE_FOLDER) / (name + '.iso')

@celery.task(time_limit=1800)
def download_image(name):
    print(f"Adding ISO {name} to DB")
    db = get_db()
    db.execute('INSERT INTO iso (name, status)  VALUES (?, ?)', (name, 'Processing'))
    db.commit()
    print(f"Attempting to download ISO {name}")
    resp = requests.get(
        f"{constants.ISO_REPO_URL}{name}.iso",
        cert=os.path.join(constants.CERTIFICATE_FOLDER, constants.CERT_FILE),
        allow_redirects=True
    )
    if not resp.ok:
        print(f"Issue downloading ISO {name}")
        update_db_failed(name)
        return False

    print(f"ISO {name} downloaded successfully")
    # ensure iso folder exists
    try:
        os.makedirs(constants.IMAGE_FOLDER)
    except OSError:
        pass

    with open(iso_file(name), 'wb+') as iso:
        iso.write(resp.content)
    return stage_image(name)

@celery.task()
def stage_image(name):
    nfs_dir = pathlib.Path(constants.IMAGE_FOLDER) / name
    # Make sure destination doesn't exist
    try:
        os.rmdir(nfs_dir)
    except FileNotFoundError:
        pass

    try:
        os.system(f"osirrox -indev {iso_file(name)} -extract / {nfs_dir}")

        # If it's already in here, don't re-add it
        if os.system(f"grep {name} /etc/exports") > 0:
            fsid = len(open('/etc/exports').readlines())
            with open('/etc/exports', 'a') as fh:
                fh.write(f"{nfs_dir} 192.168.128.0/24(fsid={fsid},no_root_squash)\n")
        os.system('exportfs -ra')
    except OSError:
        print(f"There was an error when attempting to setup the NFS share for {name}")
        update_db_failed(name)
        return False

    if (nfs_dir / OTP_KICKSTART_FILE).exists():
        ks_file = OTP_KICKSTART_FILE
        print(f"{name} is an OTP ISO based on the kickstart file found")
    elif (nfs_dir / STANDARD_KICKSTART_FILE).exists():
        ks_file = STANDARD_KICKSTART_FILE
        print(f"{name} is a standard ISO based on the kickstart file found")
    else:
        print(f"Could not find either expected kickstart file in {name}, aborting")
        update_db_failed(name)
        return False

    uefi_image_dir = pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "images" / name
    uefi_image_dir.mkdir(parents=True, exist_ok=True)

    bios_image_dir = pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "images" / name
    bios_image_dir.mkdir(parents=True, exist_ok=True)
   
    try:
        shutil.copy(nfs_dir / "images" / "pxeboot" / "vmlinuz", uefi_image_dir)
        shutil.copy(nfs_dir / "images" / "pxeboot" / "initrd.img", uefi_image_dir)
        shutil.copy(nfs_dir / "images" / "pxeboot" / "vmlinuz", bios_image_dir)
        shutil.copy(nfs_dir / "images" / "pxeboot" / "initrd.img", bios_image_dir)
    except (FileNotFoundError, OSError):
        print(f"There was an error setting up TFTP images for {name}")
        update_db_failed(name)
        return False

    uefi_pxelinux_dir = pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "pxelinux.cfg"
    uefi_pxelinux_dir.mkdir(parents=True, exist_ok=True)

    print(f"Writing UEFI pxelinux config for {name}")
    with open(uefi_pxelinux_dir / name, "w+") as fh:
        fh.writelines(["UI menu.c32\n",
                       "timeout 30\n",
                       "\n",
                       "display boot.msg\n",
                       "\n",
                       "MENU TITLE PXE Boot MENU\n",
                       "\n",
                      f"label {name}\n",
                      f"  kernel images/{name}/vmlinuz\n",
                      f"  append initrd=http://{constants.UEFI_IP}/images/{name}/initrd.img "
                      f"inst.stage2=nfs:{constants.NFS_IP}:{ pathlib.Path(constants.IMAGE_FOLDER) / name } "
                      f"inst.ks=nfs:{constants.NFS_IP}:{ pathlib.Path(constants.IMAGE_FOLDER) / name }/{ ks_file } "
                       "console=ttyS0,115200n81\n",
                     ])

    bios_pxelinux_dir = pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg"
    bios_pxelinux_dir.mkdir(parents=True, exist_ok=True)

    print(f"Writing BIOS pxelinux config for {name}")
    with open(bios_pxelinux_dir / name, "w+") as fh:
        fh.writelines([f"default {name}\n",
                       "timeout 30\n",
                       "\n",
                       "display boot.msg\n",
                       "\n",
                       "MENU TITLE PXE Boot MENU\n",
                       "\n",
                      f"label {name}\n",
                      f"  kernel images/{name}/vmlinuz\n",
                      f"  append initrd=images/{name}/initrd.img "
                      f"inst.stage2=nfs:{constants.NFS_IP}:{ pathlib.Path(constants.IMAGE_FOLDER) / name } "
                      f"inst.ks=nfs:{constants.NFS_IP}:{ pathlib.Path(constants.IMAGE_FOLDER) / name }/{ ks_file } "
                       "console=ttyS0,115200n81\n",
                     ])

    print(f"Appending new post section to kickstart to post identifier after blast")
    with open(nfs_dir / ks_file, 'a') as fh:
        fh.writelines(['%post\n',
                       'curl -XPOST http://192.168.128.128/node/add/`dmidecode --string system-serial-number`\n',
                       '%end\n'])

    print(f"Image {name} appears to have been setup correctly, updating DB")
    db = get_db()
    db.execute('UPDATE iso SET status = ? WHERE name = ?', ('Ready', name))
    db.commit()

    return True

def update_db_failed(name):
    db = get_db()
    db.execute('UPDATE iso SET status = ? WHERE name = ?', ('Failed', name))
    db.commit()

@celery.task()
def remove_image(name):
    print(f"Removing ISO {name} from DB")
    db = get_db()

    try:
        os.remove(f"{constants.IMAGE_FOLDER}/{name}.iso")
        print(f"ISO file {name} removed")
    except (OSError, FileNotFoundError):
        print(f"Error removing ISO file {name}")

    try:
        shutil.rmtree(f"{pathlib.Path(constants.IMAGE_FOLDER) / name}")
        print(f"Removed NFS share {name}")
    except (OSError, FileNotFoundError):
        print(f"Error removing NFS share {name}")

    try:
        shutil.rmtree(pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "images" / name)
        print(f"Removed UEFI TFTP image for {name}")
    except (OSError, FileNotFoundError):
        print(f"Error removing UEFI TFTP image for {name}")

    try:
        shutil.rmtree(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "images" / name)
        print(f"Removed BIOS TFTP image for {name}")
    except (OSError, FileNotFoundError):
        print(f"Error removing BIOS TFTP image for {name}")

    try:
        os.system(f"sed -i '/{name}/d' /etc/exports")
        os.system('exportfs -ra')
        print(f"Removed NFS share for {name} from exports")
    except Error:
        print(f"Error removing NFS share for {name} from exports file")

    try:
        os.remove(pathlib.Path(constants.UEFI_TFTPBOOT_DIR) / "pxelinux.cfg" / name)
        print(f"Removed UEFI pxelinux config for {name}")
    except (OSError, FileNotFoundError):
        print(f"Error removing UEFI pxelinux config for {name}")

    try:
        os.remove(pathlib.Path(constants.BIOS_TFTPBOOT_DIR) / "pxelinux.cfg" / name)
        print(f"Removed BIOS pxelinux config for {name}")
    except (OSError, FileNotFoundError):
        print(f"Error removing BIOS pxelinux config for {name}")

    db.execute('DELETE FROM iso WHERE name = ?', (name,))
    db.commit()
