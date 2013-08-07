#!/bin/bash

# This script will add a deb to the 'building' APT repository, using reprepro

export REPO_DIR="/var/www/building/ubuntu"
export BUILD_DIR="/home/buildbot/buildbot-ros"

if [[ ${#} -lt 4 ]]; then
    echo "Usage: ${0} <pkg_name> <name.deb> <distro> <arch>"
    exit -1
fi
export PKG=${1}
export NAME=${2}
export DISTRO=${3}
export ARCH=${4}

# invalidate dependent
reprepro -V -b $REPO_DIR removefilter $DISTRO "Package (% * ), Architecture (==$ARCH), (Depends (% *$PKG[, ]* ) | Depends (% *$PKG ) )"

# invalidate this package
reprepro -V -b $REPO_DIR removefilter $DISTRO "Package (==$PKG), Architecture (==$ARCH)"

reprepro -V -b $REPO_DIR deleteunreferenced

reprepro -V -b $REPO_DIR includedeb $DISTRO $BUILD_DIR/binarydebs/$NAME
