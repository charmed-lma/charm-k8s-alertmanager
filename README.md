Juju Charm/Operator for AlertManager on Kubernetes
==================================================

CI Badges
---------

Click on each badge for more details.

| Branch | Build Status | Coverage |
|--------|--------------|----------|
| master | [![Build Status (master)](https://travis-ci.org/charmed-lma/charm-k8s-alertmanager.svg?branch=master)](https://travis-ci.org/charmed-lma/charm-k8s-alertmanager) | [![Coverage Status](https://coveralls.io/repos/github/charmed-lma/charm-k8s-alertmanager/badge.svg?branch=master)](https://coveralls.io/github/charmed-lma/charm-k8s-alertmanager?branch=master) |


Quick Start
-----------

Do this first

```
git submodule update --init --recursive
```
Now this:

```
sudo snap install juju --classic
sudo snap install microk8s --classic
sudo microk8s.enable dns dashboard registry storage
sudo usermod -a -G microk8s $(whoami)
```

Log out then log back in so that the new group membership is applied to
your shell session.

```
juju bootstrap microk8s mk8s
```

Optional: Grab coffee/beer/tea or do a 5k run. Once the above is done, do:

```
juju create-storage-pool operator-storage kubernetes storage-class=microk8s-hostpath
juju add-model lma
juju deploy . --resource alertmanager-image=prom/alertmanager:v0.20.0
```

Wait until `juju status` shows that the alertmanager app has a status of active.


Check on AlertManager
---------------------

Run the following to check on its logs:

    microk8s.kubectl -n lma logs alertmanager-0

For more info on getting started with AlertManager see [its official getting
started guide](https://alertmanager.io/docs/alerting/overview/).


Make Prometheus Discover AlertManager
-------------------------------------

```
juju relate alertmanager prometheus
```

For information on deploying Prometheus, see [this charm](https://github.com/charmed-lma/charm-k8s-prometheus).


This Charm's Architecture
-------------------------

To learn how to navigate this charm's code and become an effective contributor,
please read the [Charmed LMA Operators Architecture](https://docs.google.com/document/d/1V5cA9D1YN8WGEClpLhUwQt2dYrg5VZEY99LZiE6Mx_A/edit?usp=sharing)
reference doc.


Install Test Dependencies
-------------------------

1. Install pyenv so that you can test with different versions of Python

```
curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
```

2. Append the following to your ~/.bashrc then log out and log back in

```
export PATH="/home/mark/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

3. Install development packages

```
sudo apt install build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git
```

4. Install Python 3.6.x and 3.7.x

```
pyenv install 3.6.X
pyenv install 3.7.X
```

NOTE: Replace X with the correct minor version as listed in `pyenv install --list`


Running the Unit Tests on Your Workstation
------------------------------------------

To run the test using the default interpreter as configured in `tox.ini`, run:

    tox

If you want to specify an interpreter that's present in your workstation, you
may run it with:

    tox -e python3.5

To view the coverage report that gets generated after running the tests above,
run:

    make coverage-server

The above command should output the port on your workstation where the server is
listening on. If you are running the above command on [Multipass](https://multipass.io),
first get the Ubuntu VM's IP via `multipass list` and then browse to that IP and
the abovementioned port.

NOTE: You can leave that static server running in one session while you continue
to execute `tox` on another session. That server will pick up any new changes to
the report automatically so you don't have to restart it each time.


Troubleshooting
---------------

Since Kubernetes charms are not supported by `juju debug-hooks`, the only
way to intercept code execution is to initialize the non-tty-bound
debugger session and connect to the session externally.

For this purpose, we chose the [rpdb](https://pypi.org/project/rpdb/), the
remote Python debugger based on pdb.

For example, given that you have already deployed an application named
`alertmanager` in a Juju model named `lma` and you would like to debug your
`config-changed` handler, execute the following:


    kubectl exec -it pod/alertmanager-operator-0 -n lma -- /bin/sh


This will open an interactive shell within the operator pod. Then, install
the editor and the RPDB:


    apt update
    apt install telnet vim -y
    pip3 install rpdb


Open the charm entry point in the editor:


    vim /var/lib/juju/agents/unit-alertmanager-0/charm/src/charm.py


Find a `on_config_changed_handler` function definition in the `charm.py` file.
Modify it as follows:


    def on_config_changed_handler(event, fw_adapter):
        import rpdb
        rpdb.set_trace()
        # < ... rest of the code ... >


Save the file (`:wq`). Do not close the current shell session!

Open another terminal session and trigger the `config-changed` hook as follows:


    juju config alertmanager external-labels='{"foo": "bar"}'


Do a `juju status`, until you will see the following:


    Unit           Workload  Agent      Address    Ports     Message
    alertmanager/0*  active    executing  10.1.28.2  9090/TCP  (config-changed)

This message means, that unit has started the `config-changed` hook routine and
it was already intercepted by the rpdb.

Now, return back to the operator pod session.

Enter the interactive debugger:


    telnet localhost 4444


You should see the debugger interactive console.


    # telnet localhost 4444
    Trying ::1...
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    > /var/lib/juju/agents/unit-alertmanager-0/charm/hooks/config-changed(91)on_config_changed_handler()
    -> set_juju_pod_spec(fw_adapter)
    (Pdb) where
      /var/lib/juju/agents/unit-alertmanager-0/charm/hooks/config-changed(141)<module>()
    -> main(Charm)
      /var/lib/juju/agents/application-alertmanager/charm/lib/ops/main.py(212)main()
    -> _emit_charm_event(charm, juju_event_name)
      /var/lib/juju/agents/application-alertmanager/charm/lib/ops/main.py(128)_emit_charm_event()
    -> event_to_emit.emit(*args, **kwargs)
      /var/lib/juju/agents/application-alertmanager/charm/lib/ops/framework.py(205)emit()
    -> framework._emit(event)
      /var/lib/juju/agents/application-alertmanager/charm/lib/ops/framework.py(710)_emit()
    -> self._reemit(event_path)
      /var/lib/juju/agents/application-alertmanager/charm/lib/ops/framework.py(745)_reemit()
    -> custom_handler(event)
      /var/lib/juju/agents/unit-alertmanager-0/charm/hooks/config-changed(68)on_config_changed()
    -> on_config_changed_handler(event, self.fw_adapter)
    > /var/lib/juju/agents/unit-alertmanager-0/charm/hooks/config-changed(91)on_config_changed_handler()
    -> set_juju_pod_spec(fw_adapter)
    (Pdb)

From this point forward, the usual pdb commands apply. For more information on 
how to use pdb, see the [official pdb documentation](https://docs.python.org/3/library/pdb.html)


References
----------

Much of how this charm is architected is guided by the following classic
references. It will do well for future contributors to read and take them to heart:

1. [Hexagonal Architecture](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software)) by Alistair Cockburn
1. [Boundaries (Video)](https://pyvideo.org/pycon-us-2013/boundaries.html) by Gary Bernhardt
1. [Domain Driven Design (Book)](https://dddcommunity.org/book/evans_2003/) by Eric Evans
