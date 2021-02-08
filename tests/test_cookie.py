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

    cluster = result.project.join("CookieCutter.py").read().split("\n")[16]
    assert cluster.strip() == 'return ""'

    result = cookies.bake(
        template=str(pytest.cookie_template), extra_context={"cluster_name": "dusk"}
    )
    cluster = result.project.join("CookieCutter.py").read().split("\n")[16]
    assert cluster.strip() == 'return "dusk"'
