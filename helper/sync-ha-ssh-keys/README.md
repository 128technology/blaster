# t128-sync-ha-ssh-keys.pyz
This application allows ensures ssh keys for HA Session Smart Routers (SSR) are synchronized during OTP installation.

## Setup
An OTP installation requires a so called quickstart file, which can be downloaded from the SSR conductor.

During the first boot from internal disk the bootstrap process can incorporate a USB drive connected to the router.
This USB drive has be named `BOOTSTRAP` and the downloaded quickstart file has to be renamed to `bootstrap.quickstart`.
Additionally two scripts can be triggered during the bootstrap process. `pre-bootstrap` runs as the first action prior to the default actions (setting the node name, copy config file to disk, ...) `post-bootstrap` runs as the last action before the router is rebooted and becomes active.

The `t128-sync-ha-ssh-keys.pyz` and its systemd service can be installed by the `post-bootstrap` script, which is part of this repository:

On macOS:

```
$ disk=/dev/disk<n>
$ target=/Volumes/BOOTSTRAP
$ diskutil eraseDisk FAT32 BOOTSTRAP MBR $disk
$ cp ~/Downloads/my-sample-router.quickstart $target/bootstrap.quickstart
$ cd sync-ha-ssh-keys
$ cp post-bootstrap $target/
$ diskutil eject $disk
```

On Linux:

```
$ disk=/dev/disk<n>
$ target=/mnt
$ sudo mkfs.vfat -F32 -n BOOTSTRAP $disk || sudo mkfs.ext4 -L BOOTSTRAP $disk
$ sudo mount $disk $target
$ sudo cp ~/Downloads/my-sample-router.quickstart $target/bootstrap.quickstart
$ cd sync-ha-ssh-keys
$ sudo cp post-bootstrap $target/
$ sudo umount $target
```

Details on the bootstrap process can be found [here](https://docs.128technology.com/docs/intro_otp_iso_install).

## Build .pyz Files
The .pyz files are [compressed python archives](https://docs.python.org/3/library/zipapp.html) (similar to .jar files in the Java universe) which allow to execute the main python script inside the archive, but at the same time split up modules into separate files/folders.

The source code at comes with a shell script `create_pyz.bash` that creates the archive from the sources files.

```
$ cd sync-ha-ssh-keys
$ bash create_pyz.bash
```

Done.
