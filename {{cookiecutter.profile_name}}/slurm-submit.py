#!/usr/bin/env python
"""
Snakemake SLURM submit script.
"""
import warnings

from snakemake.utils import read_job_properties

import slurm_utils


# parse job
jobscript = slurm_utils.parse_jobscript()
job_properties = read_job_properties(jobscript)

sbatch_options = {}
default_cluster_config = slurm_utils.load_default_cluster_config()

# 1) sbatch default arguments
sbatch_options.update(slurm_utils.sbatch_defaults())

# 2) default_cluster_config defaults
sbatch_options.update(default_cluster_config["__default__"])

# 3) Convert resources (no unit conversion!) and threads
sbatch_options.update(slurm_utils.convert_job_properties(job_properties))

# 4) default_cluster_config for particular rule
sbatch_options.update(default_cluster_config.get(job_properties['rule'], {}))

# 5) cluster_config options
sbatch_options.update(job_properties.get("cluster", {}))


# ensure sbatch output dirs exist
for o in ('output', "error"):
    slurm_utils.ensure_dirs_exist(sbatch_options[o]) if o in sbatch_options else None


# submit job and echo id back to Snakemake (must be the only stdout)
print(slurm_utils.submit_job(jobscript, **sbatch_options))
