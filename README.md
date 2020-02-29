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

### Cookiecutter arguments

* `profile_name` : A name to address the profile via the `--profile` Snakemake option.
* `sbatch_defaults` : List of default arguments to sbatch, e.g.: `qos=short time=60`.
  This is a convenience argument to avoid `default_cluster_config` for a few aruments.
* `default_cluster_config` : Path to a YAML or JSON configuration file analogues to the
  Snakemake [`--cluster-config` argument](https://snakemake.readthedocs.io/en/stable/snakefiles/configuration.html#cluster-configuration-deprecated). Path may relative to the profile directory or
  absolute including environment variables
  (e.g. `$PROJECT_ROOT/config/slurm_defaults.yaml`).

### Default snakemake arguments
Default arguments to ``snakemake`` maybe adjusted in the ``<profile path>/config.yaml`` file.


## Parsing arguments to SLURM (sbatch)
Arguments are overridden in the following order:

1) `sbatch_defaults`
2) `default_cluster_config` __default__
3) Snakefile threads and resources (time, mem)
4) `default_cluster_config` <jobname>
5) `--cluster-config` parsed to Snakemake (deprecated since Snakemake 5.10)


## Resources
The following resources are parsed from Snakefiles:

- **mem**, **mem_mb**: set the memory resource request in mb.
- **walltime**, **runtime**: set the time resource in min.

### Cluster configuration file

As of 2018-10-08, the profile supports setting options in the cluster
configuration file. The options must be named according to [sbatch
long option names](https://slurm.schedmd.com/sbatch.html). Note that
setting memory or time will override resources specified by rules.
Therefore, setting time or memory in the `__default__` section will
effectively override all resource specifications that set these
parameters.

As an example, you can specify constraints in the cluster
configuration file:

```yaml
__default__:
  constraint: mem500MB
  
large_memory_requirement_job:
  constraint: mem2000MB
```


## Tests

Test-driven development is enabled through the tests folder. Provided
that the user has installed docker and enabled [docker
swarm](https://docs.docker.com/engine/swarm/), the SLURM tests will
download two images:

1. [quay.io/biocontainers/snakemake](https://quay.io/repository/biocontainers/snakemake?tab=tags)
2. [giovtorres/docker-centos7-slurm](https://github.com/giovtorres/docker-centos7-slurm)

In addition, testing of the cookiecutter template itself is enabled
through the [pytest plugin for
Cookiecutters](https://github.com/hackebrot/pytest-cookies). You can
run the tests by issuing

	pytest -v -s


## ChangeLog

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
