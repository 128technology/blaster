# Installation Process #
In a standard case, the `setup.sh` script should perform these functions for you. But if that fails, or you are attempting to use a host OS that is not yet supported by the setup script, these are the full instructions on how to setup the blaster host.

Please ensure that the server is not running the rpcbind service as this will conflict with the NFS capabilities of the blaster.
```
systemctl stop rpcbind.service
systemctl disable rpcbind.service
systemctl stop rpcbind.socket
systemctl disable rpcbind.socket
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

### Setup the networking ###
Configure the blasting interface to be address `192.168.128.128/24`. The blaster currently only supports using this address. It is recommended to do this through modifying the interface's ifcfg files so that the address is persistent on reboot.

Additionally, it is recommended to enable IP masquerade on the management interface and allow IP forwarding between the blast and management networks in iptables. This allows the blasted nodes to perform an NTP sync to public NTP servers during bootstrapping and additionally other operations added in bootstrap scripts.
```
yum install iptables-service
systemctl enable iptables-service
iptables -A FORWARD -i $BLASTING_IF -j ACCEPT
iptables -A FORWARD -o $BLASTING_IF -j ACCEPT
iptables -t nat -A POSTROUTING -o $MGMT_IF -j MASQUERADE
service iptables save
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
