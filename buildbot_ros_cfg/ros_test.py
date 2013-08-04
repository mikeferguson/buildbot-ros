from buildbot.config import BuilderConfig
from buildbot.process.factory import BuildFactory
from buildbot.process.properties import Interpolate
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand
from buildbot.steps.transfer import FileDownload

from buildbot.changes.filter import ChangeFilter
from buildbot.changes.gitpoller import GitPoller
from buildbot.schedulers import basic

from buildbot.status import results
from helpers import success

## @brief Testbuild jobs are used for Continuous Integration testing of the source repo.
## @param c The Buildmasterconfig
## @param job_name Name for this job (typically the metapackage name)
## @param url URL of the SOURCE repository.
## @param branch Branch to checkout.
## @param distro Ubuntu distro to build for (for instance, 'precise')
## @param arch Architecture to build for (for instance, 'amd64')
## @param rosdistro ROS distro (for instance, 'groovy')
## @param machines List of machines this can build on.
## @param othermirror Cowbuilder othermirror parameter
## @param keys List of keys that cowbuilder will need
def ros_testbuild(c, job_name, url, branch, distro, arch, rosdistro, machines, othermirror, keys):

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
    f.addStep(
        ShellCommand(
            command = ['rm', '-rf', binddir],
            hideStepIf = success
        )
    )
    # Check out repository (to /tmp)
    f.addStep(
        Git(
            repourl = url,
            branch = branch,
            alwaysUseLatest = True,
            mode = 'full',
            workdir = binddir+'/src/'+job_name
        )
    )
    # Download testbuild.py script from master
    f.addStep(
        FileDownload(
            name = job_name+'-grab-script',
            mastersrc = 'scripts/testbuild.py',
            slavedest = Interpolate('%(prop:workdir)s/testbuild.py'),
            hideStepIf = success
        )
    )
    # Update the cowbuilder
    f.addStep(
        ShellCommand(
            command = ['cowbuilder-update.py', distro, arch] + keys,
            hideStepIf = success
        )
    )
    # Make and run tests in a cowbuilder
    f.addStep(
        TestBuild(
            name = job_name+'-build',
            command = ['sudo', 'cowbuilder', '--execute', Interpolate('%(prop:workdir)s/testbuild.py'),
                       '--distribution', distro, '--architecture', arch,
                       '--bindmounts', binddir,
                       '--basepath', '/var/cache/pbuilder/base-'+distro+'-'+arch+'.cow',
                       '--override-config', '--othermirror', othermirror,
                       '--', binddir, rosdistro],
            logfiles = {'tests' : binddir+'/testresults' },
            descriptionDone = ['make and test', job_name]
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

## @brief Shell command with overwritten evaluateCommand so that tests can be Warn
class TestBuild(ShellCommand):
    warnOnWarnings = True

    def evaluateCommand(self, cmd):
        if cmd.didFail():
            # build failed
            return results.FAILURE

        l = self.getLog('tests').readlines()
        if len(l) >= 1:
            if l[0].find('Passed') > -1:
                return results.SUCCESS
            else:
                # some tests failed
                return results.WARNINGS
