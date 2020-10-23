#!/usr/bin/env python3
import pytest
import time
import re
import py

@pytest.fixture
def issue49(cookie_factory, datafile):
    p = datafile("Snakefile_issue49", "Snakefile")
    cookie_factory()
    d = py.path.local(p.dirname)
    config = d.join("slurm").join("config.yaml")
    lines = re.sub("restart-times: 3", "restart-times: 0",
                   config.read())
    config.write(lines)


@pytest.mark.xfail
def test_issue49(smk_runner, issue49):
    """https://github.com/Snakemake-Profiles/slurm/issues/49

    Cancelling a slurm job leaves an incomplete file that causes
    Snakemake to incorrectly state that there is 'Nothing to be done'.

    """
    smk_runner.make_target("foo.delayOutput.txt", asynchronous=True)
    time.sleep(5)
    while smk_runner.check_jobstatus("RUNNING", verbose=False) is None:
        time.sleep(5)
    print("Job is running")
    time.sleep(20)
    jid = smk_runner.external_jobid[0]
    print(f"Cancelling job {jid}")
    smk_runner.exec_run(f"scancel {jid}")
    while smk_runner.check_jobstatus("CANCELLED", verbose=True) is None:
        time.sleep(5)
    print("Job has been cancelled; resubmitting")
    smk_runner.make_target("foo.delayOutput.txt")
    time.sleep(10)
    assert "Nothing to be done" in print(smk_runner.output)
