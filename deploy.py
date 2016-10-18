#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

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

import subprocess
from deployutils import *
import copy
import time
import re
import sys

verbose = False
remoteExec = False
remoteHost = None
log_file = "/tmp/{}-deploy.log".format(COMPANY_NAME)
log = None


def shell(args):
    _call(args.cmd.split())


def copy_scripts(args):
    _call(["scp", "deployutils.py", "deploy-target.py", "{}:".format(args.target)])


def publish(args):
    modules = _extract_modules(args)
    stage = args.env
    if args.target:
        stage = stages[args.target]

    _log("will publish {} modules to stage {}".format(modules, stage))
    if args.clean:
        _clean()
    for m in modules:
        _publish(m, stage)

    if not args.no_docs:
      _publish_docs(stage)


def publish_docs(args):
    stage = args.env
    if args.target:
        stage = stages[args.target]

    _log("will publish docs to stage {}".format(stage))

    if args.clean:
        _clean()

    _call(["sbt", "compile"])

    _publish_docs(stage)


def install(args):
    modules = _extract_modules(args)
    _log("installing {}".format(modules))
    if args.env == "prod":
        if not confirm("Are u really wanna install to prod?"):
            _log("Good buy!")
            sys.exit(0)

    if args.target:
        if args.update:
            _update_target(args.target, args.full_update)
        _log("will install {} to {}".format(modules, args.target))
        _install(args.target, modules)
    else:
        env = environments[args.env]
        for server in env:

            seeds = []
            if is_seed(server):
                seeds = list(groups["seed"])

            t_modules = set.intersection(modules, server["modules"] + seeds)
            if t_modules:
                if args.update:
                    _update_target(server["host"], args.full_update)
                _log("will install {} to {}".format(t_modules, server["host"]))
                _install(server["host"], t_modules)


def chick(args):
    publish(copy.deepcopy(args))
    args.update = True
    install(args)


def restart_cluster(args):

    env = environments[args.env]

    # stop non seed modules
    for server in env:
        _check_version(server["host"])
        modules = [m for m in server["modules"] if not m in groups["seed"]]
        if modules:
            _log("will stop {} at {}".format(" ".join(modules), server["host"]))
            _call(["ssh", "{}".format(server["host"]), "sudo ~/deploy-target.py restart -a stop -m {}".format(" ".join(modules))])

    # stop seed modules
    for server in env:
        _check_version(server["host"])
        modules = [m for m in server["modules"] if m in groups["seed"]]
        if modules:
            _log("will stop {} at {}".format(" ".join(modules), server["host"]))
            _call(["ssh", "{}".format(server["host"]), "sudo ~/deploy-target.py restart -a stop -m {}".format(" ".join(modules))])

    # start seed
    for server in env:
        if is_seed(server):
            _log("starting seed on {}".format(server["host"]))
            for s in groups["seed"]:
                _call(["ssh", "{}".format(server["host"]), "sudo ~/deploy-target.py restart -a start -m {}".format(s)])

    # wait for seed start up
    time.sleep(3)

    # start all other modules
    for server in env:
        modules = list(server["modules"])
        _log("starting {} on {}".format(" ".join(modules), server["host"]))
        _call(["ssh", "{}".format(server["host"]), "sudo ~/deploy-target.py restart -a start -m {}".format(" ".join(modules))])
    

def restart_module(args):
    modules = _extract_modules(args)
    if not modules:
        _log("Please specify at least one module or group")
    _check_version(args.target)
    for m in modules:
        _call(["ssh", "{}".format(args.target), "sudo ~/deploy-target.py restart -a {} -m {}".format(args.action, m)])


def start(args):
    if args.clean:
        _clean()
    modules = list(_extract_modules(args))
    if not len(modules) == 1:
        _log("Exact one module name expected")
        sys.exit(1)
    _start(modules[0], args.hostType, args.hostname)
 

def print_log(args):
    with open(log_file, 'r') as fin:
        print(fin.read())
    

def _check_version(target):
    cmd = ["ssh", target, "~/deploy-target.py version"]
    std = subprocess.check_output(cmd).decode("utf-8")
    t_version = int(std)
    if t_version < SCRIPT_VERSION:
        _log("old version of script at {}, updating...".format(target))
        _call(["scp", "deployutils.py", "deploy-target.py", "{}:".format(target)])
    elif t_version > SCRIPT_VERSION:
        _log("target version is newer than local script")
        exit(1)


def _start(module, hostType, hostname):
    _log("starting module {} with hostType {} on {}".format(module, hostType, hostname))
    module_name = module[8:]
    _call(["sbt", "'project {}'".format(module), "'runMain some.main.Class -t {} -h {}'".format(module_name, hostType, hostname)])


def _extract_modules(args):
    modules = set()
    if hasattr(args, "modules"):
        for m in args.modules:
            modules.add(m)
    if hasattr(args, "groups"):
        for g in args.groups:
            for m in groups[g]:
                modules.add(m)
    return modules


def _restart(host, modules, action):
    _check_version(host)
    _call(["ssh", "{}".format(host),
        "sudo ~/deploy-target.py restart -a {} -m {}".format(action, " ".join(modules))])
    

def _install(host, modules):
    if(modules):
        _check_version(host)
        _log("installing modules {} to {}".format(" ".join(modules), host))
        _call(["ssh", "{}".format(host), "sudo ~/deploy-target.py install -m {}".format(" ".join(modules))])


def _update_target(host, is_full):
    _check_version(host)
    if is_full:
        _call(["ssh", "{}".format(host), "sudo ~/deploy-target.py update --full"])
    else:
        _call(["ssh", "{}".format(host), "sudo ~/deploy-target.py update"])


def _clean():
    _log("cleaning...")
    _call(["sbt", "clean"])
    _call(["sbt", "update"])


def _publish(module, stage):
    _log("publishing module {}".format(module))
    _call(["sbt", "project {}".format(module), "set debRepoStage := \"{}\"".format(stage), "publishDebs"])


_base_docs_url = "http://doc.{}/docs/{}/"
_doc_user=""
_doc_password=""
def _publish_docs(stage):
    _log("publishing docs to {}".format(stage))
    try:
        for schema in ["v1.api.json"]:
                url = _base_docs_url.format(DOMAIN, stage) + schema

                latest_schema = re.sub("v[\d]+", "latest", schema)
                latest_url = _base_docs_url.format(DOMAIN, stage) + latest_schema

                schemaPath = "schema/schemas/generated/{}".format(schema)
                _call(["curl", "--user", "{}:{}".format(_doc_user, _doc_password), "-T", schemaPath, url])
                _call(["curl", "--user", "{}:{}".format(_doc_user, _doc_password), "-T", schemaPath, latest_url])

                #_call(["asciidoctor", "-o", "api.html", "api.ad"])
                #_call(["curl", "--user", "{}:{}".format(_doc_user, _doc_password), "-T", "api.html", _base_docs_url.format(stage)])

                _call(["curl", "--user", "{}:{}".format(_doc_user, _doc_password), "-T", "api_changes.md", _base_docs_url.format(stage)])
    except Exception as e:
        _log("ERROR: {}".format(e))
        _log("docs was not published!")
        pass



def _call(cmd):
    _log("will execute {}".format(cmd))
    exit_code = subprocess.call(cmd, stdout=log, stderr=log)
    if exit_code != 0:
        raise Exception("Failed to execute cmd: {}".format(cmd))

def _log(msg):
    print(msg)
    if log:
        m = msg
        if not m.endswith("\n"):
            m = m + "\n"

        m = time.strftime('%X %x') + ": " + m
        
        log.write(m)

        
def _sync_sources():
    sync_cmd = ['rsync', '--delete', '--exclude=.**', '--exclude=target', '--exclude=logs', '--exclude=__pycache__', '-avzh', '.', "{}:{}".format(remoteHost, REPO_NAME)]
    exit_code = subprocess.call(sync_cmd, stdout=log, stderr=log)
    


topParser = argparse.ArgumentParser()
topParser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help = "do not redirect output to /dev/null")

topParser.add_argument("-r", "--remote", dest="remote", choices=["build00"], help = "execute all commands at the remote host")

subParsers = topParser.add_subparsers(title = "Command categories")

cleanParser = argparse.ArgumentParser(add_help = False)
cleanParser.add_argument("-c", "--clean", dest="clean", action="store_true", help = "run `sbt clean` before building")

noDocsParser = argparse.ArgumentParser(add_help = False)
noDocsParser.add_argument("--no-docs", dest="no_docs", action="store_true", help = "skip docs publishing")

updateParser = argparse.ArgumentParser(add_help = False)
updateParser.add_argument("--no-update", dest="update", action="store_false", help = "do not run apt-get update before installing")
updateParser.add_argument("--full-update", dest="full_update",  default=False, action="store_true", help = "run apt-get update from all sources before installing")

startParser = subParsers.add_parser("start", description = "start backend module on local machine", parents = [cleanParser, modulesParser])
startParser.add_argument("-t", "--hosttype", dest="hostType", default="local", help = "backend host type", choices=["local"])
startParser.add_argument("-d", "--domain", dest="hostname", default="localhost", help = "akka hostname conf")
startParser.set_defaults(func = start)


shellParser = subParsers.add_parser("shell", description = "run shell command")
shellParser.add_argument("cmd")
shellParser.set_defaults(func = shell)


installParser = subParsers.add_parser("install", description = "installing backend modules to host", 
        parents = [modulesParser, groupsParser, hostParser, updateParser])
installParser.add_argument("-r", "--restart", dest="restart", action="store_true", help = "restart service after installation")
installParser.set_defaults(func = install)

publishParser = subParsers.add_parser("publish", description = "publishing deb to nexus repo", parents = [modulesParser, hostParser, groupsParser, cleanParser, noDocsParser])
publishParser.set_defaults(func = publish)

chickParser = subParsers.add_parser("chick", description = "hubot chick dev", 
        parents = [modulesParser, groupsParser, hostParser, cleanParser, updateParser, noDocsParser])
chickParser.set_defaults(func = chick)

deployParser = subParsers.add_parser("deploy", description = "deploy helper scripts to target", parents = [hostParser])
deployParser.set_defaults(func = copy_scripts)

deployDocsParser = subParsers.add_parser("publishdocs", description = "publish docs and api scheme", parents = [hostParser, cleanParser])
deployDocsParser.set_defaults(func = publish_docs)

restartParser = subParsers.add_parser("restart", description = "restart backend module", parents = [hostParser, modulesParser, groupsParser, actionParser])
restartParser.set_defaults(func = restart_module)

restartClusterParser = subParsers.add_parser("restartcluster", description = "start, stop backend", parents = [hostParser])
restartClusterParser.set_defaults(func = restart_cluster)

logParser = subParsers.add_parser("log", description = "print last deploy log to stdout")
logParser.set_defaults(func = print_log)
logParser.set_defaults(verbose = True) # in non verbose mode logs will be cleaned up at the beginning



try:
        import argcomplete
        argcomplete.autocomplete(topParser)
except ImportError:
        print("Try install python argcomplete :)")
        pass

parsed = topParser.parse_args()

start = time.time()
try:
    if parsed.verbose:
        verbose = True
    else:
        open(log_file, 'w').close() #clean up log file
        log = open(log_file, 'a')
        verbose = False
    if parsed.remote:
        remoteExec = True
        remoteHost = parsed.remote
        _sync_sources()

        cmd = []
        for a in sys.argv:
          if a != "-r" and a != remoteHost:
            cmd.append(a)
        
        cmd = ["'" + arg + "'" for arg in cmd]
        cmd = ["cd", REPO_NAME, ";"] + cmd
        c = ' '.join(cmd)
        cmd = ["ssh", remoteHost, c]
        _call(cmd)
    else:
       parsed.func(parsed)
except Exception as e:
    _log("ERROR: {}".format(e))
    end = time.time()
    _log("total time: {:.0f} sec".format(end - start))
    sys.exit(1)

end = time.time()
_log("total time: {:.0f} sec".format(end - start))

# vim: set tabstop=8 expandtab shiftwidth=4 softtabstop=4:
