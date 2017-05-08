# Buildbot-ROS
This is a project for building ROS components using [Buildbot](http://buildbot.net/). This is not
aimed to be a replacement for the ROS buildfarm, but rather a (hopefully) easier to setup system
for developers wishing to build their own packages, run continuous integration testing, and build
docs.

Please see the mailing list for discussions about setup, usage, and new features: https://groups.google.com/forum/#!forum/buildbot-ros-sig

## Release Notes

 * 0.3.0 (forthcoming) - will support REP-143
 * 0.2.0 (02/20/2016) - supports Trusty, adds github pull request builders
 * 0.1.0 (09/13/2014) - first tagged release, does not support Trusty.

## Design Overview
Buildbot uses a single master, and possibly multiple machines building. At present, the setup
described below will do all builds on the same machine as the master. All of the setup is done under
a 'buildbot' user account, and we use virtualenv and cowbuilder so that your machine setup is not
affected.

There are several 'builder' types available:
 * Debbuild - turns a gbp repository into a set of source and binary debs for a specific ROS distro
   and Ubuntu release. This is currently run in a nightly build.
 * Testbuild - this is a standard continuous integration testing setup. Checks out a branch of a
   repository, builds, and runs tests using catkin. Triggered by a commit to the watched branch
   of the repository. In the future, this could also be triggered by a post commit hook giving even
   faster response time to let you know that you broke the build or tests (buildbot already has nice
   GitHub post-commit hooks available). Test builds can also be done on pull requests.
 * Docbuild - are built and uploaded to the master. Currently triggered nightly and generating only
   the doxygen/epydoc/sphinx documentation (part of the docs you find on ros.org). Uses rosdoc_lite.
   Documentation builds can only be run on released repositories.
   Presently, I do a soft link from my Apache server install to the /home/buildbot/buildbot-ros/docs
   directory, but in the future, a more elegant solution to this should be implemented.

There are also several builders that are not directly related to ROS, but generally useful:
 * Launchpad - sometimes you need a regular old debian that just happens to not be available. This
   builder is called 'launchpad_debbuild' because I mainly use it to build sourcedebs from Launchpad
   into binaries, however, it can be used with any sourcedeb source.

Clearly, this is still a work in progress, but setup is fairly quick for a small set of projects.

## Comparison with ROS buildfarm
Buildbot-ROS uses mostly the same underlying tools as the ROS buildfarm. _Bloom_ is still used to
create gbp releases. _git-buildpackage_ is used to generate debians from the _Bloom_ releases,
using _cowbuilder_ to build in a chroot rather than _pbuilder_. _reprepro_ is used to update the
APT repository. Docs are generated using _rosdoc_lite_. The build is defined by a _rosdistro_
repository, and we use the _python-rosdistro_ package to parse it.

### Major differences from the ROS buildfarm:
 * Buildbot is completely configured in Python. Thus, the configuration for any build is simply a
   Python script, which I found to be more approachable than scripting Jenkins.
 * Source and binary debians for an entire repository, which can consist of several packages and a
   metapackage, are built as one job per ROS/Ubuntu distribution combination.

### Known Limitations:
 * While jobs are configured from a rosdistro, there currently isn't a scheduler that updates
   based on rosdistro updates (See #3). This is planned, but not implemented. Currently, you can
   make do by having a nightly cronjob that runs 'restart' on the buildbot instance.
 * file:/// repositories are not yet actually being bind-mounted (#10)
 * Test and doc jobs only work on git repositories.

## Setup of ROSdistro
Before you can build jobs, you will need a _rosdistro_ repository. The rosdistro format is specified
in [REP137](http://ros.org/reps/rep-0137.html). You'll need an index.yaml and at least one set of
distribution files (release.yaml, source.yaml, doc.yaml, *-build.yaml). A complete example of a
simple build configuration for a single repository can be found in
https://github.com/mikeferguson/rosdistro-buildbot-example.

In addition to the usual aspects of the files, we extensively use apt_mirrors, and a new key
apt_keys. These should be setup to a list of APT mirrors and set of keys to pull for these mirrors.
The mirrors will be passed to the cowbuilder using the _--othermirror_ option, while the keys will
be fetched and stored during the cowbuilder setup step. The format of the apt_mirrors is important,
the format should be:

    http://location DISTRO main othersections

The DISTRO will be replaced by the actual building distribution at build time. At a minimum, you
will want an Ubuntu archive, the ROS archive, and your building archive. The Ubuntu archive should
include the _universe_ section if you want to run docbuilders.

The rosdistro tools need a path to cache. While buildbot-ros does not require a cache to operate,
creating one can greatly speed up startup of the buildbot master. To create the cache, you can use:

    rosdistro_build_cache path_to_index.yaml

And then upload this to the destination of the cache. Currently, buildbot-ros does not update the
cache automatically.

## Setup for Buildbot Master
Install prerequisites:

    sudo apt-get install python-virtualenv python-dev

Create a user 'buildbot'. Make sure you don't leave the Name field blank - if you do you'll end up
with incorrect syntax in the deb changelogs, because git-dch uses the user's actual name in the changelog.
Log in as the buildbot user, and do the following:

    cd ~
    virtualenv --no-site-packages buildbot-env
    source buildbot-env/bin/activate
    echo "export PATH=/home/buildbot/buildbot-ros/scripts:${PATH}" >> buildbot-env/bin/activate
    easy_install buildbot==0.8.12 requests
    pip install rosdistro
    git clone https://github.com/mikeferguson/buildbot-ros.git
    buildbot create-master buildbot-ros

If using the Pull Request builder, you will also need to:

    sudo apt-get install libffi-dev libssl-dev
    easy_install txgithub

At this point, you have a master, with the default configuration. You will almost certainly want to
edit buildbot-ros/buildbot.tac and set the line 'umask=None' to 'umask=0022' so that uploaded debs
can be found by your webserver. You'll also want to edit buildbot-ros/master.cfg to add your own
project settings (such as which rosdistro file to use), and then start the buildbot:

    buildbot start buildbot-ros

To actually have debbuilders succeed, you'll need to create the APT repository for debs to be
installed into, as 'buildbot':

    cd buildbot-ros/scripts
    ./aptrepo-create.bash YourOrganizationName

By default, this script sets up a repository for amd64 and i386 on trusty only. You can fully
specify what you want though:

    ./aptrepo-create.bash YourOrganizationName "amd64 i386 armel" precise oneiric hardy yeahright

If you want to sign your repository, you need to generate a GPG key for reprepro to use:

    gpg --gen-key

Use _gpg --list-keys_ to find the key identifier (for instance AAAABBBB) and add a line in the
/var/www/building/ubuntu/conf/distributions file with:

    SignWith: AAAABBBB

You'll likely want to export the public key:

    gpg --output /var/www/public.key --armor --export AAAABBBB

When everything is working, buildbot can be added as a startup, by adding to the buildbot user's
crontab. Open up the crontab for the buildbot user by typing `crontab -e`, then you can use this line to restart the buildbot instance every day at 11pm for example. The second line added to the crontab is optional, it reloads the cache before restarting the buildbot instance. If you use it, don't forget to replace `/path/to/index.yaml` with the real path to you `index.yaml` distribution file.

    0 23 * * * cd /home/buildbot && buildbot restart buildbot-ros
    55 22 * * * cd /var/www/html/rosdistro && rosdistro_build_cache /path/to/index.yaml

### Setup for Pull Requests

To enable pull requests, the oauth_tokens must be configured. To create an oauth token,
go to settings under your github account, go to "Personal access tokens" and generate
a new token for the buildbot, then update the oauth_tokens in master.cfg:

    # Pull request builder tokens (should not be stored in rosdistro)
    # This is a mapping of "repo" -> "token"
    # If a repo has no entry, then pull request builder will not be started
    oauth_tokens = dict()
    oauth_tokens["first_repo"] = "1251511615134513413541351acea1ave"
    oauth_tokens["second_repo"] = "1251511615134513413541351acea1ave"

## Setup for Buildbot Slave
We need a few things installed (remember, buildbot is not in the sudoers, so you should do this
under your own account):

    sudo apt-get install reprepro cowbuilder debootstrap devscripts git git-buildpackage debhelper

If you are on a different machine, you'll have to create the buildbot user and virtualenv as done
for the master. Once you have a buildbot user and virtualenv, do the following as 'buildbot':

    source buildbot-env/bin/activate
    easy_install buildbot-slave
    echo "export PATH=/home/buildbot/buildbot-ros/scripts:${PATH}" >> buildbot-env/bin/activate
    buildslave create-slave rosbuilder1 localhost:9989 rosbuilder1 mebuildslotsaros

If you are on a diffent machine then you will need to clone the buildbot-ros repo on it as well.
Again as the buildbot user:

    git clone https://github.com/mikeferguson/buildbot-ros.git

As with the master, change umask to be 0022 in the .tac file.
It is probably a good idea to change the password (mebuildslotsaros), in both this command and the
master/master.cfg. You can also define additional slaves in the master/master.cfg file, currently
we define rosbuilder1 and 2. To start the slave:

    buildslave start rosbuilder1

For builds to succeed, you'll probably need to make it so the buildbot can run cowbuilder as root.
The best way around this is to allow the 'buildbot' user to execute git-buildpackage and
pbuilder/cowbuilder without a password, by adding the following to your /etc/sudoers file
(be sure to use visudo):

    buildbot    ALL= NOPASSWD: SETENV: /usr/bin/git-*, /usr/sbin/*builder

Note that there is a TAB between buildbot and ALL.

## Known Issues, Hacks, Tricks and Workarounds

### I need to move my gpg key (also known as 'my server has all the entropy of a dead cow!')
On the machine with the key

    gpg --output key.gpg --armor --export AAAABBBB
    gpg --output secret.gpg --armor --export-secret-key AAAABBBB

On the other machine:

    gpg --import key.gpg
    gpg --allow-secret-key-import --import secret.gpg

### buildbot will only allow 1000 unique jobs
This will prevent you from loading the entire ROS farm as is, unless different arch/code-name combinations
are restricted to different buildbots. There is a monkey-patch available here:
http://trac.buildbot.net/ticket/2045

### private repositories and dependencies
See https://github.com/mikeferguson/buildbot-ros/blob/master/documentation/private_repositories.md
