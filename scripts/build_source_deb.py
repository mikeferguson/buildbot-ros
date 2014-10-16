#!/usr/bin/env python
'''
Wrapper around git-buildpackage to deal with the change in the way that it
interprets arguments between the version that ships with ubuntu 12.04 and
the version that ships with Ubuntu 14.04.

In older versions of git-buildpackage, the --git-upstream argument could refer
to either a branch or a tag name (bloom uses tags). In recent versions of
git-buildpackage, --git-upstream can only refer to a branch. To get around this,
this script accepts the old style arguments and modifies them to work with the
version of git-buildpackage on this system.

For more information on this issue, see
https://github.com/mikeferguson/buildbot-ros/issues/33
and
https://github.com/ros-infrastructure/bloom/issues/211
'''
import sys
import re
import os
import subprocess

def get_buildpackage_version():
    '''
    Return the installed version of git-buildpackage as a tuple of three ints
    '''
    version_output = subprocess.check_output(['git-buildpackage', '--version'])
    m = re.match('git-buildpackage\s+([0-9]+)\.([0-9]+)\.([0-9]+)\s*', version_output)
    if m:
        return tuple([int(x) for x in m.groups()])
    return None

# Parse command line args
rosdistro, package, release_version = sys.argv[1:4]
gbp_args = sys.argv[4:]

# Create a git-buildpackage command appropriate for this slave
version = get_buildpackage_version()
print 'Detected git-buildpackage version' + str(version)
if version[1] >= 6:
    # This is a new version of git-buildpackage. It knows about the --git-upstream-tree arg
    command = ['git-buildpackage', '-S', '--git-upstream-tree=TAG',
        '--git-upstream-tag=release/{rosdistro}/{package}/{release_version}'.format(
            rosdistro=rosdistro, package=package, release_version=release_version)] + gbp_args
else:
    command = ['git-buildpackage', '-S'] + gbp_args

# Call out to git-buildpackage
print 'Running git-buildpackage command: ' + str(command)
sys.stdout.flush()
os.execlp('git-buildpackage', *command)

