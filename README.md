![Test SnakemakeProfiles/slurm](https://github.com/Snakemake-Profiles/slurm/workflows/Test%20SnakemakeProfiles/slurm/badge.svg)

# slurm

This cookiecutter provides a template Snakemake profile for
configuring Snakemake to run on the [SLURM Workload
Manager](https://slurm.schedmd.com/). The profile defines three
scripts

1. `slurm-submit.py` - submits a jobscript to slurm
2. `slurm-jobscript.sh` - a template jobscript
3. `slurm-status.py` - checks the status of jobs in slurm

and a configuration file `config.yaml` that defines default values for
snakemake command line arguments. The default `config.yaml` file is

    restart-times: 3
    jobscript: "slurm-jobscript.sh"
    cluster: "slurm-submit.py"
    cluster-status: "slurm-status.py"
    max-jobs-per-second: 1
    max-status-checks-per-second: 10
    local-cores: 1
    latency-wait: 60

Given an installed profile `profile_name`, when snakemake is run with
`--profile profile_name`, the configuration above would imply the
following snakemake call:

    snakemake --jobscript slurm-jobscript.sh --cluster slurm-submit.py --cluster-status slurm-status.py --restart-times 3 --max-jobs-per-second 1 --max-status-checks-per-second 10 --local-cores 1 --latency-wait 60

plus any additional options to snakemake that the user has applied.

Note that the use of option `--cluster-config` is discouraged, but the
profile still provides support for backwards compatibility. The
default configuration file therefore contains a commented section with
examples of resource configuration (see also [snakemake best
practices](https://snakemake.readthedocs.io/en/stable/snakefiles/best_practices.html?highlight=set-resources#best-practices)):

    # Example resource configuration
    # default-resources:
    #   - runtime=100
    #   - mem_mb=6000
    #   - disk_mb=1000000
    # # set-threads: map rule names to threads
    # set-threads:
    #   - single_core_rule=1
    #   - multi_core_rule=10
    # # set-resources: map rule names to resources in general
    # set-resources:
    #   - high_memory_rule:mem_mb=12000
    #   - long_running_rule:runtime=1200

See the [snakemake documentation on
profiles](https://snakemake.readthedocs.io/en/stable/executing/cli.html?highlight=profile#profiles)
for more information.

## Alternatives

For a more light-weight alternative, see the excellent repo
[smk-simple-slurm](https://github.com/jdblischak/smk-simple-slurm) by
@jdblischak. In particular, it can handle larger amounts of jobs than this profile (see
[issue
#79](https://github.com/Snakemake-Profiles/slurm/issues/79)).


## Quickstart

To create a slurm profile from the cookiecutter, simply run

    cookiecutter https://github.com/Snakemake-Profiles/slurm.git

in a directory. You will be prompted to set some values for your
profile (here assumed to be called `profile_name`), after which the
profile scripts and configuration file will be installed in the
current working directory as `./profile_name`. Then you can run
Snakemake with

    snakemake --profile profile_name ...

Note that the `--profile` argument can be either a relative or
absolute path. In addition, snakemake will search for a corresponding
folder `profile_name` in `/etc/xdg/snakemake` and
`$HOME/.config/snakemake`, where globally accessible profiles can be
placed.

## Examples

### Example 1: project setup to use specific slurm account

One typical use case is to setup a profile to use a specific slurm
account:

    $ cd ~ && mkdir -p my_project && cd my_project
    $ cookiecutter https://github.com/Snakemake-Profiles/slurm.git
    profile_name [slurm]: slurm.my_account
    sbatch_defaults []: account=my_account no-requeue exclusive
    Select advanced_argument_conversion:
    1 - no
    2 - yes
    Choose from 1, 2 [1]:
    cluster_name []:
    cluster_config_help: [The use of cluster-config is discouraged. Rather, set snakemake CLI options in the profile configuration file (see snakemake documentation on best practices). Enter to continue...]
    cluster_config []:


The command `snakemake --profile slurm.convert_args ...` will submit
jobs with `sbatch --parsable --account=my_account --no-requeue
--exclusive`. Note that the option `--parsable` is always added.

### Example 2: project setup using a specified cluster

It is possible to install multiple profiles in a project directory.
Assuming our HPC defines a [multi-cluster
environment](https://slurm.schedmd.com/multi_cluster.html), we can
create a profile that uses a specified cluster:

    $ cookiecutter slurm
    profile_name [slurm]: slurm.dusk
    sbatch_defaults []: account=my_account
    Select advanced_argument_conversion:
    1 - no
    2 - yes
    Choose from 1, 2 [1]:
    cluster_name []: dusk
    cluster_config_help: [The use of cluster-config is discouraged. Rather, set snakemake CLI options in the profile configuration file (see snakemake documentation on best practices). Enter to continue...]
    cluster_config []:


(Note that once a cookiecutter has been installed, we can reuse it
without using the github URL).

The command `snakemake --profile slurm.dusk ...` will now submit jobs
with `sbatch --parsable --account=my_account --cluster=dusk`. In
addition, the `slurm-status.py` script will check for jobs in the
`dusk` cluster job queue.

### Example 3: project setup using advanced argument conversion (WARNING: experimental feature!)

As a final example, assume we want to use advanced argument
conversion:

    $ cookiecutter slurm
    profile_name [slurm]: slurm.convert_args
    sbatch_defaults []: account=my_account
    Select advanced_argument_conversion:
    1 - no
    2 - yes
    Choose from 1, 2 [1]: 2
    cluster_name []:
    cluster_config_help: [The use of cluster-config is discouraged. Rather, set snakemake CLI options in the profile configuration file (see snakemake documentation on best practices). Enter to continue...]
    cluster_config []:

The command `snakemake --profile slurm.convert_args ...` will now
submit jobs with `sbatch --parsable --account=my_account`. The
advanced argument conversion feature will attempt to adjust memory
settings and number of cpus to comply with the cluster configuration.
See the section below

## Profile details

### Cookiecutter options

* `profile_name` : A name to address the profile via the `--profile`
  Snakemake option.
* `sbatch_defaults` : List of default arguments to sbatch, e.g.:
  `qos=short time=60`.
* `advanced_argument_conversion` : If True, try to adjust/constrain
  mem, time, nodes and ntasks (i.e. cpus) to parsed or default
  partition after converting resources. This may fail due to
  heterogeneous slurm setups, i.e. code adjustments will likely be
  necessary.
* `cluster_name` : some HPCs define multiple SLURM clusters. Set the
  cluster name, leave empty to use the default. This will add the
  `--cluster` string to the sbatch defaults, and adjust
  `slurm-status.py` to check status on the relevant cluster.
* `cluster_config` (NB: discouraged): Path to a YAML or JSON configuration file
  analogues to the Snakemake [`--cluster-config`
  option](https://snakemake.readthedocs.io/en/stable/snakefiles/configuration.html#cluster-configuration-deprecated).
  Path may be relative to the profile directory or absolute including
  environment variables (e.g.
  `$PROJECT_ROOT/config/slurm_defaults.yaml`).


### Default snakemake arguments
Default arguments to `snakemake` may be adjusted in the `<profile
path>/config.yaml` file.

### Parsing arguments to SLURM (sbatch) and resource configuration

NB!!! As previusly pointed out, the use of cluster-config is
discouraged. Rule specific resource configuration is better handled by
snakemake's CLI arguments (see [snakemake best
practices](https://snakemake.readthedocs.io/en/stable/snakefiles/best_practices.html?highlight=set-resources#best-practices))
which can be put in the profile configuration file.

Arguments are set and overridden in the following order and must be
named according to [sbatch long option
names](https://slurm.schedmd.com/sbatch.html):

1) `sbatch_defaults` cookiecutter option
2) Profile `cluster_config` file `__default__` entries
3) Snakefile threads and resources (time, mem)
4) Profile `cluster_config` file <rulename> entries
5) `--cluster-config` parsed to Snakemake (deprecated since Snakemake 5.10)
6) Snakemake CLI resource configuration in profile configuration file
7) Any other argument conversion (experimental, currently time, ntasks and mem) if `advanced_argument_conversion` is True.

### Rule specific resource configuration
In addition to Snakemake CLI resource configuration, resources can be
specified in Snakefile rules and must all be in the correct
unit/format as expected by `sbatch`. The implemented resource names
are given (and may be adjusted) in the `slurm_utils.RESOURCE_MAPPING`
global. This is intended for system agnostic resources such as time
and memory. Currently supported resources are `time`, `mem`,
`mem-per-cpu`, `nodes`, and `partition`. An example rule resources
configuration follows:

    rule bwa_mem:
        resources:
            time = "00:10:00",
            mem = 12000,
            partition = "debug"


### Advanced argument conversion (EXPERIMENTAL)
By default, Snakefile resources are provided as-is to the sbatch
submission step. Although `sbatch` does adjust options to match
cluster configuration, it will throw an error if resources exceed
available cluster resources. For instance, if the memory is set larger
than the maximum memory of any node, `sbatch` will exit with the
message

    sbatch: error: CPU count per node can not be satisfied
    sbatch: error: Batch job submission failed: Requested node configuration is not available

By choosing the advanced argument conversion upon creating a profile,
an attempt will be made to adjust memory, cpu and time settings if
these do not comply with the cluster configuration. As an example,
consider a rule with the following resources and threads:

    rule bwa_mem:
        resources:
            mem_mb = lambda wildcards, attempt: attempt * 8000,
            runtime = lambda wildcards, attempt: attempt * 1200
        threads: 1

Assume further that the available cores provide 6400MB memory per
core. If the job reaches a peak memory (8000MB), it will likely be
terminated. The advanced argument conversion will compare the
requested memory requirements to those available (defined as memory
per cpu times number of requested cpus) and adjust the number of cpus
accordingly.

Other checks are also performed to make sure memory, runtime, and
number of cpus don't exceed the maximum values specificed by the
cluster configuration.


### Cluster configuration file

Although [cluster configuration has been officially
deprecated](https://snakemake.readthedocs.io/en/stable/snakefiles/configuration.html#cluster-configuration-deprecated)
in favor of profiles since snakemake 5.10, the `--cluster-config`
option can still be used to configure default and per-rule options.
Upon creating a slurm profile, the user will be prompted for the
location of a cluster configuration file, which is a YAML or JSON file
(see example below).

```yaml
__default__:
  account: staff
  mail-user: slurm@johndoe.com

large_memory_requirement_job:
  constraint: mem2000MB
  ntasks: 16
```

The `__default__` entry will apply to all jobs.


## Tests

Tests can be run on a HPC running SLURM or locally in a
docker stack. To execute tests, run

    pytest -v -s tests

from the source code root directory. Test options can be configured
via the pytest configuration file `tests/pytest.ini`.

Test dependencies are listed in `test-environment.yml` and can be
installed in e.g. a conda environment.

### Testing on a HPC running SLURM

Test fixtures are setup in [temporary directories created by
pytest](https://docs.pytest.org/en/stable/tmpdir.html). Usually
fixtures end up in /tmp/pytest-of-user or something similar. In any
case, these directories are usually not accessible on the nodes where
the tests are run. Therefore, when running tests on a HPC running
SLURM, by default tests fixtures will be written to the directory
`.pytest` relative to the current working directory (which should be
the source code root!). You can change the location with the `pytest`
option `--basetemp`.


### Testing on machine without SLURM

For local testing the test suite will deploy a docker stack
`cookiecutter-slurm` that runs two services based on the following
images:

1. [quay.io/biocontainers/snakemake](https://quay.io/repository/biocontainers/snakemake?tab=tags)
2. [giovtorres/docker-centos7-slurm](https://github.com/giovtorres/docker-centos7-slurm)

The docker stack will be automatically deployed provided that the user
has installed docker and enabled [docker
swarm](https://docs.docker.com/engine/swarm/) (`docker swarm init`).
The docker stack can also be deployed manually from the top-level
directory as follows:

    DOCKER_COMPOSE=tests/docker-compose.yaml ./tests/deploystack.sh

See the deployment script `tests/deploystack.sh` for details.

### Baking cookies

Testing of the cookiecutter template is enabled through the
[pytest plugin for
Cookiecutters](https://github.com/hackebrot/pytest-cookies).


### Anatomy of the tests (WIP)

The slurm tests all depend on fixtures and fixture factories defined
in `tests/conftest.py` to function properly. The `cookie_factory`
fixture factory generates slurm profiles, and the `data` fixture
copies the files `tests/Snakefile` and `tests/cluster-config.yaml` to
the test directory. There is also a `datafile` fixture factory that
copies any user-provided data file to the test directory. Finally, the
`smk_runner` fixture provides an instance of the
`tests/wrapper.SnakemakeRunner` class for running Snakemake tests.

As an example, `tests/test_slurm_advanced.py` defines a fixture
`profile` that uses the `cookie_factory` fixture factory to create an
slurm profile that uses advanced argument conversion:

    @pytest.fixture
    def profile(cookie_factory, data):
        cookie_factory(advanced="yes")

The test `tests/test_slurm_advanced.py::test_adjust_runtime` depends
on this fixture and `smk_runner`:

    def test_adjust_runtime(smk_runner, profile):
        smk_runner.make_target(
            "timeout.txt", options=f"--cluster-config {smk_runner.cluster_config}"
        )


The `make_target` method makes a snakemake target with additional
options passed to Snakemake.

### Adding new tests (WIP)

See `tests/test_issues.py` and `tests/Snakefile_issue49` for an
example of how to write a test with a custom Snakefile.
