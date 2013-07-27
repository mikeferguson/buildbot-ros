from buildbot.config import BuilderConfig
from buildbot.process.factory import BuildFactory
from buildbot.process.properties import Interpolate
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand

from buildbot.changes.filter import ChangeFilter
from buildbot.changes.gitpoller import GitPoller
from buildbot.schedulers import basic

# TODO: should probably read these from environment
DEFAULT_DISTRO = 'precise'
DEFAULT_ARCH = 'amd64'
INSTALL_LOC = '/home/buildbot/buildbot-ros'

## @brief Testbuild jobs are used for Continuous Integration testing of the source repo.
## @param c The Buildmasterconfig
## @param job_name Name for this job (typically the metapackage name)
## @param packages List of packages to build.
## @param url URL of the SOURCE repository.
## @param branch Branch to checkout.
## @param rosdistro ROS distro (for instance, 'groovy')
## @param machines List of machines this can build on.
def ros_testbuild(c, job_name, packages, url, branch, rosdistro, machines):

    # Change source is simply a GitPoller
    # TODO: make this configurable for svn/etc
    c['change_source'].append(
        GitPoller(
            repourl = url,
            branch = branch,
            project = job_name+'_'+rosdistro+'_testbuild'
        )
    )
    c['schedulers'].append(
        basic.SingleBranchScheduler(
            name = job_name+'_'+rosdistro+'_testbuild',
            builderNames = [job_name+'_'+rosdistro+'_testbuild',],
            change_filter = ChangeFilter(project = job_name+'_'+rosdistro+'_testbuild')
        )
    )

    # Directory which will be bind-mounted
    binddir = '/tmp/'+job_name+'_testbuild'

    f = BuildFactory()
    # Remove any old crud in /tmp folder
    f.addStep( ShellCommand(command = ['rm', '-rf', binddir]) )
    # Check out repository (to /tmp)
    f.addStep(
        Git(
            repourl = url,
            branch = branch,
            alwaysUseLatest = True,
            mode = 'full',
            workdir = binddir+'/src/'
        )
    )
    # Make and run tests in a pbuilder
    f.addStep(
        ShellCommand(
            haltOnFailure = True,
            name = job_name+'-buildtest',
            command = ['sudo', 'cowbuilder', '--execute', INSTALL_LOC+'/scripts/testbuild.py',
                       '--distribution', DEFAULT_DISTRO, '--architecture', DEFAULT_ARCH,
                       '--bindmounts', binddir,
                       '--basepath', '/var/cache/pbuilder/base-'+DEFAULT_DISTRO+'-'+DEFAULT_ARCH+'.cow',
                       '--', binddir, rosdistro] # TODO: this script should be downloaded from master
        )
    )
    # Check that tests succeeded
    f.addStep(
        ShellCommand(
            warnOnFailure = True,
            flunkOnFailure = False,
            name = job_name+'-tests',
            command = ['testbuild_check.py', 'tests',
                       Interpolate(INSTALL_LOC+'/'+job_name+'_'+rosdistro+'_testbuild/%(prop:buildnumber)s-log-'+job_name+'-testbuild-stdio')]
        )
    )
    c['builders'].append(
        BuilderConfig(
            name = job_name+'_'+rosdistro+'_testbuild',
            slavenames = machines,
            factory = f
        )
    )
    # return the name of the job created
    return job_name+'_'+rosdistro+'_testbuild'
