from buildbot.config import BuilderConfig
from buildbot.process.factory import BuildFactory
from buildbot.process.properties import Interpolate
from buildbot.steps.shell import ShellCommand
from buildbot.steps.transfer import FileUpload, FileDownload
from buildbot.steps.trigger import Trigger
from buildbot.steps.master import MasterShellCommand

from helpers import success

## @brief Build a deb, from a source package found on launchpad
## @param c The Buildmasterconfig
## @param package Name of the package (for instance, gflags, should match the dsc file)
## @param version The version we are building (for instance -2.0-1, should match dsc file)
## @param binaries Dictionary of arch: binaries that will be created (since some might be 'arch:all')
## @param url URL of the BLOOM repository.
## @param distro Ubuntu distro to build for (for instance, 'precise')
## @param arch Architecture to build for (for instance, 'amd64')
## @param machines List of machines this can build on.
def launchpad_debbuild(c, package, version, binaries, url, distro, arch, machines, trigger_names = None):
    f = BuildFactory()
    # Grab the source package
    f.addStep(
        ShellCommand(
            haltOnFailure = True,
            name = package+'-getsourcedeb',
            command = ['dget', '--allow-unauthenticated', url]
        )
    )
    # download hooks
    f.addStep(
        FileDownload(
            name = package+'-grab-hooks',
            mastersrc = 'hooks/D05deps',
            slavedest = Interpolate('%(prop:workdir)s/hooks/D05deps'),
            hideStepIf = success,
            mode = 0777 # make this executable for the cowbuilder
        )
    )
    # Build it
    f.addStep(
        ShellCommand(
            haltOnFailure = True,
            name = package+'-build',
            command = ['sudo', 'cowbuilder',
                       '--build', package+'_'+version+'.dsc',
                       '--distribution', distro, '--architecture', arch,
                       '--basepath', '/var/cache/pbuilder/base-'+distro+'-'+arch+'.cow',
                       '--buildresult', Interpolate('%(prop:workdir)s'),
                       '--hookdir', Interpolate('%(prop:workdir)s/hooks')],
            descriptionDone = ['built binary debs', ]
        )
    )
    # Upload debs
    for deb_arch in binaries.keys():
        for deb_name in binaries[deb_arch]:
            debian_pkg = deb_name+'_'+version+'_'+deb_arch+'.deb'
            f.addStep(
                FileUpload(
                    name = deb_name+'-upload',
                    slavesrc = Interpolate('%(prop:workdir)s/'+debian_pkg),
                    masterdest = Interpolate('binarydebs/'+debian_pkg),
                    hideStepIf = success
                )
            )
            # Add the binarydeb using reprepro updater script on master
            f.addStep(
                MasterShellCommand(
                    name = deb_name+'-include',
                    command = ['reprepro-include.bash', deb_name, Interpolate(debian_pkg), distro, deb_arch],
                    descriptionDone = ['updated in apt', debian_pkg]
                )
            )
    # Trigger if needed
    if trigger_names != None:
        f.addStep( Trigger(schedulerNames = trigger_names, waitForFinish = False) )
    # Add to builders
    c['builders'].append(
        BuilderConfig(
            name = package+'_'+distro+'_'+arch+'_debbuild',
            slavenames = machines,
            factory = f
        )
    )
    # return name of builder created
    return package+'_'+distro+'_'+arch+'_debbuild'
