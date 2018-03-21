FROM ubuntu:trusty
MAINTAINER Michael Ferguson

ENV DEBIAN_FRONTEND noninteractive
ENV BUILDBOT_CREATED june_27_2014

# If using a private distro, need to setup keys for github
RUN mkdir -p /root/.ssh
ADD buildbot_id_rsa /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa
RUN echo "Host github.com\n\tStrictHostKeyChecking no\n" >> /root/.ssh/config

RUN apt-get update
RUN apt-get install -q -y openssh-server
RUN apt-get install -q -y python-virtualenv python-dev
RUN apt-get install -q -y reprepro cowbuilder debootstrap devscripts git git-buildpackage debhelper
RUN apt-get install -q -y debmirror

RUN virtualenv --no-site-packages /root/buildbot-env
RUN echo "export PATH=/root/buildbot-ros/scripts:${PATH}" >> /root/buildbot-env/bin/activate
RUN . /root/buildbot-env/bin/activate
RUN easy_install buildbot
RUN easy_install buildbot-slave
RUN pip install rosdistro
RUN git clone -b master git@github.com:mikeferguson/buildbot-ros.git /root/buildbot-ros
RUN buildbot create-master /root/buildbot-ros
RUN buildslave create-slave /root/rosbuilder1 localhost:9989 rosbuilder1 mebuildslotsaros

# Fix the file creation defaults
RUN cp /root/buildbot-ros/buildbot.tac /root/buildbot-ros/buildbot.tac.bk
RUN sed 's/umask = None/umask = 0022/' /root/buildbot-ros/buildbot.tac.bk > /root/buildbot-ros/buildbot.tac
RUN cp /root/rosbuilder1/buildbot.tac /root/rosbuilder1/buildbot.tac.bk
RUN sed 's/umask = None/umask = 0022/' /root/rosbuilder1/buildbot.tac.bk > /root/rosbuilder1/buildbot.tac

# magic hack to fix openssh on trusty
RUN sed --in-place=.bak 's/without-password/yes/' /etc/ssh/sshd_config

EXPOSE 22
EXPOSE 8010

ADD run_server /root/run_server
RUN chmod 755 /root/run_server

# setup ssh, set pass to buildbot (mega security!)
RUN mkdir /var/run/sshd
RUN echo 'root:buildbot' | chpasswd

# setup keys
ADD key.gpg /root/key.gpg
ADD secret.gpg /root/secret.gpg
RUN gpg --import /root/key.gpg
RUN gpg --allow-secret-key-import --import /root/secret.gpg

# cleanup keys after they are imported
RUN rm /root/key.gpg
RUN rm /root/secret.gpg

CMD /root/run_server
