from __future__ import annotations
import copy
import json
import math
import os
from pathlib import Path
import uuid

MODES=('health','endurance','sound','combined','screen','static')

def default_config():
    return {'version':1,'automation':False,'cache':str(Path.home()/'Zomboid'/'Lua'),
            'openrgb_exe':'','start_openrgb':False,'zones':[],
            'profiles':[{'id':'zomboid','name':'Project Zomboid','source':'zomboid','enabled':False,
                         'executables':['ProjectZomboid64.exe','ProjectZomboid32.exe'], 'routes':[]},
                        {'id':'hue','name':'Hue','source':'hue','enabled':False,
                         'executables':['Hue.exe'],'routes':[]}],
            'hue':{'brightness':.5,'smoothing':.5}}


def validate(cfg):
    if not isinstance(cfg,dict) or cfg.get('version')!=1:raise ValueError('Unbekanntes Konfigurationsformat')
    if type(cfg.get('automation')) is not bool:raise ValueError('Automatik muss ein Schalter sein')
    if not isinstance(cfg.get('cache'),str):raise ValueError('Ungueltiger Zomboid-Pfad')
    for key in ('openrgb_exe',):
        if not isinstance(cfg.get(key),str):raise ValueError('Ungueltiger OpenRGB-Pfad')
    if type(cfg.get('start_openrgb')) is not bool:raise ValueError('Ungueltiger OpenRGB-Autostart')
    zones=cfg.get('zones');profiles=cfg.get('profiles')
    if not isinstance(zones,list) or len(zones)>128:raise ValueError('Zu viele Zonen')
    zone_ids=set();used={}
    for z in zones:
        if not isinstance(z.get('id'),str) or not z['id'] or z['id'] in zone_ids:raise ValueError('Doppelte Zone')
        zone_ids.add(z['id'])
        if not isinstance(z.get('device'),str) or not z['device']:raise ValueError('Geraet fehlt')
        if not isinstance(z.get('name'),str) or not z['name'].strip():raise ValueError('Zonenname fehlt')
        leds=z.get('leds')
        if not isinstance(leds,list) or not leds or any(type(i) is not int or not 0<=i<8192 for i in leds):raise ValueError('LED-Indizes ungueltig')
        occupied=used.setdefault(z['device'],set())
        if len(set(leds))!=len(leds) or occupied.intersection(leds):raise ValueError('LED-Zonen duerfen sich nicht ueberlappen')
        occupied.update(leds)
        offset=z.get('offset',0)
        if type(offset) not in (int,float) or not math.isfinite(offset) or not -360<=offset<=360:raise ValueError('Winkel ungueltig')
        if type(z.get('reverse',False)) is not bool:raise ValueError('Richtung ungueltig')
    if not isinstance(profiles,list) or len(profiles)>32:raise ValueError('Zu viele Profile')
    ids=set()
    for p in profiles:
        if not isinstance(p.get('id'),str) or p['id'] in ids:raise ValueError('Profil-ID ungueltig')
        ids.add(p['id'])
        if not isinstance(p.get('name'),str) or not p['name'].strip() or len(p['name'])>120:raise ValueError('Profilname ungueltig')
        if p.get('source') not in ('hue','zomboid'):raise ValueError('Unbekannte Datenquelle')
        if type(p.get('enabled')) is not bool:raise ValueError('Profilstatus ungueltig')
        exes=p.get('executables')
        if not isinstance(exes,list) or len(exes)>32 or any(not isinstance(x,str) or not x.strip() for x in exes):raise ValueError('Programmdateien ungueltig')
        routes=p.get('routes')
        if not isinstance(routes,list) or len(routes)>128:raise ValueError('Profil-Zuordnungen ungueltig')
        targets=set()
        for r in routes:
            if r.get('zone') not in zone_ids or r['zone'] in targets:raise ValueError('Zone fehlt oder ist doppelt belegt')
            targets.add(r['zone'])
            if r.get('mode') not in MODES:raise ValueError('Anzeigemodus ungueltig')
            if p['source']=='hue' and r['mode'] not in ('screen','static'):raise ValueError('Hue nutzt Bildschirmfarbe oder feste Farbe')
            if p['source']=='zomboid' and r['mode']=='screen':raise ValueError('Zomboid nutzt Spieldaten')
            b=r.get('brightness')
            if type(b) not in (int,float) or not math.isfinite(b) or not 0<=b<=1:raise ValueError('Helligkeit ungueltig')
            if type(r.get('player')) is not int or not 0<=r['player']<=3:raise ValueError('Spieler ungueltig')
            if r.get('category') not in ('all','world','zombie','vehicle','player','gunshot','alarm'):raise ValueError('Geraeuschfilter ungueltig')
            color=r.get('color')
            if not isinstance(color,list) or len(color)!=3 or any(type(c) is not int or not 0<=c<=255 for c in color):raise ValueError('Farbe ungueltig')
    return cfg


def atomic_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    with temporary.open('w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)


def load(path):
    if not Path(path).exists():return default_config()
    return validate(json.loads(Path(path).read_text(encoding='utf-8')))


def save(path,cfg):atomic_json(path,validate(copy.deepcopy(cfg)))

def new_zone(name,device,leds,offset=0,reverse=False):
    return {'id':uuid.uuid4().hex,'name':name,'device':device,'leds':leds,'offset':offset,'reverse':reverse}
