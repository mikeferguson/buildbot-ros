from __future__ import print_function

from rosdistro import *
from rosdistro.dependency_walker import *
from rosdistro.release import *

from buildbot_ros_cfg.ros_deb import ros_debbuild
from buildbot_ros_cfg.ros_test import ros_testbuild
from buildbot_ros_cfg.ros_doc import ros_docbuild

## @brief The Oracle tells you all you need to build stuff
class RosDistroOracle:
    # TODO: use release file blacklist and drop those packages.

    ## @brief Constructor
    ## @param index A rosdistro.Index instance
    ## @param distros A list of ROS distribution names
    def __init__(self, index, distro_names):
        self.index = index
        self.distro_names = distro_names
        self.distributions = {}

        self.build_order = {}
        self.build_files = {}

        for dist_name in distro_names:
            self.distributions[dist_name] = get_cached_distribution(index, dist_name, allow_lazy_load = True)
            dist = self.distributions[dist_name]

            self.build_order[dist_name] = dict()

            pkg_depends = dict()
            packages = dist.release_packages.keys()
            walker = DependencyWalker(dist)

            # compute dependency of each package
            for pkg in packages:
                if dist.repositories[dist.release_packages[pkg].repository_name].release_repository.version == None:
                    continue
                pkg_depends[pkg] = list()
                depends = walker.get_depends(pkg, 'buildtool')
                depends |= walker.get_depends(pkg, 'build')
                depends |= walker.get_depends(pkg, 'run')
                for dp in depends:
                    if dp in packages:
                        pkg_depends[pkg].append(dp)

            # this gives order for packages within a single repo of the debbuild
            for repo in dist.repositories.keys():
                if dist.repositories[repo].release_repository == None:
                    continue
                if dist.repositories[repo].release_repository.version == None:
                    continue
                order = list()
                for pkg in dist.repositories[repo].release_repository.package_names:
                    self._insert(pkg, pkg_depends[pkg], order)
                self.build_order[dist_name][repo] = order

            # this gives the order of the debbuilds
            order = list()
            for repo in dist.repositories.keys():
                if dist.repositories[repo].release_repository == None:
                    continue
                if dist.repositories[repo].release_repository.version == None:
                    continue

                depends = list()
                for pkg in dist.repositories[repo].release_repository.package_names:
                    for dep in pkg_depends[pkg]:
                        rd = dist.release_packages[dep].repository_name
                        if rd not in depends:
                            depends.append(rd)
                self._insert(repo, depends, order)

            self.build_order[dist_name]['deb_jobs'] = order

            self.build_files[dist_name] = dict()
            # TODO: this is a bit hacky, come up with a better way to get 'correct' build
            self.build_files[dist_name]['release'] = get_release_build_files(self.index, dist_name)[0]
            self.build_files[dist_name]['source'] = get_source_build_files(self.index, dist_name)[0]
            self.build_files[dist_name]['doc'] = get_doc_build_files(self.index, dist_name)[0]

            # build a list of doc jobs, all doc jobs must be released,
            # but not all released things should need to be documented
            self.build_order[dist_name]['doc_jobs'] = list()
            doc = get_doc_file(self.index, dist_name)
            for repo in order:
                if repo in doc.repositories.keys():
                    self.build_order[dist_name]['doc_jobs'].append(repo)

    ## @brief Get the order to build debian packages within a single repository
    def getPackageOrder(self, repo_name, dist_name):
        return self.build_order[dist_name][repo_name]

    ## @brief Get the order for debian jobs
    def getDebJobOrder(self, dist_name):
        return self.build_order[dist_name]['deb_jobs']

    ## @brief Get the order for documentation jobs
    def getDocJobOrder(self, dist_name):
        return self.build_order[dist_name]['doc_jobs']

    ## @brief Get the job to trigger after this one
    def getDebTrigger(self, repo_name, dist_name):
        i = self.build_order[dist_name]['deb_jobs'].index(repo_name)
        try:
            return [self.build_order[dist_name]['deb_jobs'][i+1], ]
        except:
            return None

    ## @brief Get the job to trigger after this one
    def getDocTrigger(self, repo_name, dist_name):
        i = self.build_order[dist_name]['doc_jobs'].index(repo_name)
        try:
            return [self.build_order[dist_name]['doc_jobs'][i+1], ]
        except:
            return None

    ## @brief Get the job to start nightly build with
    def getNightlyDebStart(self, dist_name):
        return self.build_order[dist_name]['deb_jobs'][0]

    ## @brief Get the job to start nightly build with
    def getNightlyDocStart(self, dist_name):
        return self.build_order[dist_name]['doc_jobs'][0]

    ## @brief Get the rosdistro.Index
    def getIndex(self):
        return self.index

    ## @brief Get the list of ROS distribution names
    def getDistroNames(self):
        return self.distros

    ## @brief Get the mirrors for release jobs
    ## @param build The type of the build, 'release', 'source', or 'doc'
    ## @param rosdistro The rosdistro name, 'groovy'
    ## @param distro The Ubuntu distro, 'precise'
    def getOtherMirror(self, build, rosdistro, distro):
        build_file = self.build_files[rosdistro][build]
        if "_config" not in build_file._targets:
            print("No _config in %s build file -- this is probably not right." % build)
            return ""
        if "apt_mirrors" not in build_file.targets["_config"]:
            print("No apt_mirrors in %s _config -- this is probably not right." % build)
            return ""
        #TODO: source, doc should be updated to allow this:
        #mirrors = build_file.get_target_configuration()['apt_mirrors']
        mirrors = build_file._targets['_config']['apt_mirrors']
        return '\n'.join(['deb '+mirror.replace('DISTRO',distro)+' |' for mirror in mirrors])

    ## @brief Get the mirrors that need to be bind mounted
    ## @param build The type of the build, 'release', 'source', or 'doc'
    ## @param rosdistro The rosdistro name, 'groovy'
    ## @param distro The Ubuntu distro, 'precise'
    def getBindMirrors(self, build, rosdistro, distro):
        build_file = self.build_files[rosdistro][build]
        if "_config" not in build_file._targets:
            print("No _config in %s build file -- this is probably not right." % build)
            return ""
        if "apt_mirrors" not in build_file.targets["_config"]:
            print("No apt_mirrors in %s _config -- this is probably not right." % build)
            return ""
        #TODO: source, doc should be updated to allow this:
        #mirrors = build_file.get_target_configuration()['apt_mirrors']
        mirrors = build_file._targets['_config']['apt_mirrors']
        return ' '.join([m[7:m.find(' ')] for m in mirrors if m.startswith('file://')])

    ## @brief Get the keys for release jobs
    ## @param build The type of the build, 'release', 'source', or 'doc'
    def getKeys(self, build, rosdistro):
        build_file = self.build_files[rosdistro][build]
        if "_config" not in build_file._targets:
            print("No _config in %s build file -- this is probably not right." % build)
            return []
        if "apt_keys" not in build_file.targets["_config"]:
            print("WARNING: No apt_keys in %s _config." % build)
            return []
        #TODO: source, doc should be updated to allow this:
        #return build_file.get_target_configuration()['apt_keys']
        return build_file._targets['_config']['apt_keys']

    def _insert(self, name, depends, order):
        for i in range(len(order)):
            if order[len(order)-i-1] in depends:
                order.insert(len(order)-i, name)
                return
        order.insert(0, name)

## @brief Create debbuilders from release file
## @param c The Buildmasterconfig
## @param oracle The rosdistro oracle
## @param distro The distro to configure for ('groovy', 'hydro', etc)
## @param builders list of builders that this job can run on
## @returns A list of debbuilder names created
def debbuilders_from_rosdistro(c, oracle, distro, builders):
    rel = get_release_file(oracle.getIndex(), distro)
    build_files = get_release_build_files(oracle.getIndex(), distro)
    jobs = list()

    for name in rel.repositories.keys():
        if rel.repositories[name].version == None:
            print('Skipping %s, since it has no version' % name)
            continue
        if rel.repositories[name].type != 'git':
            print('Cannot configure ros_debbuild for %s, as it is not a git repository' % name)
            continue
        for build_file in build_files:
            for os in build_file.get_target_os_names():
                for code_name in build_file.get_target_os_code_names(os):
                    for arch in build_file.get_target_arches(os, code_name):
                        print('Configuring ros_debbuild job for: %s_%s_%s' % (name, code_name, arch))
                        jobs.append(ros_debbuild(c,
                                                 name,
                                                 oracle.getPackageOrder(name, distro),
                                                 rel.repositories[name].url,
                                                 code_name,
                                                 arch,
                                                 distro,
                                                 rel.repositories[name].version,  # release_version
                                                 builders,
                                                 oracle.getOtherMirror('release', distro, code_name),
                                                 oracle.getKeys('release', distro),
                                                 oracle.getDebTrigger(name, distro)))
    return jobs

## @brief Create testbuilders from source file
## @param c The Buildmasterconfig
## @param oracle The rosdistro oracle
## @param distro The distro to configure for ('groovy', 'hydro', etc)
## @param builders list of builders that this job can run on
## @returns A list of debbuilder names created
def testbuilders_from_rosdistro(c, oracle, distro, builders):
    source = get_source_file(oracle.getIndex(), distro)
    build_files = get_source_build_files(oracle.getIndex(), distro)
    jobs = list()

    for name in source.repositories.keys():
        if source.repositories[name].type != 'git':
            print('Cannot configure ros_debbuild for %s, as it is not a git repository' % name)
            continue
        for build_file in build_files:
            for os in build_file.get_target_os_names():
                for code_name in build_file.get_target_os_code_names(os):
                    for arch in build_file.get_target_arches(os, code_name):
                        print('Configuring ros_testbuild job for: %s_%s_%s' % (name, code_name, arch))
                        jobs.append(ros_testbuild(c,
                                                  name,
                                                  source.repositories[name].url,
                                                  source.repositories[name].version,  # branch
                                                  code_name,
                                                  arch,
                                                  distro,
                                                  builders,
                                                  oracle.getOtherMirror('source', distro, code_name),
                                                  oracle.getKeys('source', distro),
                                                  ))
    return jobs

## @brief Create docbuilders from doc file
## @param c The Buildmasterconfig
## @param oracle The rosdistro oracle
## @param distro The distro to configure for ('groovy', 'hydro', etc)
## @param builders list of builders that this job can run on
## @returns A list of debbuilder names created
def docbuilders_from_rosdistro(c, oracle, distro, builders):
    doc = get_doc_file(oracle.getIndex(), distro)
    build_files = get_doc_build_files(oracle.getIndex(), distro)
    jobs = list()

    for name in doc.repositories.keys():
        if doc.repositories[name].type != 'git':
            print('Cannot configure ros_debbuild for %s, as it is not a git repository' % name)
            continue
        for build_file in build_files:
            for os in build_file.get_target_os_names():
                for code_name in build_file.get_target_os_code_names(os):
                    for arch in build_file.get_target_arches(os, code_name):
                        print('Configuring ros_docbuild job for: %s_%s_%s' % (name, code_name, arch))
                        jobs.append(ros_docbuild(c,
                                                 name,
                                                 doc.repositories[name].url,
                                                 doc.repositories[name].version,  # branch
                                                 code_name,
                                                 arch,
                                                 distro,
                                                 builders,
                                                 oracle.getOtherMirror('doc', distro, code_name),
                                                 oracle.getKeys('doc', distro),
                                                 oracle.getDocTrigger(name, distro)))
    return jobs
