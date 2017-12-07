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
from pytest_cookies import Cookies

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
SNAKEFILE = py.path.local(os.path.join(os.path.dirname(__file__), "Snakefile"))


def pytest_namespace():
    return {
        'local_user_id': LOCAL_USER_ID,
        'snakemake_cmd': " ".join(
            ["export PATH=\"$SNAKEMAKE_PATH:$PATH\"",
             " && snakemake ", "-d {workdir} ",
             " -s {snakefile} "]),
        'path': "export PATH=\"$SNAKEMAKE_PATH:$PATH\"",
        'template': ROOT_DIR,
    }


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


def get_snakemake_quay_tag():
    import requests
    try:
        r = requests.get(
            "https://quay.io/api/v1/repository/biocontainers/snakemake/tag")
        tags = [t['name'] for t in r.json()['tags']]
    except:
        logger.error("couldn't complete requests for quay.io")
        raise
    r = re.compile("{}--{}".format(SNAKEMAKE_BASETAG, PYTHON_VERSION))
    # TODO: verify that tags are sorted by build date; if so we need
    # to verify that they are sorted in descending version order
    for t in tags:
        if r.search(t):
            return t
    logger.error("No valid snakemake tag found")
    sys.exit(1)


def get_snakemake_image():
    images = get_images(SNAKEMAKE_IMAGE)
    client = docker.from_env()
    if len(images) == 0:
        tag = get_snakemake_quay_tag()
        img = SNAKEMAKE_IMAGE + ":" + str(tag)
        logger.info("pulling image {}".format(img))
        client.images.pull(img)
        images = get_images(SNAKEMAKE_IMAGE)
    return images[0]


def get_slurm_image():
    images = get_images(SLURM_IMAGE)
    client = docker.from_env()
    if len(images) == 0:
        logger.info("pulling image {}".format(SLURM_IMAGE))
        client.images.pull(SLURM_IMAGE)
        images = get_images(SLURM_IMAGE)
    return images[0]


def get_images(name):
    client = docker.from_env()
    images = client.images.list()
    matches = []
    for img in images:
        for repo in img.attrs["RepoDigests"]:
            if repo.startswith(name):
                matches.append(img)
    return list(set(matches))


def stack_deploy(docker_compose, name=DOCKER_STACK_NAME):
    logger.info("Deploying stack {}".format(name))
    res = sp.check_output(shlex.split('docker stack ls'))
    stacks = [s.split(" ")[0] for s in res.decode().split("\n")]
    # Add config variable to disable redeployment
    if name in stacks:
        logger.info("Stack {} already deployed".format(name))
    else:
        # Implicitly assumes docker swarm init has been run
        sp.check_output(
            shlex.split('docker stack deploy --with-registry-auth -c {} {}'.format(docker_compose, name)))
        # Need to wait for containers to come up
        logger.info("Sleeping {} seconds to let containers launch".format(TIMEOUT))
        time.sleep(TIMEOUT)


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
    print(tag)
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
    template = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), os.pardir)
    output_factory = tmpdir_factory.mktemp
    c = Cookies(template, output_factory, _cookiecutter_config_file)
    c._new_output_dir = lambda: str(p)
    cc = c.bake()
    return p


@pytest.fixture(scope="session")
def cluster(slurm, snakemake, data):
    client = docker.from_env()
    stack_deploy(str(data.join("docker-compose.yaml")))
    container = [c for c in client.containers.list()
                 if c.name.startswith(SLURM_SERVICE)][0]
    add_slurm_user(pytest.local_user_id, container)
    # Hack: modify first line in snakemake file
    container.exec_run(["sed", "-i", "-e", "s:/usr:/opt:",
                        "/opt/local/bin/snakemake"])
    return container, data
