#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pytest
import logging

logging.getLogger("cookiecutter").setLevel(logging.INFO)


@pytest.mark.slow
def test_adjust_runtime(smk_runner):
    smk_runner.exec_run(
        "timeout.txt", options=f"--cluster-config {smk_runner.cluster_config}"
    )
    m = smk_runner.check_jobstatus("(?P<timelimit>\\d+)", "-o TimeLimitRaw -n", which=1)
    assert int(m.group("timelimit")) == 2


@pytest.mark.slow
def test_adjust_memory(smk_runner):
    smk_runner.exec_run(
        "memory.txt", options=f"--cluster-config {smk_runner.cluster_config}"
    )
    m = smk_runner.check_jobstatus("(?P<mem>\\d+)", "-o ReqMem -n")
    assert int(m.group("mem")) == 500


@pytest.mark.slow
def test_memory_with_constraint(smk_runner):
    smk_runner.exec_run(
        "memory_with_constraint.txt",
        options=f"--cluster-config {smk_runner.cluster_config}",
    )
    m = smk_runner.check_jobstatus("(?P<mem>\\d+)", "-o ReqMem -n")
    assert int(m.group("mem")) == 800


@pytest.mark.slow
def test_cluster_short_queue(smk_runner):
    smk_runner.exec_run(
        "short_queue.txt", options=f"--cluster-config {smk_runner.cluster_config}",
    )
    assert smk_runner.check_jobstatus("debug", "-n -o Partition")
