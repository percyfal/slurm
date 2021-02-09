#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pytest


@pytest.fixture
def profile(cookie_factory, data):
    cookie_factory(advanced="yes")


@pytest.mark.skipci
@pytest.mark.slow
@pytest.mark.docker
def test_adjust_runtime(smk_runner, profile):
    smk_runner.make_target(
        "timeout.txt", options=f"--cluster-config {smk_runner.cluster_config}"
    )
    m = smk_runner.check_jobstatus(r"(?P<timelimit>\d+)", "-o TimeLimitRaw -n", which=1)
    assert int(m.group("timelimit")) == 2


@pytest.mark.skipci
@pytest.mark.timeout(60)
@pytest.mark.docker
def test_adjust_memory(smk_runner, profile):
    smk_runner.make_target(
        "memory.txt", options=f"--cluster-config {smk_runner.cluster_config}"
    )
    m = smk_runner.check_jobstatus(r"(?P<mem>\d+)", "-o ReqMem -n")
    assert int(m.group("mem")) == 500


@pytest.mark.skipci
@pytest.mark.timeout(60)
@pytest.mark.docker
def test_memory_with_constraint(smk_runner, profile):
    smk_runner.make_target(
        "memory_with_constraint.txt",
        options=f"--cluster-config {smk_runner.cluster_config}",
    )
    m = smk_runner.check_jobstatus(r"(?P<mem>\d+)", "-o ReqMem -n")
    assert int(m.group("mem")) == 800


@pytest.mark.skipci
@pytest.mark.timeout(60)
@pytest.mark.docker
def test_cluster_short_queue(smk_runner, profile):
    smk_runner.make_target(
        "short_queue.txt",
        options=f"--cluster-config {smk_runner.cluster_config}",
    )
    assert smk_runner.check_jobstatus("debug", "-n -o Partition")


@pytest.mark.skipci
def test_si_units(smk_runner, profile):
    """Test that setting memory with si units works"""
    _, output = smk_runner.make_target(
        "siunit.txt",
        options=f"--cluster-config {smk_runner.cluster_config}",
        stream=False
    )
    assert "requested memory (1000)" in (smk_runner.output)
