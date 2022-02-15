#!/usr/bin/env python3
import sys
import pytest


def test_bake_project(cookies):
    result = cookies.bake(template=str(pytest.cookie_template))
    assert result.exit_code == 0
    assert result.exception is None
    assert result.project.basename == "slurm"
    assert result.project.isdir()


def test_cookiecutter(cookies, monkeypatch):
    result = cookies.bake(template=str(pytest.cookie_template))
    monkeypatch.syspath_prepend(str(result.project_path))
    from CookieCutter import CookieCutter
    assert CookieCutter.SBATCH_DEFAULTS == ""
    assert CookieCutter.CLUSTER_NAME == ""
    assert CookieCutter.CLUSTER_CONFIG == ""
    assert CookieCutter.get_cluster_option() == ""
    assert CookieCutter.get_advanced_argument_conversion() is False
    sys.modules.pop("CookieCutter")


def test_cookiecutter_extra_context(cookies, monkeypatch):
    result = cookies.bake(template=str(pytest.cookie_template),
                          extra_context={"sbatch_defaults": "account=foo",
                                         "cluster_name": "dusk",
                                         "cluster_config": "slurm.yaml",
                                         "advanced_argument_conversion": "yes"})
    monkeypatch.syspath_prepend(str(result.project_path))
    from CookieCutter import CookieCutter
    assert CookieCutter.SBATCH_DEFAULTS == "account=foo"
    assert CookieCutter.CLUSTER_NAME == "dusk"
    assert CookieCutter.CLUSTER_CONFIG == "slurm.yaml"
    assert CookieCutter.get_cluster_option() == "--cluster=dusk"
    assert CookieCutter.get_advanced_argument_conversion() is True
    sys.modules.pop("CookieCutter")
