# #
# Copyright 2009-2012 Ghent University
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
# #
"""
EasyBuild logger and log utilities, including our own EasybuildError class.
"""

import os
from copy import copy
from socket import gethostname
from vsc import fancylogger

from easybuild.tools.version import VERBOSE_VERSION as FRAMEWORK_VERSION
try:
    from easybuild.easyblocks import VERBOSE_VERSION as EASYBLOCKS_VERSION
except:
    EASYBLOCKS_VERSION = '0.0.UNKNOWN.EASYBLOCKS'  # make sure it is smaller then anything

# EasyBuild message prefix
EB_MSG_PREFIX = "=="


class EasyBuildError(Exception):
    """
    EasyBuildError is thrown when EasyBuild runs into something horribly wrong.
    """
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg
    def __str__(self):
        return repr(self.msg)


class EasyBuildLog(fancylogger.FancyLogger):
    """
    The EasyBuild logger, with its own error and exception functions.
    """

    # self.raiseError can be set to False disable raising the exception which is
    # necessary because logging.Logger.exception calls self.error
    raiseError = True

    def caller_info(self):
        (filepath, line, function_name) = self.findCaller()
        filepath_dirs = filepath.split(os.path.sep)

        for dirName in copy(filepath_dirs):
            if dirName != "easybuild":
                filepath_dirs.remove(dirName)
            else:
                break
        return "(at %s:%s in %s)" % (os.path.sep.join(filepath_dirs), line, function_name)

    def error(self, msg, *args, **kwargs):
        newMsg = "EasyBuild crashed with an error %s: %s" % (self.caller_info(), msg)
        fancylogger.FancyLogger.error(self, newMsg, *args, **kwargs)
        if self.raiseError:
            raise EasyBuildError(newMsg)

    def exception(self, msg, *args):
        # # don't raise the exception from within error
        newMsg = "EasyBuild encountered an exception %s: %s" % (self.caller_info(), msg)

        self.raiseError = False
        fancylogger.FancyLogger.exception(self, newMsg, *args)
        self.raiseError = True

        raise EasyBuildError(newMsg)


# set format for logger
LOGGING_FORMAT = EB_MSG_PREFIX + ' %(asctime)s %(name)s %(levelname)s %(message)s'
fancylogger.setLogFormat(LOGGING_FORMAT)

# set the default LoggerClass to EasyBuildLog
fancylogger.logging.setLoggerClass(EasyBuildLog)

# you can't easily set another LoggerClass before fancylogger calls getLogger on import
_init_fancylog = fancylogger.getLogger(fname=False)
del _init_fancylog.manager.loggerDict[_init_fancylog.name]

# EasyBuildLog
_init_easybuildlog = fancylogger.getLogger(fname=False)


def get_log(name=None):
    """
    Generate logger object
    """
    # fname is always get_log, useless
    log = fancylogger.getLogger(name, fname=False)
    log.info("Logger started for %s." % name)
    return log


def this_is_easybuild():
    """Standard starting message"""
    top_version = max(FRAMEWORK_VERSION, EASYBLOCKS_VERSION)
    msg = "This is EasyBuild %s (framework: %s, easyblocks: %s) on host %s." \
         % (top_version, FRAMEWORK_VERSION, EASYBLOCKS_VERSION, gethostname())

    return msg


def print_msg(msg, log=None, silent=False):
    """
    Print a message to stdout.
    """
    if log:
        log.info(msg)
    if not silent:
        print "%s %s" % (EB_MSG_PREFIX, msg)

