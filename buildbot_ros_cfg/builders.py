from buildbot.config import BuilderConfig
from buildbot.process.factory import BuildFactory
from buildbot.process.properties import Interpolate
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.steps.transfer import FileUpload, FileDownload, DirectoryUpload
from buildbot.steps.trigger import Trigger
from buildbot.steps.master import MasterShellCommand

from buildbot.changes.filter import ChangeFilter
from buildbot.changes.gitpoller import GitPoller
from buildbot.schedulers import basic


# TODO: should probably read these from environment
DEFAULT_DISTRO = 'precise'
DEFAULT_ARCH = 'amd64'
INSTALL_LOC = '/home/buildbot/buildbot-ros'


## @brief Debbuilds are used for building sourcedebs & binaries out of gbps and uploading to an APT repository
## @param c The Buildmasterconfig
## @param job_name Name for this job (typically the metapackage name)
## @param packages List of packages to build.
## @param url URL of the BLOOM repository.
## @param distro Ubuntu distro to build for (for instance, 'precise')
## @param arch Architecture to build for (for instance, 'amd64')
## @param rosdistro ROS distro (for instance, 'groovy')
## @param version Release version to build (for instance, '0.8.1-0')
## @param machines List of machines this can build on.
def ros_debbuild(c, job_name, packages, url, distro, arch, rosdistro, version, machines, trigger_names = None):
    gbp_args = ['-uc', '-us', '--git-ignore-branch', '--git-ignore-new',
                '--git-verbose', '--git-dist='+distro, '--git-arch='+arch]
    f = BuildFactory()
    # Check out the repository master branch, since releases are tagged and not branched
    f.addStep(
        Git(
            repourl = url,
            branch = 'master',
            alwaysUseLatest = True, # this avoids broken builds when schedulers send wrong tag/rev
            mode = 'full' # clean out old versions
        )
    )
    # Need to build each package in order
    for package in packages:
        debian_pkg = 'ros-'+rosdistro+'-'+package.replace('_','-')  # debian package name (ros-groovy-foo)
        branch_name = 'debian/'+debian_pkg+'_%(prop:release_version:~'+version+')s_'+distro  # release branch from bloom
        deb_name = debian_pkg+'_%(prop:release_version:~'+version+')s'+distro
        final_name = debian_pkg+'_%(prop:release_version:~'+version+')s-%(prop:datestamp)s'+distro+'_'+arch+'.deb'
        # Check out the proper tag. Use --force to delete changes from previous deb stamping
        f.addStep(
            ShellCommand(
                haltOnFailure = True,
                name = package+'-checkout',
                command = ['git', 'checkout', Interpolate(branch_name), '--force']
            )
        )
        # Build the source deb
        f.addStep(
            ShellCommand(
                haltOnFailure = True,
                name = package+'-buildsource',
                command = ['git-buildpackage', '-S'] + gbp_args
            )
        )
        # Upload sourcedeb to master (currently we are not actually syncing these with a public repo)
        f.addStep(
            FileUpload(
                name = package+'-uploadsource',
                slavesrc = Interpolate('%(prop:workdir)s/'+deb_name+'.dsc'),
                masterdest = Interpolate('sourcedebs/'+deb_name+'.dsc')
            )
        )
        # Stamp the changelog, in a similar fashion to the ROS buildfarm
        f.addStep( SetProperty(command="date +%Y%m%d-%H%M-%z", property="datestamp", name = package+'-getstamp') )
        f.addStep(
            ShellCommand(
                haltOnFailure = True,
                name = package+'-stampdeb',
                command = ['git-dch', '-a', '--ignore-branch', '--verbose',
                           '-N', Interpolate('%(prop:release_version:~'+version+')s-%(prop:datestamp)s'+distro)]
            )
        )
        # build the binary from the git working copy
        f.addStep(
            ShellCommand(
                haltOnFailure = True,
                name = package+'-buildbinary',
                command = ['git-buildpackage', '--git-pbuilder', '--git-export=WC',
                           Interpolate('--git-export-dir=%(prop:workdir)s')] + gbp_args,
                env = {'DIST': distro}
            )
        )
        # Upload binarydeb to master
        f.addStep(
            FileUpload(
                name = package+'-uploadbinary',
                slavesrc = Interpolate('%(prop:workdir)s/'+final_name),
                masterdest = Interpolate('binarydebs/'+final_name)
            )
        )
        # Add the binarydeb using reprepro updater script on master
        f.addStep(
            MasterShellCommand(
                name = package+'includedeb',
                command = ['reprepro-include.bash', debian_pkg, Interpolate(final_name), distro, arch]
            )
        )
    # Trigger if needed
    if trigger_names != None:
        f.addStep( Trigger(schedulerNames = trigger_names, waitForFinish = False) )
    # Add to builders
    c['builders'].append(
        BuilderConfig(
            name = job_name+'_'+rosdistro+'_'+distro+'_'+arch+'_debbuild',
            slavenames = machines,
            factory = f
        )
    )
    # return name of builder created
    return job_name+'_'+rosdistro+'_'+distro+'_'+arch+'_debbuild'


## @brief Buildtest jobs are used for Continuous Integration testing of the source repo.
## @param c The Buildmasterconfig
## @param job_name Name for this job (typically the metapackage name)
## @param packages List of packages to build.
## @param url URL of the SOURCE repository.
## @param branch Branch to checkout.
## @param rosdistro ROS distro (for instance, 'groovy')
## @param machines List of machines this can build on.
def ros_buildtest(c, job_name, packages, url, branch, rosdistro, machines):

    # Change source is simply a GitPoller
    # TODO: make this configurable for svn/etc
    c['change_source'].append(
        GitPoller(
            repourl = url,
            branch = branch,
            project = job_name+'_'+rosdistro+'_buildtest'
        )
    )
    c['schedulers'].append(
        basic.SingleBranchScheduler(
            name = job_name+'_'+rosdistro+'_buildtest',
            builderNames = [job_name+'_'+rosdistro+'_buildtest',],
            change_filter = ChangeFilter(project = job_name+'_'+rosdistro+'_buildtest')
        )
    )

    # Directory which will be bind-mounted
    binddir = '/tmp/'+job_name+'_buildtest'

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
            command = ['sudo', 'cowbuilder', '--execute', INSTALL_LOC+'/scripts/buildtest.py',
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
            command = ['buildtest_check.py', 'tests',
                       Interpolate(INSTALL_LOC+'/'+job_name+'_'+rosdistro+'_buildtest/%(prop:buildnumber)s-log-'+job_name+'-buildtest-stdio')]
        )
    )
    c['builders'].append(
        BuilderConfig(
            name = job_name+'_'+rosdistro+'_buildtest',
            slavenames = machines,
            factory = f
        )
    )
    # return the name of the job created
    return job_name+'_'+rosdistro+'_buildtest'


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
