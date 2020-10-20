#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import logging
import subprocess as sp
from docker.models.resource import Model
from docker.models.containers import ExecResult
from docker.errors import DockerException

STDOUT = sys.stdout


class ShellContainer(Model):
    """Class wrapper to emulate docker container but for shell calls"""

    _exit_code = None

    def __init__(self, attrs=None, client=None, collection=None):
        super().__init__(attrs, client, collection)

    @property
    def short_id(self):
        return self.id

    def exec_run(self, cmd, stream=False, detach=False, **kwargs):
        stdout = kwargs.pop("stdout", sp.PIPE)
        stderr = kwargs.pop("stderr", STDOUT)
        close_fds = sys.platform != "win32"
        executable = os.environ.get("SHELL", None)
        proc = sp.Popen(
            cmd,
            bufsize=-1,
            shell=True,
            stdout=stdout,
            stderr=stderr,
            close_fds=close_fds,
            executable=executable,
        )

        def iter_stdout(proc):
            for line in proc.stdout:
                yield line[:-1]

        if detach:
            return ExecResult(None, "")

        if stream:
            return ExecResult(None, iter_stdout(proc))
        return ExecResult(proc.returncode, proc.stdout.read())


class SnakemakeRunner:
    """Class wrapper to run snakemake jobs in container"""

    _snakemake = "snakemake"
    _snakefile = "Snakefile"
    _directory = None
    _jobid_regex = "|".join(
        [
            r"Submitted batch job (\d+)",
            r"Submitted job \d+ with external jobid '(\d+)'"
            # Missing resubmitted case
        ]
    )

    _process_args = {}
    _process_prefix = ""

    @classmethod
    def executable(cls, cmd):
        if os.path.split(cmd)[-1] == "bash":
            cls._process_prefix = "set -euo pipefail"
        cls._process_args["executable"] = cmd

    @classmethod
    def prefix(cls, prefix):
        cls._process_prefix = prefix

    def __init__(self, container, data, jobname, advanced=False, partition="normal"):
        self._container = container
        self._data = data
        self._jobname = re.sub("test_", "", jobname)
        self._output = []
        self._pp = self._process_prefix
        self._cmd = ""
        self._num_cores = 1
        self._logger = logging.getLogger(str(self))
        self._external_jobid = []
        self._partition = partition
        d = "slurm-advanced" if advanced else "slurm"
        self._profile = self._data.join(d).join("slurm")

    def exec_run(self, cmd, stream=False, **kwargs):
        return self._container.exec_run(cmd, stream=stream, **kwargs)

    def make_target(self, target, stream=True, asynchronous=False, **kwargs):
        """Wrapper to make snakemake target"""
        self._snakefile = kwargs.pop("snakefile", self._snakefile)
        options = kwargs.pop("options", "")
        profile = kwargs.pop("profile", str(self.profile))
        jobname = kwargs.pop("jobname", str(self.jobname))
        force = "-F" if kwargs.pop("force", False) else ""
        verbose = kwargs.pop("verbose", True)
        self._directory = "-d {}".format(kwargs.pop("dir", self.snakefile.dirname))
        prof = "" if profile is None else f"--profile {profile}"
        jn = "" if jobname is None else f"--jn {jobname}-{{jobid}}"
        self._external_jobid = []

        cmd = (
            f"{self.exe} -c '{self.pp} && "
            + f"{self.snakemake} -s {self.snakefile} "
            + f"{options} --nolock "
            + f"-j {self._num_cores} {self.workdir} {force} {target} {prof} {jn}'"
        )
        try:
            (exit_code, output) = self.exec_run(cmd, stream=stream, detach=asynchronous)
        except Exception as e:
            raise e
        if stream:
            for x in output:
                if isinstance(x, bytes):
                    x = x.decode()
                if verbose:
                    print(x)
                self._output.append(x)
        else:
            if isinstance(output, bytes):
                output = output.decode()
            self._output = [output]
        return ExecResult(exit_code, output)

    @property
    def jobname(self):
        return self._jobname

    @property
    def profile(self):
        return self._profile

    @property
    def snakefile(self):
        return self._data.join(self._snakefile)

    @property
    def snakemake(self):
        return self._snakemake

    @property
    def partition(self):
        return self._partition

    @property
    def workdir(self):
        if self._directory is None:
            self._directory = self.snakefile.dirname
        return self._directory

    @property
    def cluster_config(self):
        return self._data.join("cluster-config.yaml")

    @property
    def slurm_submit(self):
        return self.profile.join("slurm-submit.py")

    @property
    def slurm_status(self):
        return self.profile.join("slurm-status.py")

    @property
    def exe(self):
        return self._process_args["executable"]

    @property
    def pp(self):
        return self._pp

    def script(self, script):
        return self._data.join(script)

    @property
    def output(self):
        if isinstance(self._output, list):
            return "\n".join(self._output)
        return self._output

    @property
    def external_jobid(self):
        if len(self._external_jobid) == 0:
            try:
                m = re.findall(self._jobid_regex, self.output)
                if m is not None:
                    self._external_jobid = [int(x) for y in m for x in y if x]
            except Exception as e:
                print(e)
            finally:
                (_, out) = self.exec_run('squeue -h -o "%.50j,%.10i"', stream=False)
                try:
                    for res in out.decode().split("\n"):
                        if self.jobname in res:
                            self._external_jobid.append(
                                re.search(r" (\d+)$", res.strip()).group(1)
                            )
                except Exception as e:
                    print(e)

        return self._external_jobid

    def check_jobstatus(self, regex, options="", jobid=None, which=0):
        """Use sacct to check jobstatus"""
        if self.external_jobid is None and jobid is None:
            return False
        if jobid is None:
            jobid = self.external_jobid[which]
        cmd = f"sacct -P -b {options} -j {jobid}"
        (exit_code, output) = self.exec_run(cmd, stream=False)
        if exit_code != 0:
            raise DockerException(output.decode())
        m = re.search(regex, output.decode())
        if m is None:
            self._logger.warning(f"{cmd}\n{output.decode()}")
        return m

    def __str__(self):
        return f"{self._jobname}"


if "SHELL" in os.environ:
    SnakemakeRunner.executable(os.environ["SHELL"])
# Try falling back on /bin/bash
else:
    SnakemakeRunner.executable("/bin/bash")
