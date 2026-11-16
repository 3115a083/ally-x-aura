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


def external_environment(environment=None,bundle_root=None):
    import os
    result=dict(os.environ if environment is None else environment)
    root=bundle_root or getattr(sys,'_MEIPASS',None)
    if root:
        from pathlib import PureWindowsPath
        prefix=str(PureWindowsPath(root)).casefold().rstrip('\\')
        entries=result.get('PATH','').split(os.pathsep)
        result['PATH']=os.pathsep.join(p for p in entries if not (str(PureWindowsPath(p)).casefold()==prefix or str(PureWindowsPath(p)).casefold().startswith(prefix+'\\')))
    return result
