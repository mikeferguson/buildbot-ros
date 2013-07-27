from buildbot.config import BuilderConfig
from buildbot.process.factory import BuildFactory
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.steps.transfer import DirectoryUpload

# TODO: should probably read these from environment
DEFAULT_DISTRO = 'precise'
DEFAULT_ARCH = 'amd64'
INSTALL_LOC = '/home/buildbot/buildbot-ros'

## @brief Docbuild jobs build the source documentation. This isn't the whold documentation
##        that is on the wiki, like message docs, just the source documentation part.
## @param c The Buildmasterconfig
## @param job_name Name for this job (typically the metapackage name)
## @param packages List of packages to build.
## @param url URL of the SOURCE repository.
## @param branch Branch to checkout.
## @param rosdistro ROS distro (for instance, 'groovy')
## @param machines List of machines this can build on.
def ros_docbuild(c, job_name, packages, url, branch, rosdistro, machines):

    # Directory which will be bind-mounted
    binddir = '/tmp/'+job_name+'_docbuild'

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
    # Build docs in a pbuilder
    for package in packages:
        f.addStep(
            ShellCommand(
                haltOnFailure = True,
                name = package+'-docbuild',
                command = ['sudo', 'cowbuilder', '--execute', INSTALL_LOC+'/scripts/docbuild.py',
                           '--distribution', DEFAULT_DISTRO, '--architecture', DEFAULT_ARCH,
                           '--bindmounts', binddir,
                           '--basepath', '/var/cache/pbuilder/base-'+DEFAULT_DISTRO+'-'+DEFAULT_ARCH+'.cow',
                           '--', binddir, rosdistro, package] # TODO: this script should be downloaded from master
            )
        )
        # Upload docs to master
        f.addStep(
            DirectoryUpload(
                name = package+'-upload',
                slavesrc = binddir+'/doc/html',
                masterdest = 'docs/'+package
            )
        )
    c['builders'].append(
        BuilderConfig(
            name = job_name+'_'+rosdistro+'_docbuild',
            slavenames = machines,
            factory = f
        )
    )
    # return the name of the job created
    return job_name+'_'+rosdistro+'_docbuild'
