#!/usr/bin/env python

# This is used to setup the cowbuilder

from __future__ import print_function
import sys
import os
import subprocess
import time

# A bit hacky, but do this rather than redefine the function.
# Has to be in testbuild, as we only copy testbuild to pbuilder.
from testbuild import call

import random
file_num = random.randrange(100000)

## @brief Returns whether we could lock the file
def get_lock(distro, arch):
    global file_num
    if os.path.isfile('/tmp/buildbot_'+distro+'_'+arch+'_lock'):
        # check if our file_num is in the file
        try:
            with open('/tmp/buildbot_'+distro+'_'+arch+'_lock') as f:
                value = int(f.read().rstrip())
                if value == file_num:
                    return True
                else:
                    # somebody already has a lock
                    return False
        except:
            return False
    else:
        # try to put our file_num in the lock file:
        with open('/tmp/buildbot_'+distro+'_'+arch+'_lock', 'w') as f:
            f.write(str(file_num))
        # wait a moment
        time.sleep(0.05)
        # check that we got the lock
        return get_lock(distro, arch)

def release_lock(distro, arch):
    if os.path.isfile('/tmp/buildbot_'+distro+'_'+arch+'_lock'):
        # check if our file_num is in the file
        try:
            with open('/tmp/buildbot_'+distro+'_'+arch+'_lock') as f:
                value = int(f.read().rstrip())
                if value == file_num:
                    os.remove('/tmp/buildbot_'+distro+'_'+arch+'_lock')
                    return True
                else:
                    # somebody already has a lock
                    return False
        except:
            return False
    return False

## @brief Returns the basepath of the cowbuilder
## @param distro The UBUNTU distribution (for instance, 'precise')
## @param arch The architecture (for instance, 'amd64')
def basepath(distro, arch):
    return '/var/cache/pbuilder/base-'+distro+'-'+arch+'.cow'

def defaultmirrors(distro, arch):
    # cowdancer is in universe?
    if (arch == "amd64" or arch == "i386"):
        # use ubuntu archive for x86 or x64 cowbuilders
        return "deb http://archive.ubuntu.com/ubuntu DISTRO main universe".replace('DISTRO', distro)
    else:
        # use ubuntu ports for other cowbuilders (such as arm)
        return "deb http://ports.ubuntu.com/ubuntu-ports DISTRO main universe".replace('DISTRO', distro)

def getKeyCommands(keys):
    if len(keys) == 0:
        return ""
    return '\n'.join(['wget '+key+' -O- | apt-key add -' for key in keys])+'\n'

## @brief Make a cowbuilder, if one does not exist
## @param distro The UBUNTU distribution (for instance, 'precise')
## @param arch The architecture (for instance, 'amd64')
## @param keys List of keys to get
def make_cowbuilder(distro, arch, keys):
    print('(' + str(time.time()) +')Getting lock on cowbuilder')
    while not get_lock(distro, arch):
        time.sleep(1.0)
    print('(' + str(time.time()) +')Got lock!')
    if not os.path.exists(basepath(distro, arch)):
        # create the cowbuilder
        call(['sudo', 'cowbuilder', '--create',
              '--distribution', distro,
              '--architecture', arch,
              '--debootstrapopts', '--arch',
              '--debootstrapopts', arch,
              '--basepath', basepath(distro, arch),
              '--othermirror', defaultmirrors(distro, arch)])
    else:
        print('cowbuilder already exists for %s-%s' % (distro, arch))

    # login and install wget (for later adding keys)
    command = ['sudo', 'cowbuilder', '--login',
               '--save-after-login',
               '--distribution', distro,
               '--architecture', arch,
               '--basepath', basepath(distro, arch)]
               #'--othermirror', defaultmirrors(distro)]
    print('Executing command "%s"' % ' '.join(command))
    cowbuilder = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = cowbuilder.communicate(input="""echo "Installing python"
apt-get install python -y
echo "Installing wget"
apt-get install wget -y
"""+getKeyCommands(keys)+"""echo "exiting"
exit
""")
    print(output[0])
    if cowbuilder.returncode != 0:
        exit(cowbuilder.returncode)

    # update
    print('updating cowbuilder')
    call(['sudo', 'cowbuilder', '--update',
          '--distribution', distro,
          '--architecture', arch,
          '--basepath', basepath(distro, arch)])

if __name__=="__main__":
    if len(sys.argv) < 3:
        print('')
        print('Usage: cowbuilder.py <distro> <arch>')
        print('')
        exit(-1)
    distro = sys.argv[1]
    arch = sys.argv[2]
    try:
        if len(sys.argv) > 3:
            make_cowbuilder(distro, arch, sys.argv[3:])
        else:
            make_cowbuilder(distro, arch, [])
    finally:
        release_lock(distro, arch)
