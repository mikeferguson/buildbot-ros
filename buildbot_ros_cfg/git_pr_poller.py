#!/usr/bin/env python

# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

# This is the gitpoller adapted for use with pull requests.
# Extraneous code has been removed (e.g. commit-related methods).
# A modification has been added using name to allow for multiple instances.

import itertools
import os
import requests
import urllib
from datetime import datetime

from twisted.internet import defer
from twisted.internet import utils
from twisted.python import log

from buildbot import config
from buildbot.changes import base
from buildbot.util.state import StateMixin


class GitPRPoller(base.PollingChangeSource, StateMixin):

    """This source will poll a remote git repo for pull requests
    and submit changes for the PR's branches to the change master."""

    compare_attrs = ["repourl", "branches", "workdir",
                     "pollInterval", "gitbin", "usetimestamps",
                     "category", "project", "pollAtLaunch"]

    def __init__(self, repourl, name, branches=None, branch=None,
                 workdir=None, pollInterval=10 * 60,
                 gitbin='git', usetimestamps=True,
                 category=None, project=None,
                 pollinterval=-2, fetch_refspec=None,
                 encoding='utf-8', pollAtLaunch=False, token=''):

        # for backward compatibility; the parameter used to be spelled with 'i'
        if pollinterval != -2:
            pollInterval = pollinterval

        base.PollingChangeSource.__init__(self, name=name + "_" + repourl,
                                          pollInterval=pollInterval,
                                          pollAtLaunch=pollAtLaunch)

        if project is None:
            project = ''

        self.repourl = repourl
        self.branches = branches
        self.encoding = encoding
        self.gitbin = gitbin
        self.workdir = name+'-work'
        self.usetimestamps = usetimestamps
        self.category = category
        self.project = project
        self.changeCount = 0
        self.lastRev = {}
        self.lastRevs = {}

        self.pull_requests = []

        self.auth_header = {'Authorization': 'token ' + token}

        if fetch_refspec is not None:
            config.error("GitPoller: fetch_refspec is no longer supported. "
                         "Instead, only the given branches are downloaded.")

    def startService(self):
        # make our workdir absolute, relative to the master's basedir
        if not os.path.isabs(self.workdir):
            self.workdir = os.path.join(self.master.basedir, self.workdir)
            log.msg("git_pr_poller: using workdir '%s'" % self.workdir)

        d = self.getState('lastRevs', {})

        def setLastRevs(lastRevs):
            self.lastRevs = lastRevs
        d.addCallback(setLastRevs)

        d.addCallback(lambda _:
                      base.PollingChangeSource.startService(self))
        d.addErrback(log.err, 'while initializing GitPRPoller repository')

        return d

    def describe(self):
        status = ('GitPRPoller watching the remote git repository ' +
               self.repourl)

        if not self.master:
            status += " [STOPPED - check log]"

        return status

    # like _getBranches but for pull requests
    def _get_pull_requests(self):
        # get owner+repo from repo url (e.g. 'git@github.com:owner/reponame.git')
        owner_repo = (self.repourl.split(":")[1]).split(".")[0]
        url = "https://api.github.com/repos/" + owner_repo + "/pulls"
        r = requests.get(url, headers=self.auth_header)
        
        # Store xtag for next use to prevent spamming GitHub
        self.auth_header.update({'If-None-Match': r.headers['etag']})
        log.msg("etag: %s" % r.headers['etag'])
        log.msg(r.status_code)
        log.msg(r.request.headers)

        # Return nothing if there are no pull_requests
        if r.status_code == 304:
            log.msg("No changes found for %s" % owner_repo)
            return []

        prs = r.json()

        pr_info = []
        # process PRs for branches
        for pr in prs:
            infodict = {'rev': pr['head']['sha'],
                        'branch': pr['head']['ref'],
                        'repo_name': pr['head']['repo']['name'],
                        'owner': pr['head']['repo']['owner']['login'],
                        'repo_url':  pr['head']['repo']['ssh_url'],
                        'timestamp': pr['updated_at']}
            pr_info.append(infodict)
            log.msg("got info for rev %s at %s/%s/%s" % (infodict['rev'],
                                                         infodict['owner'],
                                                         infodict['repo_name'],
                                                         infodict['branch']))
        return pr_info

    # main polling method
    @defer.inlineCallbacks
    def poll(self):
        # make an empty repository
        yield self._dovccmd('init', ['--bare', self.workdir])

        # grab pull request information
        pull_requests = yield self._get_pull_requests()

        revs = {}

        for pull_request in pull_requests:
            try:
                yield self._process_changes(pull_request)
                revkey = (pull_request['owner'] + "/" + pull_request['repo_name']
                         + "/" + pull_request['branch'])
                revs.update({revkey: pull_request['rev']})
            except Exception:
                log.err(_why="trying to poll branch %s of %s"
                        % (pull_request['branch'], pull_request['repo_url']) )

        # update revs with {'owner/repo/branch': 'rev'}
        self.lastRevs.update(revs)
        yield self.setState('lastRevs', self.lastRevs)

    @defer.inlineCallbacks
    def _process_changes(self, pull_request):
        """
        Read changes since last pull request update.

        - Read list of pull requests
        - Extract details from each PR
        - Add changes to database
        """
        newRev = pull_request['rev']
        # TODO: Comb commit history instead of just processing latest?

        # check if rev is new
        
        if newRev in self.lastRevs.values():
            # original code had a pass instead
            log.msg("%s found in lastRevs, so skipping %s/%s/%s" 
                % (pull_request['rev'],
                   pull_request['owner'],
                   pull_request['repo_name'],
                   pull_request['branch']))
            return

        # convert timestamp (2000-12-31T23:59:59Z) to datetime here
        stamp_date, stamp_time = pull_request['timestamp'].split('T')
        year, month, day = [int(i) for i in stamp_date.split('-')]
        hour, minute, second = [int(i) for i in stamp_time[:-1].split(':')] 
        new_stamp = datetime(year, month, day, hour, minute, second)

        # getting here means the pull request hasn't been built yet
        # needs all values put in or SQLAlchemy throws a fit
        yield self.master.addChange(
            author=pull_request['owner'],
            comments=pull_request['repo_name'],
            revision=newRev,
            branch=pull_request['branch'],
            when_timestamp=new_stamp,
            category=self.category,
            project=self.project,
            repository=pull_request['repo_url'],
            src='git')

    def _dovccmd(self, command, args, path=None):
        d = utils.getProcessOutputAndValue(self.gitbin,
                                           [command] + args, path=path, env=os.environ)

        def _convert_nonzero_to_failure(res,
                                        command,
                                        args,
                                        path):
            "utility to handle the result of getProcessOutputAndValue"
            (stdout, stderr, code) = res
            if code != 0:
                raise EnvironmentError('command %s %s in %s on repourl %s failed with exit code %d: %s'
                                       % (command, args, path, self.repourl, code, stderr))
            return stdout.strip()
        d.addCallback(_convert_nonzero_to_failure,
                      command,
                      args,
                      path)
        return d
