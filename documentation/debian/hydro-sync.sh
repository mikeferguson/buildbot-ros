#!/bin/bash

#  be sure to sudo apt-get install debmirror

arch=amd64,i386
section=main
release=precise
server=your.server.com
inPath=/building
proto=http
outPath=/var/www/your_repo

debmirror       -a $arch \
                --no-check-gpg \
                --no-source \
                -s $section \
                -h $server \
                -d $release \
                -r $inPath \
                --progress \
                -e $proto \
                $outPath
