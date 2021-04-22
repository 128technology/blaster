# 128T Blaster #

This repository contains files and instructions that can be used to setup a basic "blaster" which can be used to install 128T software on bare metal hardware using a PXE boot mechanism.  It is the user's responsibility for working with the hardware vendor for instructions on how to enable PXE boot on any specific piece of hardware.  It is also the user's responsibility for ensuring hardware is delivered with appropriate BIOS configuration to enable PXE boot and the appropriate boot order.  This server supports PXE boot for both BIOS and UEFI mechamisms.

This software is provided as a 128T Community supported application and is not maintained by 128 Technology officially.  Any issues can be reported through this github repository with no guarantee that a fix will be provided and no SLA for any fix timeframes.

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
Once the docker containers are running, pointing a browser to the management IP of the blast server should load the blaster menu. The following sections provide information about each of the options from the main menu.

### Certificate Management ###
The certificate management menu provides options for managing your 128T yum certificate.  In order for the blaster to download official 128T ISOs, a valid yum certificate must be in place.  The `Add Certificate` page provides a portal to upload a certificate.  The `Show Esxisting Certtificate` option allows you to see details of a valid certificate, including the certificate expiration date.

### ISO Management ###
The ISO management menu provides options for managing official 128T ISOs.  The `List Availabile ISOs` option will use the uploaded yum certificate to provide a list of all available ISO images.  Clicking any one of these ISOs will start the process of downloading and preparing the ISO for PXE booting.  This process will take some time (one ISO should be setup at a time).

The `List ISOs` option will provide a list of all ISOs that the blaster knows about.  Each ISO in the list will show the name and status of the ISO.  Once an ISO has been selected from the `List Available ISOs` list, it will be put in the `Processing` state.  If an ISO shows a `Failed` state or stays in the `Processing` state for more than 10 minutes, logs should manually be investigated and the ISO should be deleted using the option from this page and retried from the `List Available ISOs` page.  Once the status shows `Ready`, it can be used for blasting.  Only one image is available for blasting at a time and will be identified with an `X` in the active column.  To make any successfully uploaded image active for blasting, click the `Set as Active` link next to that image.

Once an image is active, the blast systems are ready to start PXE booting following appropriate instructions from the hardware vendor.

### Conductor Management ###
If you wish to use the blaster as a quickstart server, you may wisth to use this functionality to pull quickstart data from one or more conductors.  The `Add Conductor` link will allow you to enter a meaningful name for the conductor, the URL to reach the conductor (base URL only, api endpoints will be added when needed), and login credentials.  The system will attempt to authenticate and retreive a token.  If there is a failure, you will be notified.  If authentication is successful, the token and conductor information will be saved in the DB.

The `List Configured Conductors` provides a listing of all conductors that were successfully added using the prior process.  Any conductor can be removed from the DB with the `Delete` link.  Using the `List Nodes` option will cause the blaster to query the conductor for all nodes via GraphQL and provdie a list of all non-conductor nodes including their router name, node name, and asset id.  Next to each node will be a `Download Quickstart` link.  Clicking this will cause the blaster to save the quickstart information for this node so that it can be used for bootstrapping with OTP ISOs (see the next section)

### Quickstart Management ###
These options can be used to manage quickstarts used for bootstrapping 128T ISO blasted systems.  The `Add Quickstart` link allows quickstarts to be uploaded to the blaster providing another mechanism aside from retreiving them directly from the Conductor API.  The conductor name, router name, and description fields are free form and are not validated against other tables or against quickstart contents.  At this time only non-password protected quickstart files are supported.  When retrieving quickstarts from conductor, be sure to delete the auto-generated password field from the quickstart download page before downloading the file.  Also note, at this time the conductor will not automatically populate the asset id field with the auto-generated asset id when downloading from conductor.  If you wish to use the auto-generated asset ID, please manually edit the downloaded quickstart file and set this as the value of the "a" option in the JSON data before uploading.  This limitation does not exist when automatically downloading quickstarts from conductor.

The `List Quickstarts` field provides data about all quickstart files that have been stored in the blaster's database.  You can click on a `Delete` link to remove a quickstart.  You can click on a `Set as Default` link to cause a specific quickstart to be offered to any device whose identifier is not already assigned to a specific quickstart (more on this in the next section).  This option is only available when no asset ID is associated with a quickstart.  You can click on `Unset as Default` if one is currently set as the default quickstart.  If a quickstart has an asset ID associated with it, you can click on `Remove Asset ID` to delete the asset ID associated with a quickstart.

NOTE: Setting asset ID during bootstrapping not currently supported and will need an update in OTP image creation.  The next paragraph explains the eventual usage.

A few notes about asset IDs.  If an asset ID is not explicitly configured when a node is created, the Conductor will automatically generate a random UUID to use.  When the OTP image is installed it will attempt to read the system's serial number from DMI and will configure this as the asset ID.  If the quickstart provides an asset ID, this will override the value that was detected by the OTP image.  In some cases you may prefer to use the serial number and update the conductor's configuration to match the serial number, in which case you would want to clear out any asset ID.  Also, you would not want every node to use the same asset id, so only quickstarts that do not have an asset ID can be selected for a default quickstart.  A default quickstart is useful if all systems for a deployment have a similar configuration with DHCP addressing, for example.

### Manage Nodes ###
When an ISO is staged, the blaster will add a step at the end of the kickstart that has the node send the blaster it's serial number.  If you click on `List Nodes`, you will see the list of system serial numbers along with the name of the ISO that they were blasted with.  If there is an assocication with a quickstart file, you will see the conductor name, router name, node name, and asset ID for the quickstart.

If you click the `Associate Nodes with Quickstarts` you will be presented with a list of all the quickstarts in the database in the format: `conductor_name:node_name.router_name` and a drop down box that lists all serial numbers that appear in the `List Nodes` page.  If you select one quickstart and one serial number and press submit, the blaster will make an associate between the quickstart and node and offer that quickstart to the node during bootstrapping.
