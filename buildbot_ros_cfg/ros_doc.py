from buildbot.config import BuilderConfig
from buildbot.process.factory import BuildFactory
from buildbot.process.properties import Interpolate
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.steps.transfer import DirectoryUpload, FileDownload

from helpers import success

## @brief Docbuild jobs build the source documentation. This isn't the whold documentation
##        that is on the wiki, like message docs, just the source documentation part.
## @param c The Buildmasterconfig
## @param job_name Name for this job (typically the repository/metapackage name)
## @param url URL of the SOURCE repository.
## @param branch Branch to checkout.
## @param distro Ubuntu distro to build for (for instance, 'precise')
## @param arch Architecture to build for (for instance, 'amd64')
## @param rosdistro ROS distro (for instance, 'groovy')
## @param machines List of machines this can build on.
def ros_docbuild(c, job_name, url, branch, distro, arch, rosdistro, machines):

    # Directory which will be bind-mounted
    binddir = '/tmp/'+job_name+'_docbuild'

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
            workdir = binddir+'/src/'
        )
    )
    # Download testbuild.py script from master
    f.addStep(
        FileDownload(
            name = job_name+'-grab-script',
            mastersrc = 'scripts/docbuild.py',
            slavedest = Interpolate('%(prop:workdir)s/docbuild.py'),
            hideStepIf = success
        )
    )
    # Build docs in a pbuilder
    f.addStep(
        ShellCommand(
            haltOnFailure = True,
            name = job_name+'-docbuild',
            command = ['sudo', 'cowbuilder', '--execute', Interpolate('%(prop:workdir)s/docbuild.py'),
                       '--distribution', distro, '--architecture', arch,
                       '--bindmounts', binddir,
                       '--basepath', '/var/cache/pbuilder/base-'+distro+'-'+arch+'.cow',
                       '--', binddir, rosdistro],
            descriptionDone = ['built docs', ]
        )
    )
    # Upload docs to master
    f.addStep(
        DirectoryUpload(
            name = job_name+'-upload',
            slavesrc = binddir+'/docs',
            masterdest = 'docs',
            hideStepIf = success
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
