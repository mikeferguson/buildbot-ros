#!/usr/bin/env python

# This is used to setup the cowbuilder

from __future__ import print_function
import sys
import os
import subprocess

# A bit hacky, but do this rather than redefine the function.
# Has to be in testbuild, as we only copy testbuild to pbuilder.
from testbuild import call

## @brief Returns the basepath of the cowbuilder
## @param distro The UBUNTU distribution (for instance, 'precise')
## @param arch The architecture (for instance, 'amd64')
def basepath(distro, arch):
    return '/var/cache/pbuilder/base-'+distro+'-'+arch+'.cow'

def defaultmirrors(distro):
    # cowdancer is in universe?
    return "deb http://archive.ubuntu.com/ubuntu DISTRO main universe".replace('DISTRO', distro)

def getKeyCommands(keys):
    if len(keys) == 0:
        return ""
    return '\n'.join(['wget '+key+' -O- | apt-key add -' for key in keys])+'\n'

## @brief Make a cowbuilder, if one does not exist
## @param distro The UBUNTU distribution (for instance, 'precise')
## @param arch The architecture (for instance, 'amd64')
## @param keys List of keys to get
def make_cowbuilder(distro, arch, keys):
    if not os.path.exists(basepath(distro, arch)):
        # create the cowbuilder
        call(['sudo', 'cowbuilder', '--create',
              '--distribution', distro,
              '--architecture', arch,
              '--debootstrapopts', '--arch',
              '--debootstrapopts', arch,
              '--basepath', basepath(distro, arch),
              '--othermirror', defaultmirrors(distro)])
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
    output = cowbuilder.communicate(input="""echo "Installing wget"
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
    if len(sys.argv) > 3:
        make_cowbuilder(distro, arch, sys.argv[3:])
    else:
        make_cowbuilder(distro, arch, [])
