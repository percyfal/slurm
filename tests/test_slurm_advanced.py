#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import pytest
import logging

logging.getLogger("cookiecutter").setLevel(logging.DEBUG)


def test_adjust_runtime(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile")))
    options = [" -j 1 -F runtime.txt --jn adjust_runtime-{jobid}"]
    options += ["--profile {}".format(str(data.join("slurm-advanced").join("slurm")))]
    options += ["--cluster-config {}".format(str(data.join("cluster-config.yaml")))]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    allres = ""
    (exit_code, output) = container.exec_run(cmd, user="user", stream=True)
    for res in output:
        print(res.decode())
        allres += res.decode()
    m = re.search("external jobid '(?P<jobid>\\d+)'", allres)
    jobid = m.group("jobid")
    (exit_code, output) = container.exec_run("sacct -o TimelimitRaw -n -j {}".format(jobid))
    assert int(output.decode().strip()) == 7200
    options = [" --unlock"]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    container.exec_run(cmd, user="user")


def test_adjust_memory(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile")))
    options = [" -j 1 -F memory.txt --jn adjust_memory-{jobid}"]
    options += ["--profile {}".format(str(data.join("slurm-advanced").join("slurm")))]
    options += ["--cluster-config {}".format(str(data.join("cluster-config.yaml")))]
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
    options = [" --unlock"]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    container.exec_run(cmd, user="user")


def test_memory_with_constraint(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile")))
    options = [" -j 1 -F memory_with_constraint.txt --jn memory_constraint-{jobid}"]
    options += ["--profile {}".format(str(data.join("slurm-advanced").join("slurm")))]
    options += ["--cluster-config {}".format(str(data.join("cluster-config.yaml")))]
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
    options = [" --unlock"]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    container.exec_run(cmd, user="user")


def test_cluster_short_queue(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile")))
    options = [" -j 1 -F short_queue.txt --jn short_queue-{jobid}"]
    options += ["--profile {}".format(str(data.join("slurm-advanced").join("slurm")))]
    options += ["--cluster-config {}".format(str(data.join("cluster-config.yaml")))]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    allres = ""
    (exit_code, output) = container.exec_run(cmd, user="user")
    assert exit_code == 0
