# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause

from ansible.module_utils.basic import AnsibleModule  # noqa: F401

import os
import pytest
import subprocess
import sys

try:
    from unittest import mock
except ImportError:
    import mock

parentdir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../"))
with mock.patch.object(
    sys,
    "path",
    [parentdir, os.path.join(parentdir, "module_utils/network_lsr")] + sys.path,
):
    print(parentdir)
    with mock.patch.dict(
        "sys.modules",
        {"ansible": mock.Mock(), "ansible.module_utils": __import__("module_utils")},
    ):
        import library.network_connections as nc


class PytestRunEnvironment(nc.RunEnvironment):
    def log(self, connections, idx, severity, msg, **kwargs):
        if severity == nc.LogLevel.ERROR:
            print("Error: {}".format(connections[idx]))
            raise RuntimeError(msg)
        else:
            print("Log: {}".format(connections[idx]))

    def _check_mode_changed(self, *args, **kwargs):
        pass


def _configure_network(connections):
    cmd = nc.Cmd.create(
        "nm",
        run_env=PytestRunEnvironment(),
        connections_unvalidated=connections,
        connection_validator=nc.ArgValidator_ListConnections(),
    )
    cmd.run()


@pytest.fixture
def testnic1():
    veth_name = "testeth"
    try:
        subprocess.call(
            [
                "ip",
                "link",
                "add",
                veth_name,
                "type",
                "veth",
                "peer",
                "name",
                veth_name + "peer",
            ]
        )
        yield veth_name
    finally:
        subprocess.call(["ip", "link", "delete", veth_name])


def _get_ip_addresses(connection_name):
    ip_a = subprocess.check_output(["ip", "address", "show", connection_name])
    return ip_a.decode("UTF-8")


def test_static_ip_with_ethernet(testnic1):
    ip_address = "192.0.2.127/24"
    connections = [
        {
            "name": testnic1,
            "type": "ethernet",
            "state": "up",
            "ip": {"address": [ip_address]},
        }
    ]
    _configure_network(connections)
    assert ip_address in _get_ip_addresses(testnic1)
    assert os.path.exists("/etc/sysconfig/network-scripts/ifcfg-" + testnic1)
