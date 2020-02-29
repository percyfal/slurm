#!/usr/bin/env python3
import os
import re
import math
import argparse
import subprocess

from snakemake import io


SBATCH_DEFAULTS = "qos=priority" #"""{{cookiecutter.default_arguments}}"""
DEFAULT_CLUSTER_CONFIG = os.path.expandvars("{{cookiecutter.default_cluster_config}}")
DEFAULT_CLUSTER_CONFIG = os.path.expandvars("$PROJECT_ROOT/slurm_config.yaml")

RESOURCE_MAPPING = {
        "time": ("time", "runtime", "walltime"),
        "mem": ("mem", "mem_mb", "ram", "memory"),
        "mem_per_cpu": ("mem_per_cpu", "mem_per_thread"),
    }


def parse_jobscript():
    """Minimal CLI to require/only accept single positional argument."""
    p = argparse.ArgumentParser(description="SLURM snakemake submit script")
    p.add_argument("jobscript", help="Snakemake jobscript with job properties.")
    return p.parse_args().jobscript


def sbatch_defaults():
    """Unpack SBATCH_DEFAULTS."""
    d = SBATCH_DEFAULTS.split() if type(SBATCH_DEFAULTS) else SBATCH_DEFAULTS
    args = {k.strip().strip('-'): v.strip() for k, v in [a.split("=") for a in d]}
    return args


def load_default_cluster_config():
    """Load config to dict either from absolute path or relative to profile dir."""
    if DEFAULT_CLUSTER_CONFIG and not DEFAULT_CLUSTER_CONFIG.startswith("{{"):
        path = os.path.join(os.path.dirname(__file__), DEFAULT_CLUSTER_CONFIG)
        dcc = io.load_configfile(path)
    else:
        dcc = {}
    if "__default__" not in dcc:
        dcc["__default__"] = {}
    return dcc


def convert_job_properties(job_properties):
    options = {}
    resources = job_properties.get("resources", {})
    for k, v in RESOURCE_MAPPING.items():
        options.update({k: resources[i] for i in v if i in resources})

    if "threads" in job_properties:
        options["ntasks"] = job_properties["threads"]
    return options


def ensure_dirs_exist(path):
    """Ensure output folder for Slurm log files exist."""
    di = os.path.dirname(path)
    if not os.path.exists(di):
        os.makedirs(di, exist_ok=True)
    return


def submit_job(jobscript, **sbatch_options):
    """Submit jobscript and return jobid."""
    optsbatch_options = [f"--{k}={v}" for k, v in sbatch_options.items()]
    try:
        res = subprocess.check_output(["sbatch"] + optsbatch_options + [jobscript])
    except subprocess.CalledProcessError as e:
        raise e
    # Get jobid
    res = res.decode()
    try:
        jobid = re.search(r"Submitted batch job (\d+)", res).group(1)
    except Exception as e:
        raise e
    return jobid
