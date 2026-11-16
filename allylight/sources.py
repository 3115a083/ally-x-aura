from __future__ import annotations
import colorsys
import json
import math
import re
from pathlib import Path
import time
from .rendering import validate_frame, finite


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


def read_pz_pulse(directory, now=None):
    """Read PZ Pulse's JSON assignment as data, never execute JavaScript.

    data.txt changes only with player values. Freshness belongs to heartbeat.txt.
    """
    now = time.time() if now is None else now
    root = Path(directory)
    if root.name.casefold() != 'pz_pulse':
        root = root / 'PZ_Pulse'
    data, heartbeat = root/'data.txt', root/'heartbeat.txt'
    try:
        beat = heartbeat.stat()
        if beat.st_size > 65536 or not -1 <= now-beat.st_mtime <= 3:
            return None
        before = data.stat()
        if before.st_size > 2_000_000 or before.st_size == 0:
            return None
        text = data.read_text(encoding='utf-8-sig')
        prefix = re.match(r'\s*window\.PZ_DATA\s*=\s*', text)
        if not prefix:
            return None
        payload, end = json.JSONDecoder().raw_decode(text, prefix.end())
        tail = re.fullmatch(r'\s*;\s*window\.PZ_DATA\.seq\s*=\s*(\d+)\s*;?\s*', text[end:])
        if not tail:
            return None
        after = data.stat()
        if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            return None
        health = finite(payload['health']['overall'], 0, 100) / 100
        stamina = [n for n in payload['needs'] if n.get('label') == 'Stamina']
        if len(stamina) != 1 or stamina[0].get('badHigh') is not False:
            return None
        endurance = finite(stamina[0]['value'], 0, 100) / 100
        # This export has one local player and no positional sound events.
        return validate_frame({'protocol':1, 'session':'pz-pulse', 'seq':int(tail[1]),
            'players':[{'id':0, 'health':health, 'endurance':endurance,
                        'sounds':[], 'sound_available':False}], 'routes':[], 'source':'pz-pulse'})
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return None


def read_zomboid(directory,now=None,source='auto'):
    root = Path(directory)
    pulse = root if root.name.casefold() == 'pz_pulse' else root/'PZ_Pulse'
    if source == 'pzpulse' or (source == 'auto' and pulse.is_dir()):
        return read_pz_pulse(directory,now)
    if source not in ('auto','addon'):
        return None
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


# Hue-specific HSV masks inspired by jath03's hue-game-sync.py.
# Algorithm reimplemented with Pillow/colorsys for Windows, no Xlib/OpenCV.
# Bounds use OpenCV's HSV scale: hue 0..180, saturation/value 0..255.
HUE_PALETTE = (
    ((175,100,200),(180,255,255),(255,0,0)),
    ((0,100,200),(20,255,255),(255,50,0)),
    ((22,200,200),(35,255,255),(255,255,0)),
    ((40,100,200),(55,255,255),(0,255,0)),
    ((60,100,200),(100,255,255),(0,255,255)),
    ((100,100,200),(130,255,255),(0,0,255)),
    ((135,150,200),(150,255,255),(150,0,255)),
    ((150,100,200),(165,255,255),(255,0,255)),
)

def hue_game_color(image):
    """Select Hue's palette by matching area, rather than averaging RGB.

    Red spans hue zero. Give exact red to red instead of the overlapping orange
    bucket. Empty/low-color screens return None, letting the engine time out.
    """
    image=image.convert('RGB').resize((96,54))
    counts=[0]*len(HUE_PALETTE)
    pixels=image.tobytes()
    for r,g,b in zip(pixels[0::3],pixels[1::3],pixels[2::3]):
        h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
        hsv=(h*180,s*255,v*255)
        for index,(low,high,_) in enumerate(HUE_PALETTE):
            inside=all(a<=x<=b for x,a,b in zip(hsv,low,high))
            if index==0 and hsv[0]<=2 and hsv[1]>=100 and hsv[2]>=200:
                inside=True
            if index==1 and hsv[0]<=2:
                inside=False
            if inside:counts[index]+=1
    winner=max(range(len(counts)),key=counts.__getitem__)
    # Original 20,000 of 640x360 pixels, scaled to the sample resolution.
    if counts[winner] < 96*54*(20000/(640*360)):
        return None
    return HUE_PALETTE[winner][2]


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
        return hue_game_color(image)
    def close(self):
        if self.capture:self.capture.close();self.capture=None
