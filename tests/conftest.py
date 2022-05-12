#!/usr/bin/env python3
import os
from os.path import join as pjoin
import re
import py
import pytest
import docker
from docker.models.containers import Container
import shutil
import logging
from pytest_cookies.plugin import Cookies
from wrapper import SnakemakeRunner, ShellContainer


def pytest_addoption(parser):
    group = parser.getgroup("slurm")
    group.addoption(
        "--partition",
        action="store",
        default="normal",
        help="partition to run tests on",
    )
    group.addoption("--account", action="store", default=None, help="slurm account")
    group.addoption(
        "--slow", action="store_true", help="include slow tests", default=False
    )
    group.addoption("--cluster", action="store", default=None, help="slurm cluster")


def pytest_configure(config):
    pytest.local_user_id = os.getuid()
    pytest.dname = os.path.dirname(__file__)
    pytest.cookie_template = py.path.local(pytest.dname).join(os.pardir)
    config.addinivalue_line("markers", "slow: mark tests as slow")
    config.addinivalue_line("markers", "docker: mark tests as docker tests only")
    config.addinivalue_line("markers", "sbatch: mark tests as sbatch shell tests only")
    config.addinivalue_line("markers", "skipci: skip tests on ci")
    setup_logging(config.getoption("--log-level"))
    pytest.partition = config.getoption("--partition")
    pytest.account = ""
    if config.getoption("--account"):
        pytest.account = "--account={}".format(config.getoption("--account"))
    pytest.cluster = config.getoption("--cluster")
    if shutil.which("sbatch") is not None and config.getoption("--basetemp") is None:
        config.option.basetemp = "./.pytest"


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
def datadir(tmpdir_factory):
    """Setup base data directory for a test"""
    p = tmpdir_factory.mktemp("data")
    return p


@pytest.fixture
def datafile(datadir):
    """Add a datafile to the datadir.

    By default, look for a source (src) input file located in the
    tests directory (pytest.dname). Custom data can be added by
    pointing a file 'dname / src'. The contents of src are copied to
    the file 'dst' in the test data directory

    Args:
      src (str): source file name
      dst (str): destination file name. Defaults to src.
      dname (str): directory where src is located.

    """

    def _datafile(src, dst=None, dname=pytest.dname):
        dst = src if dst is None else dst
        src = py.path.local(pjoin(dname, src))
        dst = datadir.join(dst)
        src.copy(dst)
        return dst

    return _datafile


@pytest.fixture
def cookie_factory(tmpdir_factory, _cookiecutter_config_file, datadir):
    """Cookie factory fixture.

    Cookie factory fixture to create a slurm profile in the test data
    directory.

    Args:
      sbatch_defaults (str): sbatch defaults for cookie
      advanced (str): use advanced argument conversion ("no" or "yes")
      cluster_sidecar (str): use sidecar to monitor job status
      cluster_name (str): set cluster name
      cluster_config (str): cluster configuration file
      yamlconfig (dict): dictionary of snakemake options with values

    """

    logging.getLogger("cookiecutter").setLevel(logging.INFO)
    _sbatch_defaults = (
        f"--partition={pytest.partition} {pytest.account} "
        "--output=logs/slurm-%j.out --error=logs/slurm-%j.err"
    )
    _yamlconfig_default = {
        'restart-times': 1
    }

    def _cookie_factory(
        sbatch_defaults=_sbatch_defaults,
        advanced="no",
        cluster_sidecar="yes",
        cluster_name=None,
        cluster_config=None,
        yamlconfig=_yamlconfig_default,
    ):
        cookie_template = pjoin(os.path.abspath(pytest.dname), os.pardir)
        output_factory = tmpdir_factory.mktemp
        c = Cookies(cookie_template, output_factory, _cookiecutter_config_file)
        c._new_output_dir = lambda: str(datadir)
        extra_context = {
            "sbatch_defaults": sbatch_defaults,
            "advanced_argument_conversion": advanced,
            "cluster_sidecar": cluster_sidecar,
        }
        if cluster_name is not None:
            extra_context["cluster_name"] = cluster_name
        if cluster_config is not None:
            extra_context["cluster_config"] = cluster_config
        c.bake(extra_context=extra_context)
        config = datadir.join("slurm").join("config.yaml")
        config_d = dict(
            [tuple(line.split(":")) for line in config.read().split("\n") if re.search("^[a-z]", line)]
        )
        config_d.update(**yamlconfig)
        config.write("\n".join(f"{k}: {v}" for k, v in config_d.items()))
    return _cookie_factory


@pytest.fixture
def data(tmpdir_factory, request, datafile):
    """Setup base data consisting of a Snakefile and cluster configuration file"""
    datafile("Snakefile")
    ccfile = datafile("cluster-config.yaml")
    return py.path.local(ccfile.dirname)


@pytest.fixture(scope="session")
def slurm(request):
    """Slurm fixture

    Return relevant container depending on environment. First look for
    sbatch command to determine whether we are on a system running the
    SLURM scheduler. Second, try deploying a docker stack to run slurm
    locally.

    Skip slurm tests if the above actions fail.

    """
    if shutil.which("sbatch") is not None:
        return ShellContainer()
    else:
        client = docker.from_env()
        container_list = client.containers.list(
            filters={"name": "cookiecutter-slurm_slurm"}
        )
        container = container_list[0] if len(container_list) > 0 else None
        if container:
            return container

    msg = (
        "no sbatch or docker stack 'cookiecutter-slurm' running;"
        " skipping slurm-based tests."
        " Either run tests on a slurm HPC or deploy a docker stack with"
        f" {os.path.dirname(__file__)}/deploystack.sh"
    )

    pytest.skip(msg)


def teardown(request):
    """Shutdown snakemake processes that are waiting for slurm

    On nsf systems, stale snakemake log files may linger in the test
    directory, which prevents reruns of pytest. The teardown function
    calls 'lsof' to identify and terminate the processes using these
    files.

    """

    logging.info(f"\n\nTearing down test '{request.node.name}'")
    basetemp = request.config.getoption("basetemp")
    from subprocess import Popen, PIPE
    import psutil

    for root, _, files in os.walk(basetemp, topdown=False):
        for name in files:
            if not root.endswith(".snakemake/log"):
                continue
            try:
                fn = os.path.join(root, name)
                proc = Popen(["lsof", "-F", "p", fn], stdout=PIPE, stderr=PIPE)
                pid = proc.communicate()[0].decode().strip().strip("p")
                if pid:
                    p = psutil.Process(int(pid))
                    logging.info(f"Killing process {p.pid} related to {fn}")
                    p.kill()
            except psutil.NoSuchProcess as e:
                logging.warning(e)
            except ValueError as e:
                logging.warning(e)


@pytest.fixture
def smk_runner(slurm, datadir, request):
    """smk_runner fixture

    Setup a wrapper.SnakemakeRunner instance that runs the snakemake
    tests. Skip tests where the partition doesn't exist on the system.
    Some tests also only run in docker.

    """

    _, partitions = slurm.exec_run('sinfo -h -o "%P"', stream=False)
    plist = [p.strip("*") for p in partitions.decode().split("\n") if p != ""]
    markers = [m.name for m in request.node.iter_markers()]
    slow = request.config.getoption("--slow")

    if pytest.partition not in plist:
        plist = ",".join(plist)
        pytest.skip(
            (
                f"partition '{pytest.partition}' not in cluster partitions '{plist}';"
                " use the --partition option"
            )
        )

    if isinstance(slurm, ShellContainer):
        if "docker" in markers:
            pytest.skip(f"'{request.node.name}' only runs in docker container")
        if pytest.account == "":
            pytest.skip(
                "HPC slurm tests require setting the account; use the --account option"
            )

    if isinstance(slurm, Container):
        if "sbatch" in markers:
            pytest.skip(f"'{request.node.name}' only runs with sbatch in shell")

    if not slow and "slow" in markers:
        pytest.skip(f"'{request.node.name}' is a slow test; activate with --slow flag")

    if os.getenv("CI") is not None and "skipci" in markers:
        pytest.skip(f"skip '{request.node.name}' on CI; test fails on CI only")

    yield SnakemakeRunner(slurm, datadir, request.node.name, pytest.partition)

    if isinstance(slurm, ShellContainer):
        teardown(request)
