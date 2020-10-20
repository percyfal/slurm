#!/usr/bin/env python3
import os
from os.path import basename, join as pjoin
import re
import py
import pytest
import docker
import shutil
import logging
from pytest_cookies.plugin import Cookies
from wrapper import SnakemakeRunner, ShellContainer


def pytest_addoption(parser):
    parser.addoption("--partition", action="store", default="normal", type=str)


def pytest_configure(config):
    pytest.local_user_id = os.getuid()
    dname = os.path.dirname(__file__)
    pytest.cookie_template = py.path.local(dname).join(os.pardir)
    config.addinivalue_line("markers", "slow: mark tests as slow")
    setup_logging(config.getoption("--log-level"))
    pytest.partition = config.getoption("--partition")


def setup_logging(level):
    if level is None:
        level = logging.WARN
    elif re.match(r"\d+", level):
        level = int(level)
    logging.basicConfig(level=level)
    logging.getLogger("urllib3").setLevel(level)
    logging.getLogger("docker").setLevel(level)
    logging.getLogger("poyo").setLevel(level)
    logging.getLogger("binaryornot").setLevel(level)


@pytest.fixture
def data(tmpdir_factory, _cookiecutter_config_file):
    p = tmpdir_factory.mktemp("data")
    dname = os.path.dirname(__file__)
    # Snakefile for test
    SNAKEFILE = py.path.local(pjoin(dname, "Snakefile"))
    snakefile = p.join("Snakefile")
    SNAKEFILE.copy(snakefile)
    # Cluster configuration
    CLUSTERCONFIG = py.path.local(pjoin(dname, "cluster-config.yaml"))
    cluster_config = p.join("cluster-config.yaml")
    CLUSTERCONFIG.copy(cluster_config)

    # Install cookie in data directory for each test
    cookie_template = pjoin(os.path.abspath(dname), os.pardir)
    output_factory = tmpdir_factory.mktemp
    defaults = (
        f"partition={pytest.partition} "
        "output=logs/slurm-%j.out error=logs/slurm-%j.err"
    )
    c = Cookies(cookie_template, output_factory, _cookiecutter_config_file)
    c._new_output_dir = lambda: str(p.join("slurm"))
    c.bake(extra_context={"sbatch_defaults": defaults})
    # Advanced setting
    c = Cookies(cookie_template, output_factory, _cookiecutter_config_file)
    c._new_output_dir = lambda: str(p.join("slurm-advanced"))
    c.bake(
        extra_context={
            "sbatch_defaults": defaults,
            "advanced_argument_conversion": "yes",
        }
    )
    return p


@pytest.fixture(scope="session")
def slurm(request):
    if shutil.which("sbatch"):
        return ShellContainer()
    else:
        client = docker.from_env()
        # Preferably return container id here
        container_list = client.containers.list(
            filters={"name": "cookiecutter-slurm_slurm"}
        )
        container = container_list[0] if len(container_list) > 0 else None
        if container:
            return container
    msg = [
        (
            "\n   no sbatch or docker stack 'cookiecutter-slurm' running;",
            " skipping slurm-based tests",
        ),
        (
            "   run tests on a slurm HPC or deploy a docker stack with ",
            f"{os.path.dirname(__file__)}/deploystack.sh",
        ),
    ]
    pytest.skip("\n".join(msg))


@pytest.fixture
def smk_runner(slurm, data, request):
    advanced = re.search("advanced", basename(request.fspath)) is not None
    _, partitions = slurm.exec_run('sinfo -h -o "%P"')
    plist = [p.strip("*") for p in partitions.decode().split("\n") if p != ""]
    if pytest.partition not in plist:
        pytest.skip(
            "partition '{}' not in cluster partitions '{}'".format(
                pytest.partition, ",".join(plist)
            )
        )
    return SnakemakeRunner(slurm, data, request.node.name, advanced, pytest.partition)
