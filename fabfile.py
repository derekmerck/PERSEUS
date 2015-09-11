"""
PERSEUS Fabfile
Merck, Spring 2015

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2015

<https://github.com/derekmerck/PERSEUS>

Dependencies: Fabric

See README.md for usage, notes, and license info.


## Setting up the network with fabric

```
$ fab --set config=config.yaml configure deploy start          # Stand up network
$ fab --set use_docker=true configure deploy start             # Stand up network inside of Docker containers
$ fab host1 start:pid=listener0,type=listener,controller=control0 # Startup a single pre-deployed host w/o config
```

"""

# TODO: Doesn't work, untested

from fabric.api import *

# TODO: Build this automagically from addresses
env.hosts = ['host1', 'host2', 'host3']
pid_by_host = ['control0', 'listener0', 'display0']

code_dir = '/PERSEUS'
shadow_config = 'shadow.yaml'


def host_type():
    run('uname -s')


def configure():

    def configure_windows_host():
        pass

    def configure_linux_host():
        run('wget https://repo.continuum.io/archive/Anaconda3-2.2.0-Linux-x86_64.sh')
        run('./Anaconda3-2.2.0-Linux-x86_64.sh')
        run('conda update conda matplotlib numpy pyyaml fabric')
        run('pip install Pyro4')
        run('apt-get update')
        run('apt-get install git')

    def configure_dow_host():
        # Docker on windows
        pass

    def configure_dom_host():
        # Docker on mac
        pass

    def configure_dol_host():
        # Docker on linux
        run('sudo apt-get install dockerio')

        # Start with the continuumio/anaconda distribution
        run('docker start -p 99500 my_container /bin/bash')  # Be sure to open the right port
        run('conda update conda matplotlib numpy pyyaml fabric')
        run('pip install Pyro4')
        run('apt-get update')
        run('apt-get install git')

        # Should probably just have a pre-configured container to pull and update
        pass

    # determine which host type we need to setup
    pass


def start():

    def get_pid(host):
        index = env.hosts.find(host)
        return pid_by_host[index]


    # TODO: If this is control, startup the name server
    with cd(code_dir):
        run("python PERSEUS -p {0}".format(get_pid(env.host)))


def deploy():
    with cd(code_dir):
        run("pip install git+https://github.com/derekmerck/PERSEUS")
        run("rsync shadow.yaml")