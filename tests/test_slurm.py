#!/usr/bin/env python3
import re
import pytest
import signal
import time
from timeit import default_timer
import logging
from wrapper import Snakemake

logging.getLogger("cookiecutter").setLevel(logging.DEBUG)


class TimeOut(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeOut


class Timer(object):
    def __init__(self, verbose=True, limit=90):
        self.old_handler = signal.getsignal(signal.SIGALRM)
        self.verbose = verbose
        self.timer = default_timer
        self.limit = limit

    def elapsed_time(self):
        return self.timer() - self.start

    def __enter__(self):
        self.start = self.timer()
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.limit)
        return self

    def __exit__(self, *args):
        signal.signal(signal.SIGALRM, self.old_handler)
        signal.alarm(0)


@pytest.fixture
def runner(cluster, request):
    container, data = cluster
    return Snakemake(container, data, request.node.name)


@pytest.mark.slow
def test_timeout(runner):
    """Test that rule with longer execution time than runtime resources times out"""
    opts = '--cluster " sbatch -p normal -c 1 -t {resources.runtime}" --attempt 1'
    for output in runner("foo.txt", options=opts, profile=None):
        print(output)
    print(runner._cmd)


@pytest.mark.slow
def test_timeout_obsolete(cluster):
    """Test that rule with longer execution time than runtime resources times out"""
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile"))
    )
    options = [
        '--cluster " sbatch -p normal -c 1 -t {resources.runtime}"',
        "-j 1 --attempt 1 --nolock --jn timeout-{jobid} -F foo.txt",
    ]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    print(cmd)
    with pytest.raises(TimeOut):
        with Timer() as t:
            (_, output) = container.exec_run(cmd, user="user", stream=True)
            allres = ""
            for res in output:
                print(res.decode())
                allres += res.decode()
    m = re.search(r"Submitted batch job (\d+)", allres)
    try:
        jobid = m.group(1)
        (_, output) = container.exec_run(f"sacct -j {jobid}")
    except:
        raise
    assert re.search("TIMEOUT", output.decode())


@pytest.mark.slow
def test_no_timeout(cluster):
    """Test that rule that updates runtime doesn't timeout"""
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile"))
    )
    options = [
        " -j 1 -F foo.txt --jn no_timeout-{jobid} --nolock",
        "--profile {}".format(str(data.join("slurm").join("slurm"))),
    ]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    allres = ""
    (_, output) = container.exec_run(cmd, user="user", stream=True)
    for res in output:
        print(res.decode())
        allres += res.decode()
    assert "Trying to restart" in allres
    assert "Finished job" in allres


def test_profile_status_running(cluster):
    """Test that slurm-status.py catches RUNNING status"""
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile"))
    )
    options = [
        ' --cluster " sbatch -p normal -n 1 -t 1"',
        "-j 1 -F foo.txt --jn running-{jobid} --nolock",
    ]
    options += ["--profile {}".format(str(data.join("slurm").join("slurm")))]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    container.exec_run(cmd, user="user", detach=True)
    time.sleep(5)
    (exit_code, res) = container.exec_run('squeue -h -o "%.18i"')
    jobids = [int(j.strip()) for j in res.decode().split("\n") if j]
    for jid in jobids:
        (exit_code, output) = container.exec_run(
            "{} {}".format(str(data.join("slurm/slurm/slurm-status.py")), jid),
            stream=True,
        )
        for res in output:
            assert res.decode().strip() == "running"


def test_slurm_submit(cluster):
    """Test that slurm-submit.py works"""
    container, data = cluster
    jobscript = data.join("jobscript.sh")
    jobscript.write(
        '#!/bin/bash\n# properties = {"cluster": {"job-name": "sm-job"}}\nsleep 10'
    )
    cmd_args = [
        pytest.path,
        " && ",
        str(data.join("slurm").join("slurm").join("slurm-submit.py")),
        str(jobscript),
    ]
    cmd = "/bin/bash -c '{}'".format(" ".join(cmd_args))
    container.exec_run(cmd)
    (exit_code, res) = container.exec_run('squeue -h -o "%.j"')
    assert "sm-job" in res.decode()


def test_cluster_config(cluster):
    """Test that slurm-submit.py works"""
    container, data = cluster
    jobscript = data.join("jobscript.sh")
    jobscript.write(
        '#!/bin/bash\n# properties = {"cluster": {"job-name": "sm-job"}}\nsleep 10'
    )
    cmd_args = [
        pytest.path,
        " && ",
        str(data.join("slurm").join("slurm").join("slurm-submit.py")),
        str(jobscript),
    ]
    cmd = "/bin/bash -c '{}'".format(" ".join(cmd_args))
    container.exec_run(cmd)
    (exit_code, res) = container.exec_run('squeue -h -o "%.j"')
    assert "sm-job" in res.decode()
