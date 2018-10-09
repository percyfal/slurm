#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pytest
import logging

logging.getLogger("cookiecutter").setLevel(logging.DEBUG)


def test_adjust_runtime(cluster):
    container, data = cluster
    snakemake_cmd = pytest.snakemake_cmd.format(
        workdir=str(data), snakefile=str(data.join("Snakefile")))
    options = [" -j 1 -F runtime.txt --resources runtime=10000 --jn adjust_runtime-{jobid}"]
    options += ["--profile {}".format(str(data.join("slurm-advanced").join("slurm")))]
    options += ["--cluster-config {}".format(str(data.join("cluster-config.yaml")))]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    allres = ""
    (exit_code, output) = container.exec_run(cmd, user="user", stream=True)
    for res in output:
        print(res.decode())
        allres += res.decode()
    # assert "Trying to restart" in allres
    # assert "Finished job" in allres
    options = [" --unlock"]
    cmd = "/bin/bash -c '{}'".format(snakemake_cmd + " ".join(options))
    container.exec_run(cmd, user="user")
