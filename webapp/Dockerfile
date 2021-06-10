FROM centos:7

RUN yum -y install epel-release
RUN yum -y install python3 openssl redis nfs-utils xorriso

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# Disable NFSv4 since that seems to be causing a problem
RUN sed -i 's/RPCNFSDARGS.*/RPCNFSDARGS="--no-nfs-version 4"/' /etc/sysconfig/nfs

COPY run.py /opt/
RUN mkdir /opt/blaster/
COPY blaster/ /opt/blaster/
COPY celery_worker.py /opt/
COPY celery.service /etc/systemd/system/
RUN mkdir /etc/conf.d
COPY conf.d-celery /etc/conf.d/celery
COPY proxy.conf /etc/conf.d/proxy.conf
COPY webapp.service /etc/systemd/system
COPY setup_scripts.sh /opt/

RUN systemctl enable celery
RUN systemctl enable webapp
RUN systemctl enable redis
RUN systemctl enable nfs

ENV LC_ALL=en_US.UTF-8
ENV FLASK_APP="blaster.factory"

VOLUME /opt/instance/
VOLUME /opt/images/
VOLUME /opt/scripts/
VOLUME ["/sys/fs/cgroup"]
ENTRYPOINT ["/usr/sbin/init"]
