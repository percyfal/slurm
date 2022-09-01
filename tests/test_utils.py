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
from slurm_utils import Time, InvalidTimeUnitError  # noqa: E402


def test_time_to_minutes():
    minutes = slurm_utils.time_to_minutes("foo")
    assert minutes is None
    minutes = slurm_utils.time_to_minutes("10-00:00:10")
    assert minutes == 14401
    minutes = slurm_utils.time_to_minutes("10:00:00")
    assert minutes == 600
    minutes = slurm_utils.time_to_minutes("100:00")
    assert minutes == 100
    minutes = slurm_utils.time_to_minutes("20")
    assert minutes == 20


def test_si_units():
    m = slurm_utils._convert_units_to_mb(1000)
    assert m == 1000
    m = slurm_utils._convert_units_to_mb("1000K")
    assert m == 1
    m = slurm_utils._convert_units_to_mb("1000M")
    assert m == 1000
    m = slurm_utils._convert_units_to_mb("1000G")
    assert m == 1e6
    m = slurm_utils._convert_units_to_mb("1000T")
    assert m == 1e9
    with pytest.raises(SystemExit):
        m = slurm_utils._convert_units_to_mb("1000E")


class TestTime:
    def test_parse_time_seconds(self):
        s = "4s"

        actual = str(Time(s))
        expected = "0:00:04"

        assert actual == expected

    def test_parse_time_minutes(self):
        s = "4m"

        actual = str(Time(s))
        expected = "0:04:00"

        assert actual == expected

    def test_parse_time_hours_in_minutes(self):
        s = "400m"

        actual = str(Time(s))
        expected = "6:40:00"

        assert actual == expected

    def test_parse_time_hours(self):
        s = "3H"

        actual = str(Time(s))
        expected = "3:00:00"

        assert actual == expected

    def test_parse_time_hours_and_minutes(self):
        s = "3h46m"

        actual = str(Time(s))
        expected = "3:46:00"

        assert actual == expected

    def test_parse_time_hours_and_minutes_with_space(self):
        s = "3h 46m"

        actual = str(Time(s))
        expected = "3:46:00"

        assert actual == expected

    def test_parse_time_days_and_seconds(self):
        s = "1d4s"

        actual = str(Time(s))
        expected = "24:00:04"

        assert actual == expected
    def test_parse_time_days_and_seconds_order_not_important(self):
        s = "4s1d"

        actual = str(Time(s))
        expected = "24:00:04"

        assert actual == expected

    def test_parse_time_weeks_and_minutes(self):
        s = "2w4m"

        actual = str(Time(s))
        expected = "336:04:00"

        assert actual == expected

    def test_parse_time_slurm_format_no_parsing(self):
        s = "3:45"

        actual = str(Time(s))
        expected = "3:45"

        assert actual == expected

    def test_parse_time_no_units(self):
        s = "3"

        actual = str(Time(s))
        expected = "3"

        assert actual == expected

    def test_parse_time_zero(self):
        s = "0"

        actual = str(Time(s))
        expected = "0"

        assert actual == expected

    def test_parse_time_float_is_supported(self):
        s = "1.5d"

        actual = str(Time(s))
        expected = "36:00:00"

        assert actual == expected

    def test_parse_time_missing_unit_ignores_value_with_no_unit(self):
        s = "5m3"

        actual = str(Time(s))
        expected = "0:05:00"

        assert actual == expected

    def test_parse_time_unknown_unit(self):
        s = "5x"

        with pytest.raises(InvalidTimeUnitError):
            actual = str(Time(s))
