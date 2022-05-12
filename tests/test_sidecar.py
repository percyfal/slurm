#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import tempfile
import time

import pytest


@pytest.mark.slow
@pytest.mark.timeout(60)
def test_cluster_sidecar_smoke():
    env = dict(os.environ)
    env["PATH"] = (
        os.path.realpath(os.path.dirname(__file__) + "/mock-slurm/bin") + ":" + env.get("PATH")
    )
    path_sidecar_py = os.path.realpath(
        os.path.dirname(__file__) + "/../{{cookiecutter.profile_name}}/slurm-sidecar.py"
    )
    with tempfile.TemporaryFile("w+t") as tmpf:
        with subprocess.Popen(["python", path_sidecar_py], env=env, text=True, stdout=tmpf) as proc:
            time.sleep(2)
            os.kill(proc.pid, signal.SIGTERM)
        tmpf.seek(0)
        stdout = tmpf.read()
    the_vars = json.loads(stdout.splitlines()[0])
    assert "server_port" in the_vars
    assert "server_secret" in the_vars
    assert proc.returncode == 0
