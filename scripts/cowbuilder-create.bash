#!/bin/bash

# This script will create a cowbuilder for a specific distro and architecture,
#  for use with buildbot-ros. The output cowbuilder will be in
#  /var/cache/pbuilder/base-<distro>-<arch>.cow'

# get command line params
if [[ ${#} -lt 2 ]]; then
    echo ""
    echo "Usage: ${0} <distro> <arch>"
    echo ""
    exit -1
fi
DISTRO=${1}
ARCH=${2}

# cowbuilder params
COW_ARGS="--distribution $DISTRO --architecture $ARCH --basepath /var/cache/pbuilder/base-$DISTRO-$ARCH.cow"

export OTHERMIRROR="deb http://archive.ubuntu.com/ubuntu ${DISTRO} main restricted universe multiverse |
deb http://archive.ubuntu.com/ubuntu ${DISTRO}-backports main restricted universe multiverse |
deb http://archive.ubuntu.com/ubuntu ${DISTRO}-security main restricted universe multiverse |
deb http://archive.ubuntu.com/ubuntu ${DISTRO}-updates main restricted universe multiverse |
deb http://packages.ros.org/ros-shadow-fixed/ubuntu precise main"

echo ""
echo "Creating the cowbuilder instance, this can take a while..."
echo ""
cowbuilder --create $COW_ARGS --othermirror "${OTHERMIRROR}" || { exit -1; }

# login and get ROS key
cowbuilder --login --save-after-login $COW_ARGS  << DELIM
echo "Installing wget"
apt-get install wget -y
echo "Adding key"
wget http://packages.ros.org/ros.key -O- | apt-key add -
echo "exiting.."
exit
DELIM

cowbuilder --update --override-config $COW_ARGS
