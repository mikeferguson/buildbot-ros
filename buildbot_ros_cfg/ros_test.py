from buildbot.config import BuilderConfig
from buildbot.process.factory import BuildFactory
from buildbot.process.properties import Interpolate
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand
from buildbot.steps.transfer import FileDownload

from buildbot.changes.filter import ChangeFilter
from buildbot.changes.gitpoller import GitPoller
from buildbot.schedulers import basic


## @brief Testbuild jobs are used for Continuous Integration testing of the source repo.
## @param c The Buildmasterconfig
## @param job_name Name for this job (typically the metapackage name)
## @param packages List of packages to build.
## @param url URL of the SOURCE repository.
## @param branch Branch to checkout.
## @param distro Ubuntu distro to build for (for instance, 'precise')
## @param arch Architecture to build for (for instance, 'amd64')
## @param rosdistro ROS distro (for instance, 'groovy')
## @param machines List of machines this can build on.
def ros_testbuild(c, job_name, packages, url, branch, distro, arch, rosdistro, machines):

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
    # Download testbuild.py script from master
    f.addStep(
        FileDownload(
            name = job_name+'-grab-script',
            mastersrc = 'scripts/testbuild.py',
            slavedest = Interpolate('%(prop:workdir)s/testbuild.py'),
        )
    )
    # Make and run tests in a pbuilder
    f.addStep(
        ShellCommand(
            name = job_name+'-build',
            command = ['sudo', 'cowbuilder', '--execute', Interpolate('%(prop:workdir)s/testbuild.py'),
                       '--distribution', distro, '--architecture', arch,
                       '--bindmounts', binddir,
                       '--basepath', '/var/cache/pbuilder/base-'+distro+'-'+arch+'.cow',
                       '--', binddir, rosdistro],
            logfiles = {'tests' : binddir+'/testresults' }
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
