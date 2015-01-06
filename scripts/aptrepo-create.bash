#!/bin/bash

# This script will create the 'building' APT repository
#  on the buildbot-ros master.

export REPO_DIR="/var/www/building/ubuntu"

# get command line params
if [[ ${#} -lt 1 ]]; then
    echo "Usage: ${0} <name> (archs) distro1 distro2 ..."
    exit -1
fi
export NAME=${1}
if [[ ${#} -lt 2 ]]; then
    export ARCHS="amd64 i386"
else
    export ARCHS=${2}
fi
if [[ ${#} -lt 3 ]]; then
    export DISTROS=(trusty)
else
    export DISTROS=${@:3}
fi

# Make sure directory does not exist
if [ -d "${REPO_DIR}" ]; then
  echo ""
  echo "ERROR: ${REPO_DIR} exists, please remove it."
  echo ""
  exit -1
fi

# Create it
mkdir -p ${REPO_DIR} || {
  echo "NOTE: this script should be run as buildbot."
  exit -1
}
chmod -R 755 ${REPO_DIR}
cd ${REPO_DIR}

mkdir conf
cd conf

for dist in ${DISTROS[*]}
do
    echo "Origin: ${NAME}" >> distributions
    echo "Label: ${NAME} $dist" >> distributions
    echo "Codename: $dist" >> distributions
    echo "Architectures: ${ARCHS}" >> distributions
    echo "Components: main" >> distributions
    echo "Description: ${NAME} Debian Repository" >> distributions
    #TODO SignWith???
    echo "" >> distributions
done

reprepro -V -b $REPO_DIR export

# Notify
echo ""
echo "APT Repository has been set up in ${REPO_DIR}"
echo "Please use scripts/reprepro-include.bash to add a package"
echo "You may also want to add a symlink in your apache repo to ${REPO_DIR}"
echo ""
