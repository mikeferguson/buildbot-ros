#!/usr/bin/env python

from __future__ import print_function

from rosdistro import *
from rosdistro import _get_dist_file_data
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

        self.releases = {}
        for dist_name in distro_names:
            rel_file_data = _get_dist_file_data(index, dist_name, 'release')
            try:
                cache = get_release_cache(index, dist_name)
            except Exception:
                # create empty cache instance
                cache = ReleaseCache(dist_name, rel_file_data=rel_file_data)
            # update
            cache.update_distribution(rel_file_data)
            self.releases[dist_name] = get_cached_release(index, dist_name, cache = cache, allow_lazy_load = True)

        self.build_order = {}
        for dist_name in distro_names:
            self.build_order[dist_name] = dict()

            pkg_depends = dict()
            release = self.releases[dist_name]
            packages = release.packages.keys()
            walker = DependencyWalker(release)

            # compute dependency of each package
            for pkg in packages:
                if release.repositories[release.packages[pkg].repository_name].version == None:
                    continue
                pkg_depends[pkg] = list()
                depends = walker.get_depends(pkg, 'build')
                for dp in depends:
                    if dp in packages:
                        pkg_depends[pkg].append(dp)

            # this gives order for packages within a single repo of the debbuild
            for repo in release.repositories.keys():
                if release.repositories[repo].version == None:
                    continue
                order = list()
                for pkg in release.repositories[repo].package_names:
                    self._insert(pkg, pkg_depends[pkg], order)
                self.build_order[dist_name][repo] = order

            # this gives the order of the debbuilds
            order = list()
            for repo in release.repositories.keys():
                if release.repositories[repo].version == None:
                    continue

                depends = list()
                for pkg in release.repositories[repo].package_names:
                    for dep in pkg_depends[pkg]:
                        rd = release.packages[dep].repository_name
                        if rd not in depends:
                            depends.append(rd)
                self._insert(repo, depends, order)

            self.build_order[dist_name]['jobs'] = order

    ## @brief Get the order to build debian packages within a single repository
    def getPackageOrder(self, repo_name, dist_name):
        return self.build_order[dist_name][repo_name]

    ## @brief Get the order for debian jobs
    def getJobOrder(self, dist_name):
        return self.build_order[dist_name]['jobs']

    ## @brief Get the job to trigger after this one
    def getTrigger(self, repo_name, dist_name):
        i = self.build_order[dist_name]['jobs'].index(repo_name)
        try:
            return self.build_order[dist_name]['jobs'][i+1]
        except:
            return None

    ## @brief Get the job to start nightly build with
    def getNightlyStart(self, dist_name):
        return self.build_order[dist_name]['jobs'][0]

    ## @brief Get the rosdistro.Index
    def getIndex(self):
        return self.index

    ## @brief Get the list of ROS distribution names
    def getDistroNames(self):
        return self.distros

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
                                                 oracle.getTrigger(name, distro)))
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
                                                  builders
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
                                                 oracle.getTrigger(name, distro)))
    return jobs
