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


### Submission scripts

There are two submission scripts that configure jobs for job
submission. `slurm-submit.py`, the default, will use the supplied
parameters untouched, making no attempt to modify the job submission
to comply with the cluster partition configuration. On the other hand,
`slurm-submit-advanced.py` will attempt to modify memory, time and
number of tasks if these exceed the limits specified by the slurm
configuration. If possible, the number of tasks will be increased if
the requested memory is larger than the available memory, defined as
the requested number of tasks times memory per cpu unit.

### Resources

The following resources are supported by on a per-rule basis:

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
