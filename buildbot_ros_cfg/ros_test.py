from buildbot.config import BuilderConfig
from buildbot.changes import base
from buildbot.changes.filter import ChangeFilter
from buildbot.changes.gitpoller import GitPoller
from buildbot.plugins import util, status
from buildbot.process.factory import BuildFactory
from buildbot.process.properties import Interpolate
from buildbot.schedulers import basic
from buildbot.status import results
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand
from buildbot.steps.transfer import FileDownload

from buildbot_ros_cfg.git_pr_poller import GitPRPoller
from buildbot_ros_cfg.helpers import success


## @brief Work around for GitPoller not allowing two instances
class NamedGitPoller(GitPoller):
    def __init__(self, repourl, name, branches=None, branch=None,
                 workdir=None, pollInterval=10*60,
                 gitbin='git', usetimestamps=True,
                 category=None, project=None,
                 encoding='utf-8'):
        base.PollingChangeSource.__init__(self, name=name+'_'+repourl,
                pollInterval=pollInterval)

        if branch and branches:
            config.error("NamedGitPoller: can't specify both branch and branches")
        elif branch:
            branches = [branch]
        elif not branches:
            branches = ['master']

        self.repourl = repourl
        self.branches = branches
        self.encoding = encoding
        self.gitbin = gitbin
        self.workdir = workdir
        self.usetimestamps = usetimestamps
        self.category = category
        self.project = project
        self.changeCount = 0
        self.lastRev = {}
        self.workdir = name+'_gitpoller-work'

## @brief Testbuild jobs are used for CI testing of the source repo.
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
def ros_testbuild(c, job_name, url, branch, distro, arch, rosdistro, machines, 
                  othermirror, keys, token=None):

    # Change source is either GitPoller or GitPRPoller
    # TODO: make this configurable for svn/etc
    project_name = ''
    if token:
        project_name = '_'.join([job_name, rosdistro, 'prtestbuild'])
        c['change_source'].append(
            GitPRPoller(name=rosdistro+"_pr_poller",
                        repourl=url, # this may pose some problems
                        project=project_name,
                        token=token,
                        pollInterval=15))
        # parse repo_url git@github:author/repo.git to repoOwner, repoName
        r_owner, r_name = (url.split(':')[1])[:-4].split('/')
        c['status'].append(status.GitHubStatus(token=token,
                                               repoOwner=r_owner,
                                               repoName=r_name))
    else:
        project_name = '_'.join([job_name, rosdistro, 'testbuild'])
        c['change_source'].append(
            NamedGitPoller(
                repourl=url,
                name=rosdistro,
                branch=branch,
                project=project_name
            )
        )

    c['schedulers'].append(
        basic.SingleBranchScheduler(
            name=project_name,
            builderNames=[project_name,],
            change_filter=ChangeFilter(project=project_name)
        )
    )

    # Directory which will be bind-mounted
    binddir = '/tmp/'+project_name

    f = BuildFactory()
    # Remove any old crud in /tmp folder
    f.addStep(
        ShellCommand(
            command=['rm', '-rf', binddir],
            hideStepIf=success
        )
    )
    # Check out repository (to /tmp)
    f.addStep(
        Git(
            repourl=util.Property('repository', default=url),
            branch=util.Property('branch', default=branch),
            alwaysUseLatest=True,
            mode='full',
            workdir=binddir+'/src/'+job_name
        )
    )
    # Download testbuild.py script from master
    f.addStep(
        FileDownload(
            name=job_name+'-grab-script',
            mastersrc='scripts/testbuild.py',
            slavedest=Interpolate('%(prop:workdir)s/testbuild.py'),
            hideStepIf=success
        )
    )
    # Update the cowbuilder
    f.addStep(
        ShellCommand(
            command=['cowbuilder-update.py', distro, arch] + keys,
            hideStepIf=success
        )
    )
    # Make and run tests in a cowbuilder
    f.addStep(
        TestBuild(
            name=job_name+'-build',
            command=['sudo', 'cowbuilder', '--execute',
                     Interpolate('%(prop:workdir)s/testbuild.py'),
                     '--distribution', distro, '--architecture', arch,
                     '--bindmounts', binddir, '--basepath',
                     '/var/cache/pbuilder/base-'+distro+'-'+arch+'.cow',
                     '--override-config', '--othermirror', othermirror,
                     '--', binddir, rosdistro],
            logfiles={'tests' : binddir+'/testresults'},
            descriptionDone=['make and test', job_name]
        )
    )
    c['builders'].append(
        BuilderConfig(
            name=project_name,
            slavenames=machines,
            factory=f
        )
    )
    # return the name of the job created
    return project_name

## @brief ShellCommand w/overloaded evaluateCommand so that tests can be Warn
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
