#!/usr/bin/env python3
import re
import pytest
import signal
import time
from timeit import default_timer
import logging

logging.getLogger("cookiecutter").setLevel(logging.DEBUG)


class TimeOut(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeOut


class Timer(object):
    def __init__(self, verbose=False, limit=10):
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


def test_timeout(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile")))
    options = [" --cluster ", "\" sbatch -p normal -n 1 ",
               "-t 0:{resources.runtime}\" -j 2"]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    with pytest.raises(TimeOut):
        with Timer() as t:
            container.exec_run(cmd, user="user")


def test_profile_no_timeout(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile")))
    options = [" -j 1 -F foo.txt"]
    options += ["--profile {}".format(str(data.join("slurm")))]
    #options += ["--time {resources.runtime}"]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    for res in container.exec_run(cmd, user="user", stream=True):
        print(res.decode())


def test_profile_status_running(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile")))
    options = [" --cluster ", "\" sbatch -p normal -n 1 ",
               "-t 0:20\" -j 1 -F foo.txt"]
    options += ["--profile {}".format(str(data.join("slurm")))]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    container.exec_run(cmd, user="user", detach=True)
    time.sleep(5)
    res = container.exec_run("squeue -h -o \"%.18i\"")
    jobids = [int(j.strip()) for j in res.decode().split("\n") if j]
    for jid in jobids:
        for res in container.exec_run("{} {}".format(
                str(data.join("slurm/slurm-status.py")), jid),
                                      stream=True):
            assert res.decode().strip() == "running"


def test_slurm_submit(cluster):
    container, data = cluster
    cmd_args = [pytest.path, " && ",
                str(data.join("slurm").join("slurm-submit.py")), "--wrap",
                "\"sleep 10\""]
    cmd = "/bin/bash -c '{}'".format(" ".join(cmd_args))
    for res in container.exec_run(cmd, stream=True):
        print(res.decode())
