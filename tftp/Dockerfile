FROM centos:7

RUN yum -y install tftp-server

VOLUME /var/lib/tftproot
EXPOSE 69/udp
ENTRYPOINT ["/usr/sbin/in.tftpd", "-L", "-s", "/var/lib/tftpboot"]
