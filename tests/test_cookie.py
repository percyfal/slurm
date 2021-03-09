#!/usr/bin/env python3
import pytest


def test_bake_project(cookies):
    result = cookies.bake(template=str(pytest.cookie_template))
    assert result.exit_code == 0
    assert result.exception is None
    assert result.project.basename == "slurm"
    assert result.project.isdir()


def test_cluster_name(cookies):
    def _get_cluster(result):
        config = result.project.join("CookieCutter.py").read()
        i = config.split("\n").index("    def get_cluster_name() -> str:") + 1
        return config.split("\n")[i].strip()

    result = cookies.bake(template=str(pytest.cookie_template))
    assert _get_cluster(result) == 'return ""'

    result = cookies.bake(
        template=str(pytest.cookie_template), extra_context={"cluster_name": "dusk"}
    )
    assert _get_cluster(result) == 'return "dusk"'
