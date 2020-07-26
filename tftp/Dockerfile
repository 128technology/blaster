FROM centos:7

RUN yum -y install epel-release
RUN yum -y install tftp-server lighttpd

RUN systemctl enable tftp
RUN systemctl enable lighttpd

RUN usermod -G root lighttpd

COPY lighttpd.conf /etc/lighttpd/lighttpd.conf

VOLUME /var/lib/tftpboot
EXPOSE 69/udp 80/tcp
VOLUME ["/sys/fs/cgroup"]
ENTRYPOINT ["/usr/sbin/init"]
