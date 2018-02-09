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


### Resources

The following resources are supported by on a per-rule bassis:

**mem** - set the memory resource request in mb.
**walltime**, **runtime** - set the time resource in min.


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
