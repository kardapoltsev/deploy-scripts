#!/usr/bin/env python3 

# Copyright 2013 Alexey Kardapoltsev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import sys
import itertools


SCRIPT_VERSION = 1
COMPANY_NAME = "company"
MODULE_PREFIX = COMPANY_NAME
DOMAIN = COMPANY_NAME + ".int"
REPO_NAME = "repo-name"


def _add_module_prefix(m):
    if m.startswith(MODULE_PREFIX + "-"):
        return m
    else:
        return "{}-{}".format(MODULE_PREFIX, m)


def _remove_module_prefix(m):
    return m.replace(MODULE_PREFIX + "-", "")

_modules = ["bootstrap"]
_seed_module = _add_module_prefix("bootstrap")

tmodules = list(map(_add_module_prefix, _modules))
modules = _modules + tmodules

groups = {
    "all": tmodules,
    "seed": [],
    "main": list(map(_add_module_prefix, ["bootstrap"]))
}
hosts = [
    "backend00.dev.{}".format(DOMAIN)
]

environments = {
     "dev": [
        {
            "host": "backend00.dev.{}".format(DOMAIN),
            "modules": list(map(_add_module_prefix, ["bootstrap"]))
        }
     ]
}


def is_seed(server):
    return bool([m for m in server["modules"] if m in groups["seed"]])


# mappings from hostname to stage
stages = dict(itertools.chain.from_iterable(((hv["host"], en) for hv in ev) for (en, ev) in environments.items()))


def confirm(question, default="no"):
    valid = {"yes": True, "y": True, "ye": True, "sure": True,
             "no": False, "n": False, "nope": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


# from argcomplete import warn
def ModuleCompleter(prefix, **kwargs):
    #warn("called with args: {}".format(kwargs))
    used = getattr(kwargs['parsed_args'], "modules", [])
    #warn("used = {}".format(used))
    m = list(set(modules) - set(used) - set(map(_remove_module_prefix, used)))
    #warn("m = {}".format(m))
    return (v for v in m if v.startswith(prefix))


def GroupCompleter(prefix, **kwargs):
    used = getattr(kwargs['parsed_args'], "groups", [])
    m = list(set(groups.keys()) - set(used))
    return (v for v in m if v.startswith(prefix))


def _module_check(m):
    if m not in modules:
        msg = "wrong module name: {}".format(m)
        raise argparse.ArgumentTypeError(msg)
    return _add_module_prefix(m)


def _group_check(g):
    if g not in groups.keys():
        msg = "wrong group name: {}".format(g)
        raise argparse.ArgumentTypeError(msg)
    return g

actionParser = argparse.ArgumentParser(add_help=False)
actionParser.add_argument(
    "-a", "--action", dest="action", help="action for module",
    choices=["stop", "start", "restart", "status"]
)

modulesParser = argparse.ArgumentParser(add_help=False)
modulesParser.add_argument(
    "-m", "--modules", nargs="+", default=[],
    help="backend modules to be installed",
    type=_module_check
).completer = ModuleCompleter

groupsParser = argparse.ArgumentParser(add_help=False)
groupsParser.add_argument(
    "-g", "--groups", nargs="+", default=[],
    help="group of backend modules to be installed",
    type=_group_check
).completer = GroupCompleter

hostParser = argparse.ArgumentParser(add_help=False)
hostGroup = hostParser.add_mutually_exclusive_group()
hostGroup.add_argument(
    "-t", "--target", dest="target", help="target host",
    choices=hosts
)
hostGroup.add_argument(
    "-e", "--env", dest="env", default="dev", help="target environment",
    choices=list(environments.keys())
)

#vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

