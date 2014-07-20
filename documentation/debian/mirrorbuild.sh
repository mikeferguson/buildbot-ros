#!/bin/bash

# Setup required:
#  sudo apt-get install debmirror
#  sudo mkdir /home/mirrorkeyring
#  sudo gpg --no-default-keyring --keyring /home/mirrorkeyring/trustedkeys.gpg --import /usr/share/keyrings/ubuntu-archive-keyring.gpg
#
#  sudo crontab -e
#  30 0 * * * <buildfarm>/mirrorbuild.sh
#  sudo /etc/init.d/cron restart

#
# Don't touch the user's keyring, have our own instead
#
export GNUPGHOME=/home/mirrorkeyring

arch=amd64,i386
section=main,universe
release=precise
server=us.archive.ubuntu.com
inPath=/ubuntu
proto=http
outPath=/var/www/ubuntu

# The --nosource option only downloads debs and not deb-src's
# The --progress option shows files as they are downloaded
# --source \ in the place of --no-source \ if you want sources also.
# --nocleanup  Do not clean up the local mirror after mirroring is complete. Use this option to keep older repository
debmirror       -a $arch \
                --no-source \
                --exclude='i386.deb' \
                -s $section \
                -h $server \
                -d $release \
                -r $inPath \
                --progress \
                -e $proto \
                $outPath
