#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import pytest
import logging

logging.getLogger("cookiecutter").setLevel(logging.DEBUG)


@pytest.mark.slow
def test_adjust_runtime(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile"))
    )
    options = [
        " -j 1 -F runtime.txt --jn adjust_runtime-{jobid} --nolock",
        "--profile {}".format(str(data.join("slurm-advanced").join("slurm"))),
        "--cluster-config {}".format(str(data.join("cluster-config.yaml"))),
    ]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    allres = ""
    (exit_code, output) = container.exec_run(cmd, user="user", stream=True)
    for res in output:
        print(res.decode())
        allres += res.decode()
    m = re.search("external jobid '(?P<jobid>\\d+)'", allres)
    jobid = m.group("jobid")
    (exit_code, output) = container.exec_run(
        "sacct -o TimelimitRaw -n -j {}".format(jobid)
    )
    assert int(output.decode().strip()) == 7200


@pytest.mark.slow
def test_adjust_memory(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile"))
    )
    options = [
        " -j 1 -F memory.txt --jn adjust_memory-{jobid} --nolock",
        "--profile {}".format(str(data.join("slurm-advanced").join("slurm"))),
        "--cluster-config {}".format(str(data.join("cluster-config.yaml"))),
    ]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    allres = ""
    (exit_code, output) = container.exec_run(cmd, user="user", stream=True)
    for res in output:
        print(res.decode())
        allres += res.decode()
    m = re.search("external jobid '(?P<jobid>\\d+)'", allres)
    jobid = m.group("jobid")
    (exit_code, output) = container.exec_run("sacct -o ReqMem -n -j {}".format(jobid))
    m = re.search("(?P<mem>\\d+)", output.decode().split("\n")[0].strip())
    assert int(m.group("mem")) == 500


@pytest.mark.slow
def test_memory_with_constraint(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile"))
    )
    options = [
        " -j 1 -F memory_with_constraint.txt --jn memory_constraint-{jobid}",
        "--profile {}".format(str(data.join("slurm-advanced").join("slurm"))),
        "--cluster-config {}".format(str(data.join("cluster-config.yaml"))),
    ]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    allres = ""
    (exit_code, output) = container.exec_run(cmd, user="user", stream=True)
    for res in output:
        print(res.decode())
        allres += res.decode()
    m = re.search("external jobid '(?P<jobid>\\d+)'", allres)
    jobid = m.group("jobid")
    (exit_code, output) = container.exec_run("sacct -o ReqMem -n -j {}".format(jobid))
    m = re.search("(?P<mem>\\d+)", output.decode().split("\n")[0].strip())
    assert int(m.group("mem")) == 800


@pytest.mark.slow
def test_cluster_short_queue(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile"))
    )
    options = [
        " -j 1 -F short_queue.txt --jn short_queue-{jobid}",
        "--profile {}".format(str(data.join("slurm-advanced").join("slurm"))),
        "--cluster-config {}".format(str(data.join("cluster-config.yaml"))),
    ]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    allres = ""
    (exit_code, output) = container.exec_run(cmd, user="user")
    assert exit_code == 0
