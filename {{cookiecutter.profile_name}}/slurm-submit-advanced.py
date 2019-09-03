#!/usr/bin/env python3
import sys
import os
import re
import math
import argparse
import subprocess
from snakemake.utils import read_job_properties


##############################
# Helper functions
##############################
def _get_default_partition():
    """Retrieve default partition for cluster"""
    if "{{cookiecutter.partition}}":
        return "{{cookiecutter.partition}}"
    cmd = "sinfo -O \"partition\""
    res = subprocess.run(cmd, check=True, shell=True,
                         stdout=subprocess.PIPE)
    m = re.search("(?P<partition>\S+)\*", res.stdout.decode(), re.M)
    partition = m.group("partition")
    return partition


def _get_cluster_configuration(partition):
    """Retrieve cluster configuration for a partition."""
    # Retrieve partition info; we tacitly assume we only get one response
    cmd = " ".join(
        ["sinfo -e -O \"partition,cpus,memory,time,size,maxcpuspernode\"",
         "-h -p {}".format(partition)])
    res = subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE)
    m = re.search("(?P<partition>\S+)\s+(?P<cpus>\d+)\s+(?P<memory>\S+)\s+((?P<days>\d+)-)?(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+)\s+(?P<size>\S+)\s+(?P<maxcpus>\S+)",
                  res.stdout.decode())
    d = m.groupdict()
    if not 'days' in d or not d['days']:
        d['days'] = 0
    d["time"] = int(d['days']) * 24 * 60 + \
        int(d['hours']) * 60 + int(d['minutes']) + \
        math.ceil(int(d['seconds']) / 60)
    return d


def _get_features_and_memory(partition):
    """Retrieve features and memory for a partition in the cluster
    configuration. """
    cmd = " ".join(
        ["sinfo -e -O \"memory,features_act\"",
         "-h -p {}".format(partition)])
    res = subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE)
    mem_feat = []
    for x in res.stdout.decode().split("\n"):
        if not re.search("^\d+", x):
            continue
        m = re.search("^(?P<mem>\d+)\s+(?P<feat>\S+)", x)
        mem_feat.append({'mem': m.groupdict()["mem"],
                         'features': m.groupdict()["feat"].split(",")})
    return mem_feat


def _get_available_memory(mem_feat, constraints=None):
    """Get available memory

    If constraints are given, parse constraint string into array of
    constraints and compare them to active features. Currently only
    handles comma-separated strings and not the more advanced
    constructs described in the slurm manual.

    Else, the minimum memory for a given partition is returned.

    """
    if constraints is None:
        return min([int(x['mem']) for x in mem_feat])
    try:
        constraint_set = set(constraints.split(","))
        for x in mem_feat:
            if constraint_set.intersection(x["features"]) == constraint_set:
                return int(x["mem"])
    except Exception as e:
        print(e)
        raise


def _update_memory_and_ntasks(arg_dict, MEMORY_PER_CPU, MEMORY_PER_PARTITION):
    """Given a one-node job, update memory and ntasks if the requested
    configuration is unavailable"""
    if arg_dict["mem"] is not None:
        arg_dict["mem"] = min(int(arg_dict["mem"]),
                              MEMORY_PER_PARTITION)
        AVAILABLE_MEM = arg_dict["ntasks"] * MEMORY_PER_CPU
        if arg_dict["mem"] > AVAILABLE_MEM:
            arg_dict["ntasks"] = int(math.ceil(arg_dict["mem"] /
                                               MEMORY_PER_CPU))
    arg_dict["ntasks"] = min(int(config["cpus"]),
                             int(arg_dict["ntasks"]))

##############################
# Main script
##############################
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    "--help", help="Display help message.", action="store_true")
parser.add_argument(
    "positional", action="append",
    nargs="?", metavar="POS",
    help="additional arguments not in slurm parser group to pass to sbatch")

# A subset of SLURM-specific arguments. Note that the parser is used
# implicitly in that the parsed arguments are used to construct a
# dictionary of arguments to be processed. Specific arguments can be
# modified via the cluster configuration file.
slurm_parser = parser.add_argument_group("slurm-specific arguments")
slurm_parser.add_argument(
    "-a", "--array", help="job array index values")
slurm_parser.add_argument(
    "-A", "--account", help="charge job to specified account")
slurm_parser.add_argument(
    "--begin", help="defer job until HH:MM MM/DD/YY")
slurm_parser.add_argument(
    "-c", "--cpus-per-task", help="number of cpus required per task",
    type=int, default=1)
slurm_parser.add_argument(
    "-d", "--dependency",
    help="defer job until condition on jobid is satisfied")
slurm_parser.add_argument(
    "-D", "--workdir", help="set working directory for batch script")
slurm_parser.add_argument(
    "-e", "--error", help="file for batch script's standard error",
    default="{{cookiecutter.error}}" if "{{cookiecutter.error}}" else None)
slurm_parser.add_argument(
    "-J", "--job-name", help="name of job")
slurm_parser.add_argument(
    "--mail-type", help="notify on state change: BEGIN, END, FAIL or ALL")
slurm_parser.add_argument(
    "--mail-user", help="who to send email notification for job state changes")
slurm_parser.add_argument(
    "-n", "--ntasks", help="number of tasks to run", type=int, default=1)
slurm_parser.add_argument(
    "-N", "--nodes", help="number of nodes on which to run (N = min[-max])",
    type=int)
slurm_parser.add_argument(
    "-o", "--output", help="file for batch script's standard output",
    default="{{cookiecutter.output}}" if "{{cookiecutter.output}}" else None)
slurm_parser.add_argument(
    "-p", "--partition", help="partition requested",
    default=_get_default_partition(), type=str)
slurm_parser.add_argument(
    "-q", "--qos", help="quality of service")
slurm_parser.add_argument(
    "-Q", "--quiet", help="quiet mode (suppress informational messages)")
slurm_parser.add_argument(
    "-t", "--time", help="time limit")
slurm_parser.add_argument(
    "--wrap", help="wrap command string in a sh script and submit")
slurm_parser.add_argument(
    "-C", "--constraint", help="specify a list of constraints")
slurm_parser.add_argument(
    "--mem", help="minimum amount of real memory")

opt_keys = ["array", "account", "begin", "cpus_per_task",
            "dependency", "workdir", "error", "job_name", "mail_type",
            "mail_user", "ntasks", "nodes", "output", "partition",
            "quiet", "time", "wrap", "constraint", "mem"]

args = parser.parse_args()

if args.help:
    parser.print_help()
    sys.exit(0)

jobscript = sys.argv[-1]
job_properties = read_job_properties(jobscript)

extras = ""
if args.positional:
    for m in args.positional:
        if m is not None:
            extras = extras + " " + m

arg_dict = dict(args.__dict__)

# Set default account
if arg_dict["account"] is None:
    if "{{cookiecutter.account}}" != "":
        arg_dict["account"] = "{{cookiecutter.account}}"


# Ensure output folder for Slurm log files exist.
# This is a bit hacky; will run for every Slurm submission...
if arg_dict["output"] is not None:
    if not os.path.exists(os.path.dirname(arg_dict["output"])):
        os.makedirs(os.path.dirname(arg_dict["output"]))
if arg_dict["error"] is not None:
    if not os.path.exists(os.path.dirname(arg_dict["error"])):
        os.makedirs(os.path.dirname(arg_dict["error"]))


# Process resources
if "resources" in job_properties:
    resources = job_properties["resources"]
    if arg_dict["time"] is None:
        if "runtime" in resources:
            arg_dict["time"] = resources["runtime"]
        elif "walltime" in resources:
            arg_dict["time"] = resources["walltime"]
    if arg_dict["mem"] is None:
        if "mem" in resources:
            arg_dict["mem"] = resources["mem"]
        elif "mem_mb" in resources:
            arg_dict["mem"] = resources["mem_mb"]

# Threads
if "threads" in job_properties:
    arg_dict["ntasks"] = job_properties["threads"]


# Process cluster configuration. Note that setting time, ntasks, and
# mem will override any setting in resources. It is assumed that the
# cluster configuration parameters are named according to the sbatch
# long options names
cluster_config = job_properties.get("cluster", {})
arg_dict.update(job_properties.get("cluster", {}))

# Determine partition with features. If no constraints have been set,
# select the partition with lowest memory
try:
    part = arg_dict["partition"]
    config = _get_cluster_configuration(part)
    mem_feat = _get_features_and_memory(part)
    MEMORY_PER_PARTITION = _get_available_memory(mem_feat,
                                                 arg_dict["constraint"])
    MEMORY_PER_CPU = MEMORY_PER_PARTITION / int(config["cpus"])
except subprocess.CalledProcessError as e:
    print(e)
    raise e
except Exception as e:
    print(e)
    raise e


# Update time. If requested time is larger than maximum allowed time,
# reset
try:
    if arg_dict["time"] is not None:
        arg_dict["time"] = min(int(config["time"]), int(arg_dict["time"]))
except Exception as e:
    print(e)
    raise e


# Adjust memory in the single-node case only; getting the
# functionality right for multi-node multi-cpu jobs requires more
# development
if arg_dict["nodes"] is None or int(arg_dict["nodes"]) == 1:
    _update_memory_and_ntasks(arg_dict, MEMORY_PER_CPU,
                              MEMORY_PER_PARTITION)
else:
    if int(arg_dict["ntasks"]) == 1:
        # Allocate at least as many tasks as requested nodes
        arg_dict["ntasks"] = int(arg_dict["nodes"])


opts = ""
for k, v in arg_dict.items():
    if k not in opt_keys:
        continue
    if v is not None:
        opts += " --{} \"{}\" ".format(k.replace("_", "-"), v)

if arg_dict["wrap"] is not None:
    cmd = "sbatch {opts}".format(opts=opts)
else:
    cmd = "sbatch {opts} {extras}".format(opts=opts, extras=extras)

try:
    res = subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE)
except subprocess.CalledProcessError as e:
    raise e

# Get jobid
res = res.stdout.decode()
try:
    m = re.search("Submitted batch job (\d+)", res)
    jobid = m.group(1)
    print(jobid)
except Exception as e:
    print(e)
    raise

