import os
from pathlib import Path
import subprocess
import sys


class SingleInstance:
    def __init__(self,path):self.path=Path(path);self.handle=None
    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.handle=self.path.open('a+b');self.handle.seek(0,2)
        if self.handle.tell()==0:self.handle.write(b'0');self.handle.flush()
        self.handle.seek(0)
        try:
            if sys.platform=='win32':
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return True
        except OSError:self.handle.close();self.handle=None;return False
    def close(self):
        if self.handle:self.handle.close();self.handle=None


def shortcut_path():
    return Path(os.environ['APPDATA'])/'Microsoft'/'Windows'/'Start Menu'/'Programs'/'Startup'/'AllyLight.lnk'


def autostart_enabled():return sys.platform=='win32' and shortcut_path().exists()


def set_autostart(enabled,script,data_dir):
    if sys.platform!='win32':raise RuntimeError('Autostart ist fuer Windows vorgesehen.')
    path=shortcut_path()
    if not enabled:path.unlink(missing_ok=True);return
    import win32com.client
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    if not pythonw.exists():raise RuntimeError('pythonw.exe fehlt.')
    path.parent.mkdir(parents=True,exist_ok=True)
    shell=win32com.client.Dispatch('WScript.Shell');link=shell.CreateShortCut(str(path))
    link.TargetPath=str(pythonw)
    link.Arguments=subprocess.list2cmdline([str(Path(script).resolve()),'--tray','--data-dir',str(Path(data_dir).resolve())])
    link.WorkingDirectory=str(Path(script).resolve().parent)
    link.Description='AllyLight Spielbeleuchtung';link.Save()


def launch_openrgb(executable):
    path=Path(executable)
    if not path.is_file() or path.suffix.casefold()!='.exe':raise ValueError('OpenRGB.exe auswaehlen.')
    # Read-only port check avoids launching a second SDK server if one is ready.
    import socket
    try:
        with socket.create_connection(('127.0.0.1',6742),timeout=.3):return False
    except OSError:pass
    subprocess.Popen([str(path),'--server','--startminimized'],cwd=str(path.parent))
    return True
