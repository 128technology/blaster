# 128T Blaster #

This repository contains files and instructions that can be used to setup a basic "blaster" which can be used to install 128T software on bare metal hardware using a PXE boot mechanism.  It is the user's responsibility for working with the hardware vendor for instructions on how to enable PXE boot on any specific piece of hardware.  It is also the user's responsibility for ensuring hardware is delivered with appropriate BIOS configuration to enable PXE boot and the appropriate boot order.  This server supports PXE boot for both BIOS and UEFI mechamisms.

This software is provided as a 128T Community supported application and is not maintained by 128 Technology officially.  Any issues can be reported through this github repository with no guarantee that a fix will be provided and no SLA for any fix timeframes.

> **Current Release: v1.1, April 22, 2021
>
> Updates from v1.0:
> * Improved memory usage when downloading ISOs
> * Added button to search all conductors for assets matching hardware identifiers and automatically associate quickstarts
> * Proxy server support
> * Ability to disassociate a quickstart from a node after an association has been made
> * Ability to define custom passwords for root and t128 user to override ISO defaults
> * Update to handle new 128T Combined ISO format
> * Self-documentation in web UI
> * Update Manage nodes page to improve workflow of assigning quickstarts to nodes
>
> Note when upgrading from v1.0: A new table has been added to the database.  If you wish to keep your current data and not recreate the DB from scratch, follow this procedure on the docker host after performing the upgrade procedure:
> ```
> cd blaster/instance
> sqlite3 blaster.sqlite
> CREATE TABLE passwords (
>   username TEXT PRIMARY KEY,
>   password_hash TEXT
> );
> .quit
> ```
 
## Topology ##

![Blasting Architecture](./Blaster.png)

The above drawing illustrates the architecture of the Blaster.  The blasting server will need a minimum of two interfaces.  The first interface needs to be configured to connect into an existing LAN for management.  This LAN will need access out to the public Internet in order to obtain official 128T ISOs from the 128T yum servers and also to optionally obtain quickstart files from 128T Conductors.  The second interface needs to be connected to a dedicated switch or VLAN used exclusively for blasting purposes.

## Server Setup ##
The minimum requirements for the blaster server are 2 cores and 4GB RAM.  It is possible to run the blaster virtualized, but additional considerations need to be made.  The docker containers each use a unique MAC address which may conflict with a hypervisor's port security.  In this case, port security features must be disabled and potentially promiscuous mode turned on in the hypervisor's settings.  Additionally, the Linux OS for the guest may need promiscuous mode enabled on the second interface.

These instructions are based on a host system installed from a CentOS 1804 image.  Other Linux OS variants should be usable provided the setup instructions are modified appropriately.  The blasting interface must be configured with the static IP address of `192.168.128.128/24`.  Any software firewalls should be disabled on the blasting interface and set to allow HTTP and SSH traffic in on the management interface.

Please ensure that the server is not running the rpcbind service as this will conflict with the NFS capabilities of the blaster.
```
systemctl stop rpcbind
systemctl disable rpcbind
```

The blaster software is distributed through git and installed through docker.  The following sections should be run as root

### Install docker and docker compose ###
We will use docker to rapidly deploy the setup.  Please use the following commands to install docker:
```
yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo

yum install docker-ce docker-ce-cli containerd.io
```

Once docker is installed, start and enable the docker service:
```
systemctl start docker
systemctl enable docker
```

Install docker-compose to be able to build the monitoring server from the provided docker-compose.yml file:
```
curl -L "https://github.com/docker/compose/releases/download/1.25.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### Setup the environment file for variables  ###
Please create a file called `.env` in the root directory of the repo.  Its contents should resemble:
```
BLASTING_INTERFACE=XXX
```
Where `XXX` is the name of the Linux interface connected to the `192.168.128.0/24` network.

### Optionally setting a proxy server ###
If a proxy server is required in order to initiate outbound HTTPS connections, please edit the file `webapp/proxy.conf` to point to the appropriate proxy server. The format of this parameter is shown below.
```
HTTPS_PROXY=http://[username[:password]@]<proxy address>:<proxy port>
```
If you modify this file, please be sure to remove the comment at the beginning of the variable.

Note: If this parameter needs to be changed after the initial build of the blaster, please run the following commands on the blaster host to have these changes take effect:
```
docker-compose down
docker-compose build
docker-compose up -d
```

### Bring up the blaster ###
Use docker-compose to build the monitoring server by running the following command:
```
docker-compose up -d
```

### Initialize the DB ###
The first time you setup the blaster on a host machine, you need to initialize the DB.  This can be done with the following commands:
```
docker exec -it blaster_webapp_1 bash
cd /opt
flask init-db
exit
```

## Upgrading the Blaster ##
If new updates are available in the git repo, the following steps can be used to update your blaster:
```
git pull origin master
docker-compose down
docker-compose build
docker-compose up -d
```

## Using the Blaster ##
Once the docker containers are running, pointing a browser to the management IP of the blast server should load the blaster menu. The blaster is fully self-documented through the web iterface, but some high level instructions follow.

### Certificate Management ###
The certificate management menu provides options for managing your 128T yum certificate.  In order for the blaster to download official 128T ISOs, a valid yum certificate must be in place.

### ISO Management ###
The ISO management menu provides options for managing official 128T ISOs. ISOs can be downloaded from the 128T yum repo if a valid certificate was provided, or they can be uploaded manually. This menu is also where to select which ISO is "active" for blasting purposes.

### Conductor Management ###
If you wish to use the blaster as a quickstart server, you may want to use this functionality to extract quickstart data from one or more 128T conductors.

### Quickstart Management ###
This menu allows you to view all quickstarts staged on the blaster for bootstrapping and manually upload individual quickstarts.

### Manage Nodes ###
After a node has been blasted with an ISO, it will show up in this page allowing you to assign a quickstart file for bootstrapping.
