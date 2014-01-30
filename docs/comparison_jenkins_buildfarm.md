##Comparison with ROS buildfarm
Buildbot-ROS uses mostly the same underlying tools as the ROS buildfarm. _Bloom_ is still used to
create gbp releases. _git-buildpackage_ is used to generate debians from the _Bloom_ releases,
using _cowbuilder_ to build in a chroot rather than _pbuilder_. _reprepro_ is used to update the
APT repository. Docs are generated using _rosdoc_lite_. The build is defined by a _rosdistro_
repository, and we use the _python-rosdistro_ package to parse it.

###Major differences from the ROS buildfarm:
 * Buildbot is completely configured in Python. Thus, the configuration for any build is simply a
   Python script, which I found to be more approachable than scripting Jenkins.
 * Source and binary debians for an entire repository, which can consist of several packages and a
   metapackage, are built as one job per ROS/Ubuntu distribution combination.
