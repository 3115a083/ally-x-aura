from __future__ import annotations
import copy
import logging
from logging.handlers import RotatingFileHandler
import math
from pathlib import Path
import queue
import sys
import time
from .backend import OpenRGBBackend
from .config import validate
from .sources import WindowsForeground,ScreenSource,choose_profile,read_zomboid,smooth
from .rendering import render,scale


def output_frames(cfg,profile,players=None,color=None):
    zones={z['id']:z for z in cfg['zones']}
    frames={}
    for route in profile['routes']:
        zone=zones.get(route['zone'])
        if not zone:continue
        size=len(zone['leds']);mode=route['mode']
        if mode=='static':colors=[scale(route['color'],route['brightness'])]*size
        elif mode=='screen':
            if color is None:continue
            colors=[scale(color,route['brightness'])]*size
        else:
            player=next((p for p in players or [] if p['id']==route['player']),None)
            if player is None:continue
            if mode=='sound' and player.get('sound_available') is False:continue
            colors=render(route,player,size,bearing_offset=math.radians(zone.get('offset',0)),reverse=zone.get('reverse',False))
        frames.setdefault(zone['device'],{}).update(zip(zone['leds'],colors))
    return frames


def log_setup(data_dir):
    path=Path(data_dir)/'logs';path.mkdir(parents=True,exist_ok=True)
    handler=RotatingFileHandler(path/'engine.log',maxBytes=300000,backupCount=2,encoding='utf-8')
    logging.basicConfig(handlers=[handler],level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',force=True)


def recover_process(data_dir,events):
    backend=None
    try:
        backend=OpenRGBBackend(data_dir);backend.recover()
        events.put({'type':'recovery','ok':True,'message':'Gesicherte Beleuchtung wiederhergestellt.'})
    except Exception as exc:events.put({'type':'recovery','ok':False,'message':str(exc)})
    finally:
        if backend:
            try:backend.close()
            except Exception:pass


def worker(commands,events,initial_config,data_dir,demo=False):
    log_setup(data_dir)
    cfg=validate(copy.deepcopy(initial_config));backend=None;screen=ScreenSource()
    foreground=None;profile_key=None;color=None;preview=None
    last_parent=time.monotonic();last_status=0;retry_at=0;waiting_since=None;stopping=False
    try:
        if sys.platform=='win32':foreground=WindowsForeground()
        while not stopping:
            now=time.monotonic()
            while True:
                try:message=commands.get_nowait()
                except queue.Empty:break
                action=message['type']
                if action=='heartbeat':last_parent=now
                elif action=='stop':stopping=True
                elif action=='config':
                    cfg=validate(copy.deepcopy(message['config']))
                    if backend:backend.release()
                    profile_key=None;color=None
                elif action=='preview':
                    if backend:backend.release()
                    preview={'device':message['device'],'leds':message['leds'],'color':message.get('color',[35,35,35]),'until':now+2}
                    profile_key=None
                elif action in ('refresh','restore'):
                    preview=None;profile_key=None;color=None
                    if backend:
                        backend.release()
                        if action=='restore':backend.recover()
                        events.put({'type':'devices','devices':backend.inventory()})
                    else:retry_at=0
            if stopping:break
            if now-last_parent>5:
                logging.warning('Oberflaeche antwortet nicht. Beleuchtung wird zurueckgesetzt.');break
            if demo:
                if now-last_status>.5:
                    events.put({'type':'status','message':'Demo: keine Hardwarezugriffe','profile':'','color':None,'foreground':''});last_status=now
                time.sleep(.1);continue
            try:
                if backend is None:
                    if now<retry_at:time.sleep(.1);continue
                    backend=OpenRGBBackend(data_dir);backend.recover()
                    events.put({'type':'devices','devices':backend.inventory()})
                active=foreground.current() if foreground else None
                profile=choose_profile(cfg,active)
                if preview and now<preview['until']:
                    backend.apply({preview['device']:{i:preview['color'] for i in preview['leds']}})
                    status='LED-Test. Danach Wiederherstellung.';pname='Test';frames=None
                else:
                    if preview:
                        backend.release();preview=None
                    current=profile['id'] if profile else None
                    if current!=profile_key:
                        backend.release();profile_key=current;color=None;waiting_since=None
                    frames={};status='Bereit. Kein aktives Spielprofil.';pname=''
                    if profile:
                        pname=profile['name']
                        if profile['source']=='zomboid':
                            frame=read_zomboid(cfg['cache'],source=cfg.get('zomboid_source','auto'))
                            if frame:
                                frames=output_frames(cfg,profile,frame['players'])
                                status=('PZ Pulse: Gesundheit/Ausdauer empfangen. Keine Geraeuschrichtungen.' if frame.get('source')=='pz-pulse' else 'Zomboid-Daten empfangen.')
                            else:
                                frames=output_frames(cfg,profile,[])
                                status='Warte auf frische Spieldaten. PZ Pulse: data.txt und heartbeat.txt pruefen.'
                        elif not any(r['mode']=='screen' for r in profile['routes']):
                            frames=output_frames(cfg,profile)
                            status='Feste Profilfarbe aktiv.'
                        else:
                            next_color=screen.color(active,foreground)
                            if next_color is not None:
                                color=smooth(color,next_color,.5);waiting_since=None
                                frames=output_frames(cfg,profile,color=color);status='Hue: Hintergrundfarbe aktiv.'
                            else:
                                waiting_since=waiting_since or now
                                if color is not None and now-waiting_since<1.5:frames=output_frames(cfg,profile,color=color)
                                if not frames:frames=output_frames(cfg,profile)
                                status='Hue: keine klare Hintergrundfarbe erkannt.'
                    backend.apply(frames)
                if now-last_status>.5:
                    events.put({'type':'status','message':status,'profile':pname,'color':color,
                                'foreground':active['exe'] if active else ''});last_status=now
            except Exception as exc:
                logging.warning('%s',str(exc).replace(str(Path.home()),'<USER_HOME>'))
                events.put({'type':'error','message':str(exc).replace(str(Path.home()),'<USER_HOME>')})
                if backend:
                    try:backend.close()
                    except Exception as cleanup:logging.error('Wiederherstellung: %s',cleanup)
                backend=None;preview=None;profile_key=None;retry_at=time.monotonic()+3
            time.sleep(.12)
    except Exception as exc:
        logging.exception('Engine beendet');events.put({'type':'error','message':str(exc)})
    finally:
        screen.close()
        if backend:
            try:backend.close()
            except Exception as exc:events.put({'type':'error','message':'Wiederherstellung offen: '+str(exc)})
        events.put({'type':'stopped'})
