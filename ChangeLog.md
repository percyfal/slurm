# ChangeLog

## 2022-05-12

### Changes

- add support for sidecar (PR #85)

## 2021-03-10

### Issues

- serialize cookiecutter settings in json file and add CookieCutter
  class to access config (fixes #63)
- demote pandas import to function (addresses #64)
- add preliminary support for suffixes when specifying memory (fixes #62)

## 2020-10-23

This is a major rewrite of the testing framework, in an attempt to
make it more accessible to users. In particular, it is now possible to
run tests on an HPC.

### Changes

- the new ShellContainer class emulates container output and allows
  the tests to be executed on a HPC running SLURM
- slurm-submit.py now submits sbatch jobs with the --parsable option
- add profile option 'cluster\_name' - some HPCs define multiple SLURM
  clusters. Simply adding --cluster=cluster\_name to SBATCH_DEFAULTS
  will not suffice as slurm-status.py also needs to check status in
  the queue corresponding to the chosen cluster.
- the advanced argument conversion has been much simplified and
  improved

### Issues

- options without arguments can now be set in SBATCH_DEFAULTS (fixes #52)


## 2020-09-11

Move CI infrastructure from circleCI to github actions.

## 2020-04-15

- process string patterns in snakemake style (replace keywords in braces)

## 2020-03-31

- map threads to `--cpus-per-task` (#35)
- rewrite some tests to address changes

## 2020-02-29

- major rewrite and merge of the `slurm-submit.py` script to support any sbatch argument
- parse any argument via the `sbatch_defaults` option and
- enable per-profile cluster (YAML/JSON) config file
- make experimental sbatch argument adjustments optional via the `advanced_argument_conversion` option

## 2019-09-03

- add qos option

## 2019-08-21

- replace pytest_namespace with pytest_configure
- make days optional (#18)

## 2018-10-18

- add cookiecutter options to set sbatch output and error defaults

## 2018-10-09

- add support for mem_mb in resources
- add support for cluster configuration file
- add advanced slurm-submit file
- adjust resource requirements if they exceed partition configuration
  settings (#11)
