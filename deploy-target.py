#!/usr/bin/env python3 
# PYTHON_ARGCOMPLETE_OK

# Copyright 2013 Alexey Kardapoltsev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import time
from deployutils import *


def install(args):
    #print("installing {}".format(args.modules))
    cmd = ["apt-get", "install",  "-y", "--force-yes"]
    cmd.extend(args.modules)
    subprocess.call(cmd)


def update(args):
    #print("running apt-get update")
    if args.full:
        subprocess.call(["apt-get", "update"])
    else:
        source = 'Dir::Etc::sourcelist=/etc/apt/sources.list.d/.list'.format(COMPANY_NAME)
        subprocess.call(["apt-get", "update", '-o', souce, '-o', 'Dir::Etc::sourceparts=-', '-o', 'APT::Get::List-Cleanup="0"'])
    #subprocess.call(["apt-get", "update"])


def restart(args):
    print("{}ing {}".format(args.action, args.modules))
    for m in args.modules:
        subprocess.call(["sudo", "service", m, args.action])
        if args.action == "start" or args.action == "restart":
            time.sleep(3)

def kill_backend(args):
    #kill -9
    print("killing backend")
    subprocess.call(["sudo", "pkill", "-f", COMPANY_NAME])      
    time.sleep(1)
    subprocess.call(["sudo", "pkill", "-9", "-f", COMPANY_NAME])      


def print_version(args):
    print(SCRIPT_VERSION)




topParser = argparse.ArgumentParser()
subParsers = topParser.add_subparsers(title = "Command categories")

installParser = subParsers.add_parser("install", description = "installing backend modules to host", parents=[modulesParser])
installParser.set_defaults(func = install)

updateParser = subParsers.add_parser("update", description = "run apt-get update")
updateParser.add_argument("--full", dest="full", action="store_true", default=False, help = "run apt-get update from all sources before installing")
updateParser.set_defaults(func = update)

killParser = subParsers.add_parser("killbackend", description = "kill all backend modules")
killParser.set_defaults(func = kill_backend)

restartParser = subParsers.add_parser("restart", description = "start, stop backend modules", parents = [modulesParser, actionParser])
restartParser.set_defaults(func = restart)

versionParser = subParsers.add_parser("version", description = "print script version")
versionParser.set_defaults(func = print_version)


try:
    import argcomplete
    argcomplete.autocomplete(topParser)
except ImportError:
    pass

args = topParser.parse_args()

args.func(args)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

