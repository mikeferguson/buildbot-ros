##Buildbot-ROS
This is a project for building ROS components using [Buildbot](http://buildbot.net/). This is not
aimed to be a replacement for the ROS buildfarm, but rather a (hopefully) easier to setup system
for developers wishing to build their own packages, run continuous integration testing, and build
docs.

##Design Overview
Buildbot uses a single master, and possibly multiple slaves. At present, the setup described below
will create a single slave on the same machine as the master. All of the setup is done under a
'buildbot' user account, and we use virtualenv so that your machine setup is not affected.

There are several job types available:
 * Debbuild - turns a gbp repository into a set of source and binary debs for a specific ROS distro
   and Ubuntu release. In the future, this should be triggered by rosdistro updates, currently it
   is a nightly job.
 * Buildtest - checks out a branch of a repository, builds, and runs tests. Triggered by a commit
   to the watched branch of the repository.
 * Docbuild - are built and uploaded to the master. Currently triggered nightly. In the future, a
   more elegant way of locating files correctly should be used.

##Comparison with ROS buildfarm
Buildbot-ROS uses mostly the same underlying tools as the ROS buildfarm. _Bloom_ is still used to
create gbp releases. _git-buildpackage_ is used to generate debians from the _Bloom_ releases,
using _cowbuilder_ to build in a chroot rather than _pbuilder_. _reprepro_ is used to update the
APT repository.

###Major differences from the ROS buildfarm:
 * Buildbot is completely configured in Python. Thus, the configuration for any build is simply a
   Python script, which I found to be more approachable than scripting Jenkins.
 * Currently, we build source and binary debians for an entire repository, which can consist of
   several packages and a metapackage, as one job per ROS/Ubuntu distribution combination.
 * The order of dependencies between packages (and between repositories) must be specified in the
   build configuration. In the future this should be read from a rosdistro file and automatically
   generated, as done on the ROS buildfarm.

###Known Limitations:
 * There is not yet a rosdistro tie-in to read the state of the rosdistro, determine updates, and
   trigger updated jobs. This is planned, but not implemented. In the meantime, debian builds are
   simply run nightly (and of course, are easily triggerable).
 * Buildtest jobs only work on git repositories.

##Setup for Buildbot Master
Install prerequisites:

    sudo apt-get install python-virtualenv python-dev

Create a user 'buildbot', log in as that user, and do the following:

    cd ~
    virtualenv --no-site-packages buildbot-env
    source buildbot-env/bin/activate
    easy_install buildbot
    git clone git@github.com:mikeferguson/buildbot-ros.git
    buildbot create-master buildbot-ros

At this point, you have a master, with the default configuration. You'll want to edit
buildbot-ros/master.cfg to add your own project settings (such as which rosdistro file to use),
and then start the buildbot:

    buildbot start buildobot-ros

To actually have debbuilders succeed, you'll need to create the APT repository for debs to be
installed into, as 'buildbot':

    cd buildbot-ros/scripts
    ./aptrepo-create.bash YourOrganizationName

By default, this script sets up a repository for amd64 and i386 on precise only. You can fully
specify what you want though:

    ./aptrepo-create.bash YourOrganizationName "amd64 i386 armel" precise oneiric hardy yeahright

When everything is working, buildbot can be added as a startup, by adding to the buildbot user's
crontab:

    TODO

##Setup for Buildbot Slave
We need a few things installed (remember, buildbot is not in the sudoers, so you should do this
under your own account):

    sudo apt-get install reprepro cowbuilder debootstrap devscripts git git-buildpackage debhelper

If you are on a different machine, you'll have to create the buildbot user and virtualenv as done
for the master. Once you have a buildbot user and virtualenv, do the following as 'buildbot':

    source buildbot-env/bin/activate
    easy_install buildbot-slave
    buildslave create-slave rosbuilder1 localhost:9989 rosbuilder1 mebuildslotsaros

It is probably a good idea to change the password (mebuildslotsaros), in both this command and the
master/master.cfg. You can also define additional slaves in the master/master.cfg file, currently
we define rosbuilder1 and 2. To start the slave:

    buildslave start rosbuilder1

For builds to succeed, you'll need to create a cowbuilder on the local machine. You will need to
run the script once for each architecture and distribution of Ubuntu that you want to build for:

    cd /home/buildbot/buildbot-ros/scripts
    sudo ./cowbuilder-create.bash precise amd64

##Known Issues
###pbuilder requires sudo privilege
The best way around this is to allow the 'buildbot' user to execute git-buildpackage and
pbuilder/cowbuilder without a password, by adding the following to your /etc/sudoers file
(be sure to use visudo):

    buildbot    ALL= NOPASSWD: SETENV: /usr/bin/git-*, /usr/sbin/*builder

Note that there is a TAB between buildbot and ALL.

###easy_install version of sqlalchemy causes buildbot scripts to fail
This is an incompatibility between version 0.7.x of sqlalchemy-migrate and 0.8 of sqlalchemy. The
quick fix is to edit a file in your virtualenv. In
/home/buildbot/buildbot-env/lib/python2.7/site-packages/sqlalchemy_migrate-0.*/migrate/versioning/schema.py
at line 10. change 'exceptions' to 'exc':

    from sqlalchemy import exc as sa_exceptions

