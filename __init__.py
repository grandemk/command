import subprocess
import os
import datetime

# dependency on asyncpro for interactive command
from . import asyncproc
from time import sleep
import collections

try:
  from .elastic_export import send_cmd_perf_to_elastic, init_elastic
except ModuleNotFoundError:
  # Do nothing if elastic support isn't available
  def send_cmd_perf_to_elastic(*varargs):
    pass
  def init_elastic():
    pass

class PerfLogger:
  def add(self, args, start_time, end_time):
    try:
      send_cmd_perf_to_elastic(args[0], " ".join(args[1:]), start_time, end_time)
    except KeyError:
      pass

_perf_logger = None

def GetPerfLogger():
  global _perf_logger
  if _perf_logger is None:
    _perf_logger = PerfLogger()
  return _perf_logger

class RunCommandError(Exception):
    def __init__(self, cmd, output, error, returncode):
        if output is None:
            self.output=""
        else:
            self.output = output.decode("utf-8", "surrogateescape")
        self.returncode = returncode
        if error is None:
            self.error=""
        else:
            self.error = error.decode("utf-8", "surrogateescape")
        self.cmd = cmd

    def __str__(self):
        return "RunCommandError.\ncmd:{}\noutput:{}\nerror:{}\nreturncode:{}".format(self.cmd, self.output, self.error, self.returncode)

def run_command(args, timeout=None, shell=False, cwd=None, env=os.environ.copy()):
    if shell and not isinstance(args, str):
        args = convert_command_to_shell(args)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell, cwd=cwd, env=env)

    (output, error) = ("", "")

    try:
        (output, error) = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as e:
        proc.kill()
        print("Process \"{}\"timed out after {} seconds".format(e.cmd, e.timeout))
        raise RunCommandError(args, e.stdout, e.stderr, -1)

    if proc.returncode != 0:
        print("Error. Got return code {}".format(proc.returncode))
        raise RunCommandError(args, output, error, proc.returncode)

    return output, error

def run_command_and_log(args, timeout=None, shell=False, cwd=None, env=os.environ.copy()):
    start_time = datetime.datetime.utcnow()
    start_time_local = datetime.datetime.now()
    print("[{}] Launching: ".format(start_time_local), args)
    ret = run_command(args, timeout, shell, cwd, env)
    end_time = datetime.datetime.utcnow()
    p = GetPerfLogger()
    p.add(args, start_time, end_time)
    return ret

def run_shell_command(args, timeout=None):
    return run_command(args, timeout=None, shell=True)

def convert_command_to_shell(args):
    args = ["\"{}\"".format(i) for i in args]
    args = " ".join(args)
    return args

def read_both(proc):
    out = proc.read()
    if out != b"":
        print(out.decode("utf-8"), end="")
    err = proc.readerr()
    if err != b"":
        print(err.decode("utf-8"), end="")
    return (out, err)

def run_command_interactive(args, shell=False, cwd=None, env=os.environ.copy()):
    proc = asyncproc.Process(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell, cwd=cwd, env=env)

    returncode = 0
    whole_out, whole_err = b"", b""

    while True:
        returncode = proc.wait(os.WNOHANG)
        if returncode is not None:
            break
        out, err = read_both(proc)
        whole_out, whole_err = whole_out + out, whole_err + err
        sleep(0.1)

    out, err = read_both(proc)
    whole_out, whole_err = whole_out + out, whole_err + err

    # the command was interactive (we could keep the output but there is no usage for now
    if returncode != 0:
        print("Error. Got return code {}".format(returncode))
        raise RunCommandError(args, whole_out, whole_err, returncode)

    return (whole_out, whole_err)

def run_command_interactive_and_log(args, shell=False, cwd=None, env=os.environ.copy()):
    start_time = datetime.datetime.utcnow()
    start_time_local = datetime.datetime.now()
    print("[{}] Launching: ".format(start_time_local), args)
    ret = run_command_interactive(args, shell, cwd, env)
    end_time = datetime.datetime.utcnow()
    p = GetPerfLogger()
    p.add(args, start_time, end_time)
    return ret
