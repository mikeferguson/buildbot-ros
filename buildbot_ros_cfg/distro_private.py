#
# Custom import for a rosdistro in a private git repository
# Checks out the distro to local disk and builds index from that copy
#

from __future__ import print_function
from rosdistro import *
import subprocess, sys

## @brief Call a command
def call(command):
    helper = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    while True:
        output = helper.stdout.readline().decode('utf8', 'replace')
        if helper.returncode is not None or not output:
            break
    helper.wait()
    if helper.returncode != 0:
        print('Failed to execute command "%s" with return code %d' % (command, helper.returncode))
        return

## @brief Function used to get a private index, for which we need to do git+ssh checkout
def get_private_index(url, branch = None):
    print('Getting private rosdistro from: %s' % url)
    call(['rm', '-rf', '/tmp/rosdistro'])
    if branch:
        call(['git', 'clone', '-b', branch, url, '/tmp/rosdistro'])
    else:
        call(['git', 'clone', url, '/tmp/rosdistro'])
    return get_index( 'file:///tmp/rosdistro/index.yaml' )
