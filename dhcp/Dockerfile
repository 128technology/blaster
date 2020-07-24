FROM centos:7

RUN ["yum", "-y", "install", "dhcp"]
RUN ["touch", "/var/lib/dhcpd/dhcpd.leases"]
COPY dhcpd.conf /etc/dhcp/dhcpd.conf
EXPOSE 67/udp 67/tcp
ENTRYPOINT ["/usr/sbin/dhcpd", "-f", "-cf", "/etc/dhcp/dhcpd.conf", "-d", "--no-pid"]

