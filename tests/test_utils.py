#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import pytest
from docker.models.containers import Container

sys.path.append(
    os.path.join(os.path.dirname(__file__), os.pardir, "{{cookiecutter.profile_name}}")
)
from CookieCutter import CookieCutter  # noqa: E402
import slurm_utils  # noqa: E402


# # Profile has not been installed so need to mock calls
# @pytest.fixture
# def mock_cookiecutter_cluster_option(monkeypatch):
#     def cluster_option():
#         return ""
#     monkeypatch.setattr(CookieCutter, "get_cluster_option", cluster_option)


# @pytest.fixture
# def mock_cookiecutter_named_cluster_option(monkeypatch):
#     def cluster_option():
#         return "--cluster=linux"
#     monkeypatch.setattr(CookieCutter, "get_cluster_option", cluster_option)


# def test_time_to_minutes():
#     minutes = slurm_utils.time_to_minutes("foo")
#     assert minutes is None
#     minutes = slurm_utils.time_to_minutes("10-00:00:10")
#     assert minutes == 14401
#     minutes = slurm_utils.time_to_minutes("10:00:00")
#     assert minutes == 600
#     minutes = slurm_utils.time_to_minutes("100:00")
#     assert minutes == 100
#     minutes = slurm_utils.time_to_minutes("20")
#     assert minutes == 20


# def test_si_units():
#     m = slurm_utils._convert_units_to_mb(1000)
#     assert m == 1000
#     m = slurm_utils._convert_units_to_mb("1000K")
#     assert m == 1
#     m = slurm_utils._convert_units_to_mb("1000M")
#     assert m == 1000
#     m = slurm_utils._convert_units_to_mb("1000G")
#     assert m == 1e6
#     m = slurm_utils._convert_units_to_mb("1000T")
#     assert m == 1e9
#     with pytest.raises(SystemExit):
#         m = slurm_utils._convert_units_to_mb("1000E")
