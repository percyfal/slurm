[![CircleCI](https://circleci.com/gh/percyfal/slurm.svg?style=svg)](https://circleci.com/gh/percyfal/slurm)

# slurm

This profile configures Snakemake to run on the [SLURM Workload Manager](https://slurm.schedmd.com/)

## Setup

### Deploy profile

To deploy this profile, run

	mkdir -p ~/.config/snakemake
	cd ~/.config/snakemake
	cookiecutter https://github.com/Snakemake-Profiles/slurm.git

Then, you can run Snakemake with

	snakemake --profile slurm ...

### Cookiecutter options

* `profile_name` : A name to address the profile via the `--profile` Snakemake option.
* `sbatch_defaults` : List of default arguments to sbatch, e.g.: `qos=short time=60`.
  This is a convenience argument to avoid `cluster_config` for a few aruments.
* `cluster_config` : Path to a YAML or JSON configuration file analogues to the
  Snakemake [`--cluster-config` option](https://snakemake.readthedocs.io/en/stable/snakefiles/configuration.html#cluster-configuration-deprecated).
  Path may relative to the profile directory or absolute including environment variables
  (e.g. `$PROJECT_ROOT/config/slurm_defaults.yaml`).
* `advanced_argument_conversion` : If True, try to adjust/constrain mem, time, nodes and ntasks (i.e. cpus) to
  parsed or default partition after converting resources. This may fail due to heterogeneous slurm setups,
  i.e. code adjustments will likely be necessary.

### Default snakemake arguments
Default arguments to ``snakemake`` maybe adjusted in the ``<profile path>/config.yaml`` file.


## Parsing arguments to SLURM (sbatch)
Arguments are overridden in the following order and must be named according to
[sbatch long option names](https://slurm.schedmd.com/sbatch.html):

1) `sbatch_defaults` cookiecutter option
2) Profile `cluster_config` file `__default__` entries
3) Snakefile threads and resources (time, mem)
4) Profile `cluster_config` file <rulename> entries
5) `--cluster-config` parsed to Snakemake (deprecated since Snakemake 5.10)
6) Any other argument conversion (experimental, currently time, ntasks and mem) if `advanced_argument_conversion` is True.

## Resources
Resources specified in Snakefiles must all be in the correct unit/format as expected by `sbatch`.
The implemented resource names are given (and may be adjusted) in the `slurm_utils.RESOURCE_MAPPING` global.
This is intended for system agnostic resources such as time and memory.

## Cluster configuration file
The profile supports setting default and per-rule options in either the `cluster_config` file and
the [`--cluster-config` file parsed to snakemake](https://snakemake.readthedocs.io/en/stable/snakefiles/configuration.html#cluster-configuration-deprecated)
(the latter is deprecated since snakemake 5.10). The `__default__` entry will apply to all jobs. Both may be YAML (see example
below) or JSON files.

```yaml
__default__:
  account: staff
  mail-user: slurm@johndoe.com
  
large_memory_requirement_job:
  constraint: mem2000MB
  ntasks: 16
```


## Tests
Test-driven development is enabled through the tests folder. Provided
that the user has installed docker and enabled [docker
swarm](https://docs.docker.com/engine/swarm/) (`docker swarm init`), the SLURM tests will
download two images:

1. [quay.io/biocontainers/snakemake](https://quay.io/repository/biocontainers/snakemake?tab=tags)
2. [giovtorres/docker-centos7-slurm](https://github.com/giovtorres/docker-centos7-slurm)

and testing of the cookiecutter template itself is enabled
through the [pytest plugin for
Cookiecutters](https://github.com/hackebrot/pytest-cookies). You can
run the tests by issuing

	pytest -v -s


## ChangeLog

### 2020-04-15

- process string patterns in snakemake style (replace keywords in braces)

### 2020-03-31

- map threads to `--cpus-per-task` (#35)
- rewrite some tests to address changes

### 2020-02-29

- major rewrite and merge of the `slurm-submit.py` script to support any sbatch argument
- parse any argument via the `sbatch_defaults` option and
- enable per-profile cluster (YAML/JSON) config file
- make experimental sbatch argument adjustments optional via the `advanced_argument_conversion` option

### 2019-09-03

- add qos option

### 2019-08-21

- replace pytest_namespace with pytest_configure
- make days optional (#18)

### 2018-10-18

- add cookiecutter options to set sbatch output and error defaults

### 2018-10-09

- add support for mem_mb in resources
- add support for cluster configuration file
- add advanced slurm-submit file
- adjust resource requirements if they exceed partition configuration
  settings (#11)
