#!/usr/bin/env python3
import pytest


def test_bake_project(cookies):
    result = cookies.bake(template=str(pytest.cookie_template))
    assert result.exit_code == 0
    assert result.exception is None
    assert result.project.basename == "slurm"
    assert result.project.isdir()


def test_cluster_name(cookies):
    result = cookies.bake(template=str(pytest.cookie_template))
    sbatch_defaults = result.project.join("slurm-submit.py").read().split("\n")[11]
    assert '""""""' in sbatch_defaults
    cluster = result.project.join("slurm-status.py").read().split("\n")[15]
    print(cluster)
    assert cluster == 'cluster = ""'

    result = cookies.bake(
        template=str(pytest.cookie_template), extra_context={"cluster_name": "dusk"}
    )
    sbatch_defaults = result.project.join("slurm-submit.py").read().split("\n")[11]
    assert "dusk" in sbatch_defaults
    cluster = result.project.join("slurm-status.py").read().split("\n")[15]
    assert cluster == 'cluster = "--cluster=dusk"'
