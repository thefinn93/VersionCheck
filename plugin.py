###
# Copyright (c) 2013, Finn Herzfeld
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.ircmsgs as ircmsgs
import cjdnsadmin
import requests
from datetime import datetime, timedelta
#import git
from . import pretty

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('VersionCheck')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class VersionCheck(callbacks.Plugin):
    """Checks the cjdns version of everyone who joins.
    Harasses them if they're out of date"""
    threaded = True
    def __init__(self, irc):
        self.__parent = super(VersionCheck, self)
        self.__parent.__init__(irc)
        
        github = requests.get("https://api.github.com/repos/cjdelisle/cjdns/commits").json()
        self.latest = {
            "time": datetime.strptime(github[0]['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ"),
            "sha": github[0]['sha']
            }
        self.versions = {}
        for version in github:
            self.versions[version['sha']] = datetime.strptime(version['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ")
        self.recentnotices = {}
    
    def versioncheck(self, irc, msg, args=None, nick=None):
        """[<nick>]
        
        Checks the cjdns version of <nick>, or your nick if no args are given."""
        host = None
        if nick is not None and args is not None:
            if nick in irc.state.nicksToHostmasks:
                hostmask = irc.state.nicksToHostmasks[nick]
                host = hostmask.split("@")[-1]
            else:
                irc.error("Can't find user %s" % nick)
        else:
            host = msg.host
        if host is not None:
            if nick is None:
                nick = msg.nick
            hostmask = "%s!%s@%s" % (msg.nick, msg.user, msg.host)
            sendNotice = True
            if hostmask not in self.recentnotices:
                self.recentnotices[hostmask] = datetime.now()
            else:
                if datetime.now() - self.recentnotices[hostmask] < timedelta(hours=6):
                    sendNotice = False
            if sendNotice or args is not None:
                cjdns = cjdnsadmin.connectWithAdminInfo()
                ping = cjdns.RouterModule_pingNode(host, self.registryValue('timeout'))
                if "version" in ping:
                    version = ping['version']
                    if not version in self.versions:
                        github = requests.get("https://api.github.com/repos/cjdelisle/cjdns/commits/%s" % version).json()
                        self.versions[version] = datetime.strptime(github['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ")
                    if self.versions[version] > self.latest['time']:
                        github = requests.get("https://api.github.com/repos/cjdelisle/cjdns/commits").json()
                        self.latest = {
                            "time": datetime.strptime(github[0]['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ"),
                            "sha": github[0]['sha']
                            }
                        for version in github:
                            self.versions[version['sha']] = datetime.strptime(version['commit']['author']['date'])
                    committime = self.versions[version]
                    if version != self.latest['sha']:
                        if datetime.now() - committime > timedelta(weeks=4):
                            if hostmask not in self.recentnotices:
                                self.recentnotices[hostmask] = datetime.now()
                            else:
                                if datetime.now() - self.recentnotices[hostmask] < timedelta(hours=6):
                                    sendNotice = False
                            if sendNotice:
                                self.log.info("%s is running a commit from %s" % (msg.nick, pretty.date(committime)))
                                irc.queueMsg(ircmsgs.privmsg(msg.args[0], "%s is running an old version of cjdns! Using a commit from %s, by the looks of it. You really ought to update." % (msg.nick, pretty.date(committime))))
                        elif datetime.now() - committime > timedelta(weeks=2):
                            sendNotice = True
                            if hostmask not in self.recentnotices:
                                self.recentnotices[hostmask] = datetime.now()
                            else:
                                if datetime.now() - self.recentnotices[hostmask] < timedelta(hours=6):
                                    sendNotice = False
                            if sendNotice:
                                self.log.info("%s is running a commit from %s" % (msg.nick, pretty.date(committime)))
                                irc.queueMsg(ircmsgs.notice(msg.nick, "You're running an old version of cjdns! Using a commit from %s, by the looks of it. You really ought to update." % pretty.date(committime)))
                    elif args is not None:
                        irc.reply("%s is up to date" % nick)
                        irc.reply("%s is running %s (from %s)" % (nick, version, pretty.date(committime)))
                elif "error" in ping and args is not None:
                    irc.reply("Error checking version of %s: %s" % (host, ping['error']))
    
    doJoin = versioncheck
    versioncheck = wrap(versioncheck, [additional('something')])


Class = VersionCheck


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
