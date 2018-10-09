#!/usr/bin/env python3
import re
import pytest

PARTITION_RE = re.compile("^\s+arg_dict\[\"partition\"\]\s+=\s+\"(.*)\"$",
                          flags=re.MULTILINE)
ACCOUNT_RE = re.compile("^\s+arg_dict\[\"account\"\]\s+=\s+\"(.*)\"$",
                        flags=re.MULTILINE)


def test_bake_project(cookies):
    result = cookies.bake(template=str(pytest.template))
    assert result.exit_code == 0
    assert result.exception is None
    assert result.project.basename == 'slurm'
    assert result.project.isdir()


def test_default_partition(cookies):
    result = cookies.bake(template=str(pytest.template))
    submit = result.project.join("slurm-submit.py")
    submit_lines = "".join(submit.readlines())
    m = PARTITION_RE.search(submit_lines)
    partition = m.group(1)
    assert partition == ""


def test_normal_partition(cookies):
    result = cookies.bake(template=str(pytest.template),
                          extra_context={'partition': 'normal'})
    submit = result.project.join("slurm-submit.py")
    submit_lines = "".join(submit.readlines())
    m = PARTITION_RE.search(submit_lines)
    partition = m.group(1)
    assert partition == "normal"


def test_account(cookies):
    result = cookies.bake(template=str(pytest.template),
                          extra_context={'account': 'foo'})
    submit = result.project.join("slurm-submit.py")
    submit_lines = "".join(submit.readlines())
    m = ACCOUNT_RE.search(submit_lines)
    account = m.group(1)
    assert account == "foo"


def test_advanced_submit(cookies):
    result = cookies.bake(
        template=str(pytest.template),
        extra_context={'submit_script': 'slurm-submit-advanced.py'})
    config = result.project.join("config.yaml")
    config_list = [x.strip() for x in config.readlines()]
    assert "cluster: \"slurm-submit-advanced.py\"" in config_list
