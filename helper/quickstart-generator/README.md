# quickstart-generator.py
This application creates a generic quickstart file, which can be used to provision a Session Smart Router (SSR) during OTP installation.

## Installation
The python application requires additional python packages, which are listed in the `requirements.txt` file.

To install all packages, a python virtualenv is recommended:

```
$ cd quickstart-generator
$ python3 -m venv venv
$ venv/bin/pip install -r requirements.txt
```

## OTP Preparation
An OTP installation requires a quickstart file, which can be downloaded from the SSR conductor.

During the first boot from internal disk the bootstrap process can incorporate a USB drive connected to the router.
This USB drive must have the label `BOOTSTRAP` and the downloaded quickstart file has to be named `bootstrap.quickstart`.
Additionally two scripts can be triggered during the bootstrap process. `pre-bootstrap` runs as the first action prior to the default actions (setting the node name, copy config file to disk, ...) `post-bootstrap` runs as the last action before the router is rebooted and becomes active.

Instead of using a router-specific quickstart file from conductor, this application can create a generic file, which just contains the IP address of the SSR conductor and network interface config needed to connect to the conductor. Afterwards the router gets it actual (router-specific) config by the conductor.

The application is configured by a file in yaml file like the following:

```
$ cp sample-parameters.yml parameters.yml
$ vi parameters.yml
# the conductor IP address(es) - specify both to connect to an HA conductor
conductors:
- 10.0.0.1
- 10.0.0.2

# network interfaces needed to create the conductor connection - used in this order
interfaces:
- name: wan1
  proto: dhcp
  pci_address: "0000:00:12.0"
# - name: wan2
#   proto: dhcp
#   pci_address: "0000:00:13.0"
# - name: lte1
#   type: lte
#   target_interface: wwp0s20u5i4
#   apn: sample-apn
#   user: jdoe
#   password: secret
#   auth: chap
```

After adjusting the `parameters.yml` call the application:

```
$ venv/bin/python3 quickstart-generator.py -p parameters.yml -q generic.quickstart
```

Now copy the `generic.quickstart` file to the USB drive.

On macOS:

```
$ disk=/dev/disk<n>
$ target=/Volumes/BOOTSTRAP
$ diskutil eraseDisk FAT32 BOOTSTRAP MBR $disk
$ cp generic.quickstart $target/bootstrap.quickstart
$ diskutil eject $disk
```

On Linux:

```
$ disk=/dev/sd<n>
$ target=/mnt
$ sudo mkfs.vfat -F32 -n BOOTSTRAP $disk || sudo mkfs.ext4 -L BOOTSTRAP $disk
$ sudo mount $disk $target
$ cp generic.quickstart $target/bootstrap.quickstart
$ sudo umount $target
```

The USB drive can be plugged into a freshly installed SSR router and router can be powered on.

Details on the bootstrap process can be found [here](https://docs.128technology.com/docs/intro_otp_iso_install).