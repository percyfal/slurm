#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
from docker.models.containers import ExecResult


class Snakemake:
    """Class wrapper to run snakemake jobs on container"""

    _path = 'export PATH="$SNAKEMAKE_PATH:$PATH"'
    _snakemake = "snakemake"
    _snakefile = "Snakefile"
    _process_args = {}
    _process_prefix = ""

    @classmethod
    def executable(cls, cmd):
        if os.path.split(cmd)[-1] == "bash":
            cls._process_prefix = "set -euo pipefail;"
        cls._process_args["executable"] = cmd

    @classmethod
    def prefix(cls, prefix):
        cls._process_prefix = prefix

    def __init__(self, container, data, jobname, advanced=False):
        self._container = container
        self._data = data
        self._jobname = jobname.lstrip("test_")
        d = "slurm-advanced" if advanced else "slurm"
        self._profile = self._data.join(d).join("slurm")
        self._output = []

    def __call__(self, target, iterable=True, asynchronous=False, **kwargs):
        self._snakefile = kwargs.pop("snakefile", self._snakefile)
        pp = kwargs.pop("process_prefix", self._process_prefix)
        path = self._path
        exe = self._process_args["executable"]
        snakemake = self._snakemake
        snakefile = self.snakefile
        options = kwargs.pop("options", "")

        profile = kwargs.pop("profile", self.profile)
        if profile is None:
            prof = ""
        else:
            prof = f"--profile {profile}"

        jobname = kwargs.pop("jobname", self.jobname)
        if jobname is None:
            jn = ""
        else:
            jn = f"--jn {jobname}-{{jobid}}"

        self._cmd = f"{exe} -c '{pp} {path} && {snakemake} -s {snakefile} {options} --nolock -j 1 -F {target} {prof} {jn}'"

        try:
            proc = self._container.exec_run(
                self._cmd, stream=iterable, detach=asynchronous, **kwargs
            )
        except Exception:
            raise
        if iterable:
            return self.iter_stdout(proc)
        return self.read_stdout(proc)

    def __str__(self):
        return f"{self._jobname}"

    @property
    def jobname(self):
        return f"{self._jobname}"

    @property
    def profile(self):
        return self._profile

    @property
    def snakefile(self):
        return self._data.join(self._snakefile)

    @property
    def output(self):
        if isinstance(self._output, list):
            return "\n".join(self._output)
        return self._output

    def read_stdout(self, proc):
        if isinstance(proc, ExecResult):
            self._output = proc.output.decode()
            return proc.output.decode()
        elif isinstance(proc, bytes):
            self._output = proc.decode()
            return proc.decode()

    def iter_stdout(self, proc):
        # Assume ExecResult
        for l in proc.output:
            if isinstance(l, bytes):
                for k in l.decode().split("\n"):
                    self._output.append(k)
                    yield k
            else:
                self._output = l[:-1].decode()
                yield l[:-1].decode()
        return

    @property
    def external_jobid(self):
        m = re.search("external jobid '(?P<jobid>\\d+)'", self.output)
        if m is None:
            return None
        return m.group("jobid")

    def is_finished(self, regex=None):
        if regex is None:
            regex = "Finished"
        m = re.search(f"(?P<finished>{regex})", self.output)
        return m is not None


if "SHELL" in os.environ:
    Snakemake.executable(os.environ["SHELL"])
