from __future__ import annotations
import colorsys
import json
import math
from pathlib import Path
import time
from .rendering import validate_frame


def matches(executable,patterns):
    from pathlib import PureWindowsPath
    exe=str(PureWindowsPath(executable)).casefold()
    for pattern in patterns:
        p=PureWindowsPath(pattern)
        if (str(p).casefold()==exe if ('/' in pattern or '\\' in pattern) else p.name.casefold()==PureWindowsPath(executable).name.casefold()):return True
    return False


def choose_profile(cfg,foreground):
    if not cfg['automation'] or not foreground:return None
    return next((p for p in cfg['profiles'] if p['enabled'] and matches(foreground['exe'],p['executables'])),None)


def read_zomboid(directory,now=None):
    now=time.time() if now is None else now
    candidates=[]
    for slot in (0,1):
        p=Path(directory)/f'za-frame-{slot}.json'
        try:
            stat=p.stat()
            if stat.st_size>256000 or not -1<=now-stat.st_mtime<=3:continue
            f=validate_frame(json.loads(p.read_text(encoding='utf-8')))
            candidates.append((stat.st_mtime,f))
        except (OSError,ValueError,TypeError,KeyError,AttributeError):pass
    return max(candidates,key=lambda x:(x[0],x[1]['seq']))[1] if candidates else None


def dominant_color(image):
    """Most common saturated hue group; ignore black geometry and white UI."""
    image=image.convert('RGB').resize((96,54))
    groups={};accepted=0
    pixels=image.tobytes()
    for r,g,b in zip(pixels[0::3],pixels[1::3],pixels[2::3]):
        h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
        if v<.16 or s<.20:continue
        bucket=int(h*24)%24
        a=groups.setdefault(bucket,[0,0,0,0])
        a[0]+=1;a[1]+=r;a[2]+=g;a[3]+=b;accepted+=1
    if accepted<96*54*.02:return None
    group=max(groups.values(),key=lambda x:x[0])
    return tuple(round(v/group[0]) for v in group[1:])


def smooth(previous,color,alpha=.5):
    if previous is None:return color
    return tuple(round(a*(1-alpha)+b*alpha) for a,b in zip(previous,color))


class WindowsForeground:
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes=ctypes;self.w=wintypes
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.user.GetForegroundWindow.restype=wintypes.HWND
        self.user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        self.user.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
        self.user.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)]
        self.kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.kernel.OpenProcess.restype=wintypes.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        try:self.user.SetProcessDPIAware()
        except Exception:pass

    def current(self):
        c,w=self.ctypes,self.w
        hwnd=self.user.GetForegroundWindow()
        if not hwnd:return None
        pid=w.DWORD();self.user.GetWindowThreadProcessId(hwnd,c.byref(pid))
        handle=self.kernel.OpenProcess(0x1000,False,pid.value)
        if not handle:return None
        try:
            buffer=c.create_unicode_buffer(32768);size=w.DWORD(len(buffer))
            if not self.kernel.QueryFullProcessImageNameW(handle,0,buffer,c.byref(size)):return None
            rect=w.RECT();point=w.POINT(0,0)
            if not self.user.GetClientRect(hwnd,c.byref(rect)) or not self.user.ClientToScreen(hwnd,c.byref(point)):return None
            if rect.right<=0 or rect.bottom<=0:return None
            return {'hwnd':int(hwnd),'exe':buffer.value,'rect':{'left':point.x,'top':point.y,'width':rect.right,'height':rect.bottom}}
        finally:self.kernel.CloseHandle(handle)


class ScreenSource:
    def __init__(self):self.capture=None
    def color(self,foreground,reader):
        # Confirm the same foreground window both before and after the in-memory capture.
        before=reader.current()
        if not before or before['hwnd']!=foreground['hwnd'] or before['exe']!=foreground['exe']:return None
        if self.capture is None:
            import mss
            self.capture=mss.mss()
        from PIL import Image
        shot=self.capture.grab(before['rect'])
        after=reader.current()
        if not after or after['hwnd']!=before['hwnd'] or after['exe']!=before['exe']:return None
        image=Image.frombytes('RGB',shot.size,shot.rgb)
        return dominant_color(image)
    def close(self):
        if self.capture:self.capture.close();self.capture=None
