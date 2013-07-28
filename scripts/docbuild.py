#!/usr/bin/env python

# This file is the actual docbuild that is run

from __future__ import print_function
import sys, os, shutil, subprocess

## @brief Build the docs (using doxygen/epydoc/etc)
## @param workspace A bind-mounted directory to build from/in
## @param rosdistro The rosdistro to build for (for instance, 'groovy')
def run_docbuild(workspace, rosdistro):
    # Install depends
    call(['apt-get', 'update'])
    call(['apt-get', 'install', '--yes',
          'ros-%s-ros'%rosdistro,
          'ros-%s-rosdoc-lite'%rosdistro,
          'doxygen',
          'python-epydoc',
          'python-sphinx'])

    if os.path.exists(os.path.join(workspace, 'docs')):
        shutil.rmtree(os.path.join(workspace, 'docs'))

    ros_env = get_ros_env('/opt/ros/%s/setup.bash' % rosdistro)

    # Get a list of packages in our workspace
    packages = list()
    for f in os.listdir( os.path.join(workspace, 'src') ):
        print('Considering ' + os.path.join(workspace, 'src', f, 'package.xml'))
        if os.path.exists( os.path.join(workspace, 'src', f, 'package.xml') ):
            packages.append(f)
    print('Generating docs for: ' + ' '.join(packages))

    # For each package, call rosdoc_lite
    for package in packages:
        call([ 'rosdoc_lite',
               os.path.join(workspace, 'src', package),
               '-o', os.path.join(workspace, 'docs', package) ],
             ros_env)

    # Hack so the buildbot can delete this directory later
    call(['chmod', '-R', '777', os.path.join(workspace, 'docs')])

## @brief Call a command
## @param command Should be a list
def call(command, envir=None):
    print('Executing command "%s"' % ' '.join(command))
    helper = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True, env=envir)
    while True:
        output = helper.stdout.readline().decode('utf8', 'replace')
        if helper.returncode is not None or not output:
            break
        sys.stdout.write(output)

    helper.wait()
    if helper.returncode != 0:
        msg = 'Failed to execute command "%s" with return code %d' % (command, helper.returncode)
        print('/!\ %s' % msg)
        raise BuildException(msg)

## @brief imported from jenkins-scripts/common.py
def get_ros_env(setup_file):
    res = os.environ
    print('Retrieve the ROS build environment by sourcing %s' % setup_file)
    command = ['bash', '-c', 'source %s && env' % setup_file]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE)
    for line in proc.stdout:
        (key, _, value) = line.partition("=")
        res[key] = value.split('\n')[0]
    proc.communicate()
    if proc.returncode != 0:
        msg = 'Failed to source %s' % setup_file
        print('/!\  %s' % msg)
        raise BuildException(msg)
    return res

class BuildException(Exception):
    def __init__(self, msg):
        if os.path.exists(os.path.join(workspace, 'doc')):
            shutil.rmtree(os.path.join(workspace, 'doc'))
        self.msg = msg

if __name__=="__main__":
    if len(sys.argv) < 3:
        print('')
        print('Usage: docbuild.py <workspace> <rosdistro>')
        print('')
        exit(-1)
    workspace = sys.argv[1] # for cleanup
    run_docbuild(sys.argv[1], sys.argv[2])
