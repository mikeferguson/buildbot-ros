##Using Private Repositories with Buildbot-ROS

A common use case of buildbot-ros is to build from private GBP or source
repositories, typically hosted on Github. This can be accomplished by adding
SSH keys for your buildbot slaves (it is recommended to make them read-only),
and then using the git+ssh URL in your rosdistro. If your private packages
depend only on publicly available packages, then all is good. However,
if you have a private package which depends on another private package, there
is some extra work involved.

###Overview of dependency calculation

There are two points in the build infrastructure where dependencies are used:

 * when packages are released using _bloom-release_, bloom must convert all
   dependencies found in the package.xml into the name of a debian package.
 * when building a source repository on the buildfarm, the buildbot must
   install the correct debian package dependencies, again computed from the
   package.xml

In both of these cases, _rosdep_ is used. In the public ROS ecosphere there
are two types of dependencies: ROS packages and other system dependencies.
Because of this, _rosdep_ gets it's information in two ways. In the case of
system dependencies, these are hand coded in the YAML files found in the 
rosdep folder of the rosdistro. In the case of ROS packages, it is pulled from
the distributions.yaml. Your private packages appear in neither of these
places.

###Solution for bloom-release
The simplest solution for building on top of an existing rosdistro is to add
manual rosdep keys for your unlisted packages. Since you are already
maintaining a separate rosdistro, you can easily _rosdep/private.yaml_ file.
In order to use these private keys, you need to add them to your rosdep lists.
Since rosdep does not like to check out private repositories, the best solution
is to manually check it out on your system and point your rosdep lists at it,
by adding a line to /etc/ros/rosdep/sources.list.d like:

        yaml file:///home/myuser/myrosdistro/rosdep/private.yaml

The private.yaml will look something like:

        my_private_package1:
          ubuntu: ros-hydro-my-private-package1
        my_private_package2:
          ubuntu: ros-hydro-my-private-package2

You can then _rosdep update_ and run _bloom-release_ as usual.

If you run into an error about a missing dependency for the 'heisenbug'
distribution when running bloom-release, you will need to add a second line
for each of your packages, so that it looks like:

        my_private_package1:
          ubuntu: ros-hydro-my-private-package1
          fedora: ros-hydro-my-private-package1
        my_private_package2:
          ubuntu: ros-hydro-my-private-package2
          fedora: ros-hydro-my-private-package2

This is because of https://github.com/ros-infrastructure/bloom/issues/296

###Solution for build time dependencies
When building and testing the source repositories, there is a horrible hack
in buildbot-ros, which assumes that any unresolved dependencies are in fact
private and unlisted catkin packages. Thus, it resolves a missing _package_name_
to _ros-distro-package-name_. This can cause interesting error messages when
packages that are not ROS packages are not in your rosdep, but it solves the
dependency calculation for packages which are not in the public rosdistro.

###Using a private rosdistro
In addition to private repositories, buildbot-ros can be used with an entirely
private rosdistro. In the default master.cfg, the index is typically taken
from a raw.github address by calling:

        get_index('https://raw.github.com/user/repo/index.yaml')

This will not work with a git+ssh address, however, it is easy to switch to
a private index:

        from buildbot_ros_cfg.distro_private import get_private_index
        get_private_index('git@github.com:user/repo.git')

Note here that we actually give the repository address, not the file. The
private indexer will actually check out the repository to /tmp and then use
a 'file://' access method to get the index and all other rosdistro files.

