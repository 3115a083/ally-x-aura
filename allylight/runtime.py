"""Resolve persistent launch paths separately from temporary one-file resources."""
from pathlib import Path
import subprocess
import sys


def resource_root():
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))


def launch_command(script,data_dir,frozen=None,executable=None):
    frozen=getattr(sys,'frozen',False) if frozen is None else frozen
    exe=Path(executable or sys.executable)
    if frozen:
        return exe,subprocess.list2cmdline(['--tray','--data-dir',str(Path(data_dir).resolve())]),exe.parent
    pythonw=exe.with_name('pythonw.exe')
    return pythonw,subprocess.list2cmdline([str(Path(script).resolve()),'--tray','--data-dir',str(Path(data_dir).resolve())]),Path(script).resolve().parent
