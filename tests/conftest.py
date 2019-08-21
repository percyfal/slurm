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

# TODO: put in function so level can be set via command line
logging.basicConfig(level=logging.INFO)
logging.getLogger("urllib3").setLevel(logging.INFO)
logging.getLogger("docker").setLevel(logging.INFO)
logging.getLogger("poyo").setLevel(logging.INFO)
logging.getLogger("binaryornot").setLevel(logging.INFO)
logging.getLogger("cookiecutter").setLevel(logging.INFO)
logger = logging.getLogger("cookiecutter-slurm")


ROOT_DIR = py.path.local(os.path.dirname(__file__)).join(os.pardir)
# Variables for docker stack setup
STATUS_ATTEMPTS = 20
TIMEOUT = 10
DOCKER_STACK_NAME = "cookiecutter-slurm"
SLURM_SERVICE = DOCKER_STACK_NAME + "_slurm"
LOCAL_USER_ID = os.getuid()

# Versions
PYTHON_VERSION = "py{}{}".format(sys.version_info.major,
                                 sys.version_info.minor)
try:
    SNAKEMAKE_VERSION = sp.check_output(
        ["snakemake", "--version"]).decode().strip()
except:
    logger.error("couldn't get snakemake version")
    raise

# Image names
SLURM_IMAGE = "giovtorres/docker-centos7-slurm"
SNAKEMAKE_IMAGE = "quay.io/biocontainers/snakemake"
SNAKEMAKE_BASETAG = "{}--{}".format(SNAKEMAKE_VERSION, PYTHON_VERSION)


# Snakefile for test
SNAKEFILE = py.path.local(os.path.join(os.path.dirname(__file__),
                                       "Snakefile"))
# Cluster configuration
CLUSTERCONFIG = py.path.local(os.path.join(os.path.dirname(__file__),
                                           "cluster-config.yaml"))


def pytest_configure():
    pytest.local_user_id = LOCAL_USER_ID
    pytest.snakemake_cmd = " ".join(
        ["export PATH=\"$SNAKEMAKE_PATH:$PATH\"",
         " && snakemake ", "-d {workdir} ",
         " -s {snakefile} -p "])
    pytest.path = "export PATH=\"$SNAKEMAKE_PATH:$PATH\""
    pytest.template = ROOT_DIR


def add_slurm_user(user, container):
    try:
        cmd_args = [
            "/bin/bash -c '", "if", "id", str(user), ">/dev/null;",
            "then", "echo \"User {} exists\";".format(user),
            "else",
            "useradd --shell /bin/bash ",
            "-u {} -o -c \"\" -m -g slurm user;".format(user),
            "fi'"]
        cmd = " ".join(cmd_args)
        container.exec_run(cmd, detach=False, stream=False, user="root")
    except:
        raise


def link_python(container):
    (exit_code, output) = container.exec_run("which python{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor))
    cmd = "ln -s {} /usr/bin/python{}".format(output.decode(), sys.version_info.major)
    container.exec_run(cmd, detach=False, stream=False, user="root")


def setup_sacctmgr(container):
    nodes = "NodeName=c\[1-5\] NodeHostName=localhost NodeAddr=127.0.0.1 RealMemory=1000"
    nodes2 = "NodeName=c\[6-10\] NodeHostName=localhost NodeAddr=127.0.0.1 RealMemory=1000 Gres=gpu:titanxp:1"
    newnodes = "\\n".join([
        "NodeName=c[1-3] NodeHostName=localhost NodeAddr=127.0.0.1 RealMemory=500 Feature=thin,mem500MB",
        "NodeName=c[4-5] NodeHostName=localhost NodeAddr=127.0.0.1 RealMemory=800 Feature=fat,mem800MB",
        "NodeName=c[6-10] NodeHostName=localhost NodeAddr=127.0.0.1 RealMemory=500 Feature=thin,mem500MB"
    ])
    partition = "PartitionName=debug Nodes=c\[6-10\] Priority=50 DefMemPerCPU=500 Shared=NO MaxNodes=5 MaxTime=5-00:00:00 DefaultTime=5-00:00:00 State=UP"
    partition_new = partition.replace("5-00", "05")
    try:
        cmd_args = [
            "/bin/bash -c 'sacctmgr --immediate add cluster name=linux ; ",
            "sed -i -e \"s/{old}/{new}/g\" /etc/slurm/slurm.conf ;".format(old=nodes, new=newnodes),
            "sed -i -e \"s/{old}/#/g\" /etc/slurm/slurm.conf ;".format(old=nodes2),
            "sed -i -e \"s/{old}/{new}/g\" /etc/slurm/slurm.conf ;".format(old=partition, new=partition_new),
            "supervisorctl restart slurmdbd;",
            "supervisorctl restart slurmctld;",
            "sacctmgr --immediate add account none,test Cluster=linux Description=\"none\" Organization=\"none\"'"
        ]
        cmd = " ".join(cmd_args)
        container.exec_run(cmd, detach=False, stream=False, user="root")
    except:
        raise


def get_snakemake_quay_tag():
    import requests
    try:
        r = requests.get(
            "https://quay.io/api/v1/repository/biocontainers/snakemake/tag")
        tags = [t['name'] for t in r.json()['tags']]
    except:
        logger.error("couldn't complete requests for quay.io")
        raise
    r = re.compile(SNAKEMAKE_BASETAG)
    # TODO: verify that tags are sorted by build date; if so we need
    # to verify that they are sorted in descending version order
    for t in tags:
        if r.search(t):
            return t
    logger.error("No valid snakemake tag found")
    sys.exit(1)


def get_snakemake_image():
    images = get_images(SNAKEMAKE_IMAGE, SNAKEMAKE_BASETAG)
    client = docker.from_env()
    if len(images) == 0:
        tag = get_snakemake_quay_tag()
        img = SNAKEMAKE_IMAGE + ":" + str(tag)
        logger.info("pulling image {}".format(img))
        client.images.pull(img)
        images = get_images(SNAKEMAKE_IMAGE, SNAKEMAKE_BASETAG)
    return images[0]


def get_slurm_image():
    images = get_images(SLURM_IMAGE)
    client = docker.from_env()
    if len(images) == 0:
        logger.info("pulling image {}".format(SLURM_IMAGE))
        client.images.pull(SLURM_IMAGE)
        images = get_images(SLURM_IMAGE)
    return images[0]


def get_images(name, tag=None):
    client = docker.from_env()
    images = client.images.list()
    matches = []
    for img in images:
        for repo in img.attrs["RepoDigests"]:
            if repo.startswith(name):
                if tag is not None:
                    if not any(t.startswith("{}:{}".format(name, tag)) for t in img.tags):
                        continue
                matches.append(img)
    return list(set(matches))


def stack_deploy(docker_compose, name=DOCKER_STACK_NAME):
    logger.info("Deploying stack {}".format(name))
    client = docker.from_env()
    res = sp.check_output(shlex.split('docker stack ls'))
    stacks = [s.split(" ")[0] for s in res.decode().split("\n")]
    # Add config variable to disable redeployment
    if name in stacks:
        logger.info("Stack {} already deployed".format(name))
        try:
            container = [c for c in client.containers.list()
                         if c.name.startswith(SLURM_SERVICE)][0]
            res = container.exec_run("scontrol show slurmd")
            if res.output.decode().startswith("scontrol: error:"):
                raise Exception("scontrol error")
        except Exception as e:
            logger.warning("Stack is up but no slurm service available")
            raise e
    else:
        # Implicitly assumes docker swarm init has been run
        sp.check_output(
            shlex.split('docker stack deploy --with-registry-auth -c {} {}'.format(docker_compose, name)))
        # Need to wait for containers to come up
        logger.info("Verifying that stack has been initialized")
        for i in range(STATUS_ATTEMPTS):
            try:
                container = [c for c in client.containers.list()
                             if c.name.startswith(SLURM_SERVICE)][0]
                res = container.exec_run("scontrol show slurmd")
                if res.output.decode().startswith("scontrol: error:"):
                    raise Exception("scontrol error")
                break
            except Exception as e:
                logger.info("Stack inactive; retrying, attempt {}".format(i+1))
                time.sleep(3)
    return container


def stack_rm(name=DOCKER_STACK_NAME):
    logger.info("Finalizing session")
    res = sp.check_output(shlex.split('docker stack ls'))
    stacks = [s.split(" ")[0] for s in res.decode().split("\n")]
    if name in stacks:
        logger.info("Removing docker stack {}".format(name))
        sp.check_output(
            shlex.split('docker stack rm {}'.format(name)))
        logger.info("Pruning docker volumes")
        sp.check_output(
            shlex.split('docker volume prune -f'))
        time.sleep(TIMEOUT)


@pytest.fixture(scope="session")
def slurm():
    return get_slurm_image()


@pytest.fixture(scope="session")
def snakemake():
    return get_snakemake_image()


@pytest.fixture(scope="session")
def docker_compose(slurm, snakemake):
    tag = snakemake.tags[0]
    # Docker compose template for test
    COMPOSE_TEMPLATE = os.path.join(os.path.dirname(__file__),
                                    "docker-compose.yaml")
    with open(COMPOSE_TEMPLATE) as fh:
        TEMPLATE = "".join(fh.readlines())
    COMPOSEFILE = TEMPLATE.format(snakemake_tag=tag)
    return COMPOSEFILE


@pytest.fixture(scope="session")
def data(tmpdir_factory, _cookiecutter_config_file, docker_compose):
    p = tmpdir_factory.mktemp("data")
    compose = p.join("docker-compose.yaml")
    compose.write(docker_compose)
    snakefile = p.join("Snakefile")
    SNAKEFILE.copy(snakefile)
    cluster_config = p.join("cluster-config.yaml")
    CLUSTERCONFIG.copy(cluster_config)
    template = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), os.pardir)
    output_factory = tmpdir_factory.mktemp
    c = Cookies(template, output_factory, _cookiecutter_config_file)
    c._new_output_dir = lambda: str(p.join("slurm"))
    c.bake(extra_context={'partition': 'normal',
                          'output': 'logs/slurm-%j.out',
                          'error': 'logs/slurm-%j.err'})
    # Advanced setting
    c = Cookies(template, output_factory, _cookiecutter_config_file)
    c._new_output_dir = lambda: str(p.join("slurm-advanced"))
    c.bake(extra_context={'partition': 'normal',
                          'output': 'logs/slurm-%j.out',
                          'error': 'logs/slurm-%j.err',
                          'submit_script': 'slurm-submit-advanced.py'})
    return p


@pytest.fixture(scope="session")
def cluster(slurm, snakemake, data):
    container = stack_deploy(str(data.join("docker-compose.yaml")))
    add_slurm_user(pytest.local_user_id, container)
    setup_sacctmgr(container)
    link_python(container)
    # Hack: modify first line in snakemake file
    container.exec_run(["sed", "-i", "-e", "s:/usr:/opt:",
                        "/opt/local/bin/snakemake"])
    return container, data
