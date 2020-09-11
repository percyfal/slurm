#!/usr/bin/env python3
import os
import re
import sys
import py
import pytest
import docker
import shlex
import subprocess as sp
import time
import logging
from pytest_cookies.plugin import Cookies
from wrapper import SlurmRunner, SnakemakeRunner

# TODO: put in function so level can be set via command line
logging.basicConfig(level=logging.INFO)
logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("docker").setLevel(logging.INFO)
logging.getLogger("poyo").setLevel(logging.INFO)
logging.getLogger("binaryornot").setLevel(logging.INFO)
logging.getLogger("cookiecutter").setLevel(logging.INFO)
logger = logging.getLogger("cookiecutter-slurm")

ROOT_DIR = py.path.local(os.path.dirname(__file__)).join(os.pardir)
DOCKER_STACK_NAME = "cookiecutter-slurm"
SLURM_SERVICE = DOCKER_STACK_NAME + "_slurm"
LOCAL_USER_ID = os.getuid()


# Snakefile for test
SNAKEFILE = py.path.local(os.path.join(os.path.dirname(__file__), "Snakefile"))
# Cluster configuration
CLUSTERCONFIG = py.path.local(
    os.path.join(os.path.dirname(__file__), "cluster-config.yaml")
)

# Check services
client = docker.from_env()
service_list = client.services.list(filters={"name": "cookiecutter-slurm_slurm"})
service_up = pytest.mark.skipif(
    len(service_list) == 0,
    reason="docker service cookiecutter-slurm is down; deploy docker-compose.yaml",
)


def pytest_configure(config):
    pytest.local_user_id = LOCAL_USER_ID
    pytest.template = ROOT_DIR
    config.addinivalue_line("markers", "slow: mark tests as slow")


def add_slurm_user(user, container):
    logger.info(f"Adding user {user} to {container}")
    try:
        cmd_args = [
            "/bin/bash -c '",
            "if",
            "id",
            str(user),
            ">/dev/null;",
            "then",
            'echo "User {} exists";'.format(user),
            "else",
            "useradd --shell /bin/bash ",
            '-u {} -o -c "" -m -g slurm user;'.format(user),
            "fi'",
        ]
        cmd = " ".join(cmd_args)
        container.exec_run(cmd, detach=False, stream=False, user="root")
    except:
        logger.warn(f"Failed to add user {user} to {container}")
        raise


def link_python(container):
    (_, output) = container.exec_run(
        "which python{}.{}".format(sys.version_info.major, sys.version_info.minor)
    )
    cmd = "ln -s {} /usr/bin/python{}".format(output.decode(), sys.version_info.major)
    container.exec_run(cmd, detach=False, stream=False, user="root")


SLURM_CONF = """
# NEW COMPUTE NODE DEFINITIONS
NodeName=DEFAULT Sockets=1 CoresPerSocket=2 ThreadsPerCore=2 State=UNKNOWN TmpDisk=10000
NodeName=c[1-2] NodeHostName=localhost NodeAddr=127.0.0.1 RealMemory=500 Feature=thin,mem500MB
NodeName=c[3-4] NodeHostName=localhost NodeAddr=127.0.0.1 RealMemory=800 Feature=fat,mem800MB
NodeName=c[5] NodeHostName=localhost NodeAddr=127.0.0.1 RealMemory=500 Feature=thin,mem500MB
# NEW PARTITIONS
PartitionName=normal Default=YES Nodes=c[1-4] Shared=NO MaxNodes=1 MaxTime=5-00:00:00 DefaultTime=5-00:00:00 State=UP DefMemPerCPU=500 OverSubscribe=NO
PartitionName=debug  Nodes=c[5] Shared=NO MaxNodes=1 MaxTime=05:00:00 DefaultTime=05:00:00 State=UP DefMemPerCPU=500
"""


def setup_sacctmgr(container):
    slurmconf = "/etc/slurm/slurm.conf"
    (exit_code, output) = container.exec_run(
        f'grep -c "NEW PARTITIONS" {slurmconf}',
        user="root",
        detach=False,
        stream=False,
    )
    cmd_args = [
        "/bin/bash -c 'sacctmgr --immediate add cluster name=linux;",
        f'sed -i -e "s/CR_CPU_Memory/CR_Core/g" {slurmconf} ;',
        f'sed -i -e "s/^NodeName/# NodeName/g" {slurmconf} ;',
        f'sed -i -e "s/^PartitionName/# PartitionName/g" {slurmconf} ;',
        f'echo "{SLURM_CONF}" >> {slurmconf} ; ',
        "service supervisor stop;",
        "service supervisor start;",
        "supervisorctl restart slurmdbd;",
        "supervisorctl restart slurmctld;",
        'sacctmgr --immediate add account none,test Cluster=linux Description="none" Organization="none"\'',
    ]
    cmd = " ".join(cmd_args)
    if int(output.decode().strip()) == 0:
        logger.info("Setting up slurm partitions...")
        (exit_code, output) = container.exec_run(
            cmd, detach=False, stream=True, user="root"
        )
        logger.info("...setting up slurm partitions done!")
    if exit_code:
        logger.critical("Failed to setup account")
        sys.exit()


@pytest.fixture(scope="session")
def data(tmpdir_factory, _cookiecutter_config_file):
    p = tmpdir_factory.mktemp("data")
    snakefile = p.join("Snakefile")
    SNAKEFILE.copy(snakefile)
    cluster_config = p.join("cluster-config.yaml")
    CLUSTERCONFIG.copy(cluster_config)
    template = os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir)
    output_factory = tmpdir_factory.mktemp
    defaults = "partition=normal output=logs/slurm-%j.out error=logs/slurm-%j.err"
    c = Cookies(template, output_factory, _cookiecutter_config_file)
    c._new_output_dir = lambda: str(p.join("slurm"))
    c.bake(extra_context={"sbatch_defaults": defaults})
    # Advanced setting
    c = Cookies(template, output_factory, _cookiecutter_config_file)
    c._new_output_dir = lambda: str(p.join("slurm-advanced"))
    c.bake(
        extra_context={
            "sbatch_defaults": defaults,
            "advanced_argument_conversion": "yes",
        }
    )
    return p


@pytest.fixture(scope="session")
def cluster(data):
    client = docker.from_env()
    service_list = client.services.list(filters={"name": "cookiecutter-slurm_slurm"})
    s = client.services.get(service_list[0].id)
    container = client.containers.get(
        s.tasks()[0]["Status"]["ContainerStatus"]["ContainerID"]
    )
    add_slurm_user(pytest.local_user_id, container)
    setup_sacctmgr(container)
    link_python(container)
    # Hack: modify first line in snakemake file
    container.exec_run(["sed", "-i", "-e", "s:/usr:/opt:", "/opt/local/bin/snakemake"])
    return container, data


# NB: currently not used
@pytest.fixture
def slurm_runner(cluster, request):
    container, data = cluster
    return SlurmRunner(container, data, request.node.name)


@pytest.fixture
def smk_runner(cluster, request):
    container, data = cluster
    advanced = re.search("advanced", os.path.basename(request.fspath)) is not None
    return SnakemakeRunner(container, data, request.node.name, advanced=advanced)
