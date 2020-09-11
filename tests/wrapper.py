#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import logging
from docker.models.containers import ExecResult
from docker.errors import DockerException


class SlurmRunner:
    """Class wrapper to submit slurm jobs to the test docker stack"""

    # pylint: disable=too-many-instance-attributes
    # Going with ten attributes for now

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

    def __init__(self, container, data, jobname, advanced=False):
        self._container = container
        self._data = data
        self._jobname = re.sub("test_", "", jobname)
        self._output = []
        self._exit_code = None
        self._pp = self._process_prefix
        self._cmd = ""
        self._num_cores = 1
        self._logger = logging.getLogger(str(self))

    def _setup_exec_run(self, *args, **kwargs):
        if args:
            kwargs["cmd"] = args[0]
        cmd = kwargs.pop("cmd", 'squeue -h -o "%.18i"')
        self._pp = kwargs.pop("process_prefix", self._pp)
        self._cmd = f"{self.exe} -c '{self.pp} && {cmd}'"
        return kwargs

    def exec_run(
        self, *args, iterable=True, asynchronous=False, verbose=True, **kwargs,
    ):
        self._num_cores = kwargs.pop("num_cores", 1)
        self._output = []
        kwargs = self._setup_exec_run(*args, **kwargs)
        if verbose:
            self._logger.info(f"'{self.cmd}'")

        try:
            proc = self._container.exec_run(
                self.cmd, stream=iterable, detach=asynchronous, **kwargs
            )

        except Exception as e:
            raise e
        if iterable:
            if verbose:
                for x in self.iter_stdout(proc):
                    print(x)
            return self.iter_stdout(proc)
        return self.read_stdout(proc)

    @property
    def cmd(self):
        return self._cmd

    def script(self, script):
        return self._data.join(script)

    @property
    def num_cores(self):
        return self._num_cores

    @property
    def pp(self):
        return self._pp

    @property
    def exe(self):
        return self._process_args["executable"]

    def iter_stdout(self, proc):
        if isinstance(proc, ExecResult):
            for l in proc.output:
                if isinstance(l, bytes):
                    for k in l.decode().split("\n"):
                        self._output.append(k)
                        yield k
                else:
                    self._output = l[:-1].decode()
                    yield l[:-1].decode()

    @property
    def output(self):
        if isinstance(self._output, list):
            return "\n".join(self._output)
        return self._output

    def read_stdout(self, proc):
        if isinstance(proc, ExecResult):
            if isinstance(proc.output, str):
                self._output = proc.output
            else:
                self._output = proc.output.decode()
        elif isinstance(proc, bytes):
            self._output = proc.decode()
        self._exit_code = proc.exit_code
        return self._output

    @property
    def exit_code(self):
        return self._exit_code

    def __str__(self):
        return f"{self._jobname}"


class SnakemakeRunner(SlurmRunner):
    """Class wrapper to run snakemake jobs in container"""

    _snakemake = "snakemake"
    _snakefile = "Snakefile"
    _jobid_regex = "|".join(
        [
            "Submitted batch job (\d+)",
            "Submitted job \d+ with external jobid '(\d+)'"
            # Missing resubmitted case
        ]
    )

    def __init__(self, container, data, jobname, advanced=False):
        super().__init__(container, data, jobname)
        self._external_jobid = []
        d = "slurm-advanced" if advanced else "slurm"
        self._profile = self._data.join(d).join("slurm")

    def _setup_exec_run(self, *args, **kwargs):
        if args:
            kwargs["target"] = args[0]
        target = kwargs.pop("target", None)
        if target is None:
            return super()._setup_exec_run(**kwargs)
        self._snakefile = kwargs.pop("snakefile", self._snakefile)
        options = kwargs.pop("options", "")
        profile = kwargs.pop("profile", str(self.profile))
        jobname = kwargs.pop("jobname", str(self.jobname))
        prof = "" if profile is None else f"--profile {profile}"
        jn = "" if jobname is None else f"--jn {jobname}-{{jobid}}"
        self._external_jobid = []

        self._cmd = (
            f"{self.exe} -c '{self.pp} && "
            + f"{self.snakemake} -s {self.snakefile} "
            + f"{options} --nolock "
            + f"-j {self.num_cores} -F {target} {prof} {jn}'"
        )
        return kwargs

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
    def cluster_config(self):
        return self._data.join("cluster-config.yaml")

    @property
    def slurm_submit(self):
        return self.profile.join("slurm-submit.py")

    @property
    def slurm_status(self):
        return self.profile.join("slurm-status.py")

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
                (_, out) = self._container.exec_run('squeue -h -o "%.50j,%.10i"')
                try:
                    for res in out.decode().split("\n"):
                        if self.jobname in res:
                            self._external_jobid.append(
                                re.search(" (\d+)$", res.strip()).group(1)
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
        (exit_code, output) = self._container.exec_run(cmd)
        if exit_code != 0:
            raise DockerException(output.decode())
        m = re.search(regex, output.decode())
        if m is None:
            self._logger.warning(f"{cmd}\n{output.decode()}")
        return m


if "SHELL" in os.environ:
    SlurmRunner.executable(os.environ["SHELL"])
    SnakemakeRunner.executable(os.environ["SHELL"])
# Try falling back on /bin/bash
else:
    SlurmRunner.executable("/bin/bash")
    SnakemakeRunner.executable("/bin/bash")
