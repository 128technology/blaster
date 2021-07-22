#!/bin/bash
NC='\033[0m' # No color
GREEN='\033[0;32m'
RED='\033[0;31m'

function determine_os {
  if [ ! -f /etc/os-release ]; then
    echo -e "${RED}Error Could not determine Linux variant, exiting...${NC}"
    exit 1
  fi
  source /etc/os-release
  echo -e "${GREEN}Detected OS: ${NAME}${NC}"
  case $ID in
    "centos")
      echo -e "${GREEN}OS appears to be centos${NC}"
      return 1
      ;;
    *)
      echo -e "${RED}Did not detect a supported OS, exiting...${NC}"
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

  echo -e "${RED}It doesn't appear that this OS uses systemd and is therefore not supported by this script, exiting...${NC}"
  exit 1
}

function centos_setup_and_install_docker {
  dnf_or_yum
  echo -e "${GREEN}Setting up Docker repo...${NC}"
  case $PKGMGR in
    *"dnf"*)
      $PKGMGR config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
      if [ $? -gt 0 ]; then
        echo -e "${RED}dnf returned error trying to setup docker repo, exiting...${NC}"
        exit 1
      else
        echo -e "${GREEN}docker repo setup successfully${NC}"
      fi
      ;;
    *"yum"*)
      yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
      if [ $? -gt 0 ]; then
        echo -e "${RED}yum returned error trying to setup docker repo, exiting...${NC}"
        exit 1
      else
        echo -e "${GREEN}docker repo setup successfully${NC}"
      fi
      ;;
    *)
      echo -e "${RED}Undetermined package manager, exiting...${NC}"
      exit 1
      ;;
  esac
  echo -e "${GREEN}Installing Docker...${NC}"
  $PKGMGR install docker-ce docker-ce-cli containerd.io iptables-services -y
  if [ $? -gt 0 ]; then
    echo  -e "${RED}Issue installing docker, exiting...${NC}"
    exit 1
  else
    echo -e "${GREEN}docker installed successfully${NC}"
  fi
}

function install_docker_compose {
  which docker-compose
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}docker-compose already installed${NC}"
    return 0
  fi
  echo -e "${GREEN}Downloading docker compose...${NC}"
  curl -L "https://github.com/docker/compose/releases/download/1.25.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  if [ $? -gt 0 ]; then
    echo -e "${RED}There was an issue downloading docker compose, exiting...${NC}"
    exit 1
  fi
  chmod +x /usr/local/bin/docker-compose
  echo -e "${GREEN}docker-compose successfully installed${NC}"
}

function systemd_setup_services {
  echo -e "${GREEN}Disabling NFS on host OS${NC}"
  systemctl stop rpcbind.service
  systemctl disable rpcbind.service
  systemctl stop rpcbind.socket
  systemctl disable rpcbind.socket
  echo -e "${GREEN}Starting and enabling docker${NC}"
  systemctl start docker.service
  systemctl enable docker.service
  systemctl enable iptables.service
}

function find_management_interface {
  which ip
  if [ $? -gt 0 ]; then
    echo -e "${RED}This system doesn't have the ip command, cannot auto-determine interfaces. Exiting...${NC}"
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

function is_firewalld {
systemctl status firewalld
return $?
}

function setup_firewalld_rules {
firewall-cmd --permanent --zone=trusted --add-interface=$BLASTING_IF
firewall-cmd --permanent --zone=external --add-interface=$MGMT_IF
firewall-cmd --permanent --zone=external --add-service=http
firewall-cmd --reload
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
    echo -e "${RED}This script doesn't know how to handle this OS, exiting...${NC}"
    exit 1
esac

case $INIT_SYS in
  1)
    systemd_setup_services
    ;;
esac

find_management_interface
while true; do
  echo -e "${GREEN}It appears that the managemnt interface on this server is $AUTO_MGMT${NC}"
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
            if [ -e "/sys/class/net/$INPUT2" ]; then
              MGMT_IF=$INPUT2
              break
            else
              echo -e "${RED}You did not enter a valid interface name${NC}"
            fi
            ;;
        esac
      done
      break
      ;;
    "list") ip a ;;
    *) echo -e "${RED}Please answer yes, no, or list${NC}" ;;
  esac
done

get_interfaces
IIFS=( ${IIFS[@]/$MGMT_IF} )
case ${#IIFS[@]} in
  0)
    echo -e "${RED}Could not find an additional interface for blasting. The blasting server requires two interfaces, exiting...${NC}"
    exit 1
    ;;
  1)
    while true; do
      echo -e "${GREEN}It appears that the blasting interface should be ${IIFS[0]}${NC}"
      read -p "Is this correct? (entering \"list\" will show your interfaces) [yes/no/list] " INPUT
      case $INPUT in
        [Yy]*)
          BLASTING_IF=${IIFS[0]}
          break
          ;;
        [Nn]*)
          echo -e "${RED}The script was unable to find a valid blasting interface, please configure network setup manually, exiting...${NC}"
          exit 1
          ;;
        "list") ip a ;;
        *) echo -e "${RED}Please answer yes, no, or list${NC}" ;;
      esac
    done
    ;;
  *)
    while true; do
      echo -e "${GREEN}It looks like these interfaces are available for the blasting network: ${IIFS[@]}${NC}"
      read -p "Please select an interface from this list (entering list will show your interface details)" INPUT
      case $INPUT in
        "list") ip a ;;
        *)
          if [[ " ${IIFS[@]} " =~ " ${INPUT} " ]]; then
            BLASTING_IF=$INPUT
            break
          else
            echo -e "${RED}$INPUT was not detected as a valid interface. Please select a valid interface or configure networking manually${NC}"
          fi
          ;;
      esac
    done
    ;;
esac

echo -e "${GREEN}Using Management interface: $MGMT_IF and blasting interface: $BLASTING_IF${NC}"
echo BLASTING_INTERFACE=$BLASTING_IF > .env
case $OS in
  1)
    setup_centos_blasting_interface
    setup_iptables_rules
    is_firewalld
    case $? in
      0)
        setup_firewalld_rules
        ;;
      [1-3])
        systemctl is-enabled firewalld
        if [ $? -eq 0 ]; then
          echo -e "${RED}Detected this system has firewalld and it is enabled but not running. Either start firewalld or disable firewalld and re-run.  Exiting...${NC}"
          exit 1
        fi
        ;;
    esac
    ;;
  *)
    echo -e "${RED}This script doesn't know how to handle this OS, exiting...${NC}"
    exit 1
esac

echo -e "${GREEN}Blaster setup complete, you may now continue to build and start the containers!${NC}"
