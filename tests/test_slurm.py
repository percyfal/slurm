#!/usr/bin/env python3
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


class Timer:
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


@pytest.mark.slow
def test_timeout(smk_runner):
    """Test that rule excessive runtime resources times out"""
    opts = '--cluster "sbatch -p normal -c 1 -t {resources.runtime}" --attempt 1'
    with pytest.raises(TimeOut):
        with Timer():
            smk_runner.exec_run("timeout.txt", options=opts, profile=None)
    assert smk_runner.check_jobstatus("TIMEOUT")


@pytest.mark.slow
def test_no_timeout(smk_runner):
    """Test that rule that updates runtime doesn't timeout"""
    smk_runner.exec_run("timeout.txt")
    assert "Trying to restart" in smk_runner.output
    assert "Finished job" in smk_runner.output


def test_profile_status_running(smk_runner):
    """Test that slurm-status.py catches RUNNING status"""
    opts = '--cluster " sbatch -p normal -c 1 -t 1"'
    smk_runner.exec_run("timeout.txt", options=opts, asynchronous=True)
    time.sleep(5)
    smk_runner.exec_run(cmd='squeue -h -o "%.18i"', verbose=False)
    jobids = [int(j.strip()) for j in smk_runner.output if j]
    for jid in jobids:
        output = smk_runner.exec_run(
            cmd=f"{smk_runner.slurm_status} {jid}", verbose=False, iterable=False
        )
        if output:
            assert output.strip() == "running"


def test_slurm_submit(smk_runner):
    """Test that slurm-submit.py works"""
    jobscript = smk_runner.script("jobscript.sh")
    jobscript.write(
        '#!/bin/bash\n# properties = {"cluster": {"job-name": "sm-job"}}\nsleep 10'
    )
    smk_runner.exec_run(cmd=f"{smk_runner.slurm_submit} {jobscript}", asynchronous=True)
    output = smk_runner.exec_run(cmd='squeue -h -o "%.j"', iterable=False)
    assert "sm-job" in output
