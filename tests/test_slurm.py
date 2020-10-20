#!/usr/bin/env python3
import pytest
import signal
import time
from timeit import default_timer
import logging


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
        if self.verbose:
            logging.info(f"Elapsed time: {int(self.elapsed_time())}s")
        signal.signal(signal.SIGALRM, self.old_handler)
        signal.alarm(0)


@pytest.mark.slow
def test_no_timeout(smk_runner):
    """Test that rule that updates runtime doesn't timeout"""
    smk_runner.make_target("timeout.txt")
    assert "Trying to restart" in smk_runner.output
    assert "Finished job" in smk_runner.output


@pytest.mark.slow
def test_timeout(smk_runner):
    """Test that rule excessive runtime resources times out"""
    opts = (
        f'--cluster "sbatch -p {smk_runner.partition} '
        '-c 1 -t {resources.runtime}" --attempt 1'
    )
    with pytest.raises(TimeOut):
        with Timer():
            smk_runner.make_target("timeout.txt", options=opts, profile=None)
    assert smk_runner.check_jobstatus("TIMEOUT|NODE_FAIL")


def test_profile_status_running(smk_runner):
    """Test that slurm-status.py catches RUNNING status"""
    opts = f'--cluster "sbatch -p {smk_runner.partition} -c 1 -t 1"'
    smk_runner.make_target(
        "timeout.txt", options=opts, profile=None, asynchronous=True
    )  # noqa: E501
    time.sleep(5)
    jid = smk_runner.external_jobid[0]
    _, output = smk_runner.exec_run(
        cmd=f"{smk_runner.slurm_status} {jid}", stream=False
    )
    assert output.decode().strip() == "running"


def test_slurm_submit(smk_runner):
    """Test that slurm-submit.py works"""
    jobscript = smk_runner.script("jobscript.sh")
    jobscript.write(
        (
            "#!/bin/bash\n"
            '# properties = {"cluster": {"job-name": "sm-job"},'
            '"input": [], "output": [], "wildcards": {}, "params": {},'
            '"rule": "slurm_submit"}\n'
        )
    )
    _, output = smk_runner.exec_run(
        cmd=f"{smk_runner.slurm_submit} {jobscript}", stream=False
    )
    time.sleep(5)
    assert smk_runner.check_jobstatus(
        "sm-job",
        options="--format=jobname",
        jobid=int(output.decode().strip()),  # noqa: E501
    )
