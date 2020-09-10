# ChangeLog

## 2020-09-10

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
