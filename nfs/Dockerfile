FROM centos:7

RUN ["yum", "-y", "install", "nfs-utils"]
RUN systemctl enable nfs
VOLUME /var/lib/nfs

RUN sed -i 's/^#MOUNTD_PORT=8192/MOUNTD_PORT=8192/' /etc/sysconfig/nfs
RUN sed -i 's/^#STATD_PORT=665/STATD_PORT=662/' /etc/sysconfig/nfs
RUN sed -i 's/^#STATD_OUTGOING_PORT=2020/STATD_OUTGOING_PORT=2020/' /etc/sysconfig/nfs

COPY lockd.conf /etc/modprobe.d/lockd.conf

EXPOSE 8192/udp 8192/tcp 662/udp 662/tcp 2020/udp 2020/tcp 34323/tcp 56513/udp

VOLUME ["/sys/fs/cgroup"]
ENTRYPOINT ["/usr/sbin/init"]
