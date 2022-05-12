#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import logging
import time
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
        stderr = kwargs.pop("stderr", sp.STDOUT)
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

        output = proc.communicate()
        return ExecResult(proc.returncode, output[0])


class SnakemakeRunner:
    """Class wrapper to run snakemake jobs in container"""

    _snakemake = "snakemake"
    _snakefile = "Snakefile"
    _directory = None
    _jobid_regex = "|".join(
        [
            r"Submitted batch job (\d+)",
            r"Submitted job \d+ with external jobid '(\d+)'.",
            r"Submitted group job \S+ with external jobid '(\d+)'."
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

    def __init__(self, container, data, jobname, partition="normal", account=None):
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
        self._account = account
        self._profile = self._data.join("slurm")

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
            + f"{options} --nolock --default-resources mem_mb=100 "
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
    def account(self):
        return self._account

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

    def wait_while_status(self, status, timeout=60, tdelta=10, verbose=False):
        """Wait for status to change"""
        t = 0
        while self.check_jobstatus(status, verbose=verbose):
            time.sleep(tdelta)
            t = t + tdelta
            if t >= timeout:
                self._logger.error(f"waiting while status '{status}' timed out")
                break

    def wait_for_status(self, status, timeout=60, tdelta=10, verbose=False):
        """Wait until status is achieved"""
        t = 0
        while not self.check_jobstatus(status, verbose=verbose):
            time.sleep(tdelta)
            t = t + tdelta
            if t >= timeout:
                self._logger.error(f"waiting for status '{status}' timed out")
                break

    def cancel_slurm_job(self, jobid):
        """Cancel job in slurm queue"""
        self.exec_run(f"scancel {jobid}")

    def check_jobstatus(self, regex, options="", jobid=None, which=0, verbose=True):
        """Use sacct to check jobstatus"""
        if len(self.external_jobid) == 0 and jobid is None:
            return False
        if jobid is None:
            jobid = str(self.external_jobid[which]).strip()
        cmd = f"sacct --parsable2 -b {options} -j {jobid}"
        (exit_code, output) = self.exec_run(cmd, stream=False)
        if exit_code != 0:
            raise DockerException(output.decode())
        m = re.search(regex, output.decode())
        if m is None and verbose:
            self._logger.warning(f"{cmd}\n{output.decode()}")
        return m

    def __str__(self):
        return f"{self._jobname}"


if "SHELL" in os.environ:
    SnakemakeRunner.executable(os.environ["SHELL"])
# Try falling back on /bin/bash
else:
    SnakemakeRunner.executable("/bin/bash")
