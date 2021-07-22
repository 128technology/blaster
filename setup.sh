#!/bin/bash

function determine_os {
  if [ ! -f /etc/os-release ]; then
    echo "Error Could not determine Linux variant, exiting..."
    exit 1
  fi
  source /etc/os-release
  echo "Detected OS: ${NAME}"
  case $ID in
    "centos")
      echo "OS appears to be centos"
      return 1
      ;;
    *)
      echo "Did not detect a supported OS, exiting..."
      exit 1
      ;;
  esac
}

function dnf_or_yum {
  PKGMGR=`which dnf`
  if [ $? -gt 0 ]; then
    PKGMGR=`which yum`
  fi
}

function determine_init_sys {
  if [ -d /run/systemd/system ]; then
    return 1
  fi

  echo "It doesn't appear that this OS uses systemd and is therefore not supported by this script, exiting..."
  exit 1
}

function centos_setup_and_install_docker {
  dnf_or_yum
  echo "Setting up Docker repo..."
  case $PKGMGR in
    *"dnf"*)
      $PKGMGR config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
      if [ $? -gt 0 ]; then
        echo "dnf returned error trying to setup docker repo, exiting..."
        exit 1
      else
        echo "docker repo setup successfully"
      fi
      ;;
    *"yum"*)
      yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
      if [ $? -gt 0 ]; then
        echo "yum returned error trying to setup docker repo, exiting..."
        exit 1
      else
        echo "docker repo setup successfully"
      fi
      ;;
    *)
      echo "Undetermined package manager, exiting..."
      exit 1
      ;;
  esac
  echo "Installing Docker..."
  $PKGMGR install docker-ce docker-ce-cli containerd.io iptables-services -y
  if [ $? -gt 0 ]; then
    echo "Issue installing docker, exiting..."
    exit 1
  else
    echo "docker installed successfully"
  fi
}

function install_docker_compose {
  which docker-compose
  if [ $? -eq 0 ]; then
    echo "docker-compose already installed"
    return 0
  fi
  echo "Downloading docker compose..."
  curl -L "https://github.com/docker/compose/releases/download/1.25.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  if [ $? -gt 0 ]; then
    echo "There was an issue downloading docker compose, exiting..."
    exit 1
  fi
  chmod +x /usr/local/bin/docker-compose
  echo "docker-compose successfully installed"
}

function systemd_setup_services {
  echo "Disabling NFS on host OS"
  systemctl stop rpcbind.service
  systemctl disable rpcbind.service
  systemctl stop rpcbind.socket
  systemctl disable rpcbind.socket
  echo "Starting and enabling docker"
  systemctl start docker.service
  systemctl enable docker.service
  systemctl enable iptables.service
}

function find_management_interface {
  which ip
  if [ $? -gt 0 ]; then
    echo "This system doesn't have the ip command, cannot auto-determine interfaces. Exiting..."
    exit 1
  fi
  AUTO_MGMT=`ip r get 8.8.8.8 | sed -En 's/^.*dev\s([a-zA-Z0-9_]+)\s.*$/\1/p'`
}

function get_interfaces {
  IIFS=( `ls /sys/class/net` )
  # Remove loopback
  IIFS=( ${IIFS[@]/lo} )
  # Remove docker0
  IIFS=( ${IIFS[@]/docker0} )
}

function setup_centos_blasting_interface {
ifdown $BLASTING_IF
cat > "/etc/sysconfig/network-scripts/ifcfg-$BLASTING_IF" << EOF
BOOTPROTO=none
DEVICE=$BLASTING_IF
IPADDR=192.168.128.128
PREFIX=24
ONBOOT=yes
TYPE=Ethernet
USERCTL=no
ZONE=trusted
NM_CONTROLLED=no
EOF
ifup $BLASTING_IF
}

function setup_iptables_rules {
iptables -A FORWARD -i $BLASTING_IF -j ACCEPT
iptables -A FORWARD -o $BLASTING_IF -j ACCEPT
iptables -t nat -A POSTROUTING -o $MGMT_IF -j MASQUERADE
service iptables save
}

################### Main logic #############
determine_os
OS=$?
determine_init_sys
INIT_SYS=$?

case $OS in 
  1)
    centos_setup_and_install_docker
    install_docker_compose
    ;;
  *)
    echo "This script doesn't know how to handle this OS, exiting..."
    exit 1
esac

case $INIT_SYS in
  1)
    systemd_setup_services
    ;;
esac

find_management_interface
while true; do
  echo "It appears that the managemnt interface on this server is $AUTO_MGMT"
  read -p "Is this correct? (entering \"list\" will show your interfaces) [yes/no/list] " INPUT
  case $INPUT in
    [Yy]*)
      MGMT_IF=$AUTO_MGMT
      break
      ;;
    [Nn]*)
      while true; do
        read -p "Please enter the management interface (entering \"list\" will show your interfaces)" INPUT2
        case $INPUT2 in
          "list") ip a ;;
          *)
            echo "/sys/class/net/$INPUT2"
            if [ -e "/sys/class/net/$INPUT2" ]; then
              MGMT_IF=$INPUT2
              break
            else
              echo "You did not enter a valid interface name"
            fi
            ;;
        esac
      done
      break
      ;;
    "list") ip a ;;
    *) echo "Please answer yes, no, or list" ;;
  esac
done

get_interfaces
IIFS=( ${IIFS[@]/$MGMT_IF} )
case ${#IIFS[@]} in
  0)
    echo "Could not find an additional interface for blasting. The blasting server requires two interfaces, exiting..."
    exit 1
    ;;
  1)
    while true; do
      echo "It appears that the blasting interface should be ${IIFS[0]}"
      read -p "Is this correct? (entering \"list\" will show your interfaces) [yes/no/list] " INPUT
      case $INPUT in
        [Yy]*)
          BLASTING_IF=${IIFS[0]}
          break
          ;;
        [Nn]*)
          echo "The script was unable to find a valid blasting interface, please configure network setup manually, exiting..."
          exit 1
          ;;
        "list") ip a ;;
        *) echo "Please answer yes, no, or list" ;;
      esac
    done
    ;;
  *)
    while true; do
      echo "It looks like these interfaces are available for the blasting network: ${IIFS[@]}"
      read -p "Please select an interface from this list (entering list will show your interface details)" INPUT
      case $INPUT in
        "list") ip a ;;
        *)
          if [[ " ${IIFS[@]} " =~ " ${INPUT} " ]]; then
            BLASTING_IF=$INPUT
            break
          else
            echo "$INPUT was not detected as a valid interface. Please select a valid interface or configure networking manually"
          fi
          ;;
      esac
    done
    ;;
esac

echo "Using Management interface: $MGMT_IF and blasting interface: $BLASTING_IF"
case $OS in
  1)
    setup_centos_blasting_interface
    setup_iptables_rules
    ;;
  *)
    echo "This script doesn't know how to handle this OS, exiting..."
    exit 1
esac

