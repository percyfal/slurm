#!/usr/bin/env python3
import pytest


def test_bake_project(cookies):
    result = cookies.bake(template=str(pytest.template))
    assert result.exit_code == 0
    assert result.exception is None
    assert result.project.basename == 'slurm'
    assert result.project.isdir()
