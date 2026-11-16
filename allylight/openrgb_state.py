"""OpenRGB tests with durable snapshots and explicit restoration, localhost only."""
from __future__ import annotations
import base64
import copy
import hashlib
import json
from pathlib import Path
import struct
import time

SAFE_MODES={'static','direct','solid','solid color'}


def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    temporary.replace(path)


def rgb(color):return [int(color.red),int(color.green),int(color.blue)]


def identities(client):
    result={};counts={}
    for d in client.devices:
        # Device location/serial are used only in the hash, never included in reports.
        meta=d.metadata
        value='|'.join(str(v) for v in (d.name,d.type,getattr(meta,'serial',''),getattr(meta,'location',''),getattr(meta,'description','')))
        occurrence=counts.get(value,0);counts[value]=occurrence+1
        key=hashlib.sha256((value+'|'+str(occurrence)).encode()).hexdigest()[:20]
        result[key]=d
    return result


def inventory(client):
    client.update()
    return [{'id':key,'name':d.name,'led_count':len(d.leds),
             'active_mode':d.modes[d.active_mode].name,
             'modes':[m.name for m in d.modes],
             'colors':[rgb(c) for c in d.colors]}
            for key,d in identities(client).items()]


def snapshot(client,keys):
    from openrgb.utils import ModeColors
    client.update();devices=identities(client);rows=[]
    if not keys or len(set(keys))!=len(keys):raise ValueError('Select at least one distinct device')
    for key in keys:
        if key not in devices:raise ValueError('Device no longer present: '+key)
        d=devices[key];mode=copy.deepcopy(d.modes[d.active_mode])
        if mode.name.lower() not in SAFE_MODES:
            raise ValueError('First select Static or Direct in OpenRGB for '+d.name)
        if mode.color_mode not in (ModeColors.PER_LED,ModeColors.MODE_SPECIFIC):
            raise ValueError('Current mode does not support explicit colors')
        if not d.leds:raise ValueError('Device has no LEDs')
        mode_colors=mode.colors or []
        colors=mode_colors if mode_colors else d.colors
        if not colors or not any(any(rgb(c)) for c in colors):
            raise ValueError('OpenRGB reports black only. Set visible static blue in OpenRGB before testing.')
        rows.append({'id':key,'name':d.name,'led_count':len(d.leds),
                     'mode_name':mode.name,'mode_index':d.active_mode,
                     'mode_packet':base64.b64encode(mode.pack(client.protocol_version)).decode(),
                     'colors':[rgb(c) for c in d.colors]})
    return {'format':1,'backend':'openrgb','protocol':client.protocol_version,'devices':rows}


def restore(client,saved,sleep=time.sleep):
    from openrgb.utils import ModeData,ModeColors,RGBColor
    if saved.get('format')!=1 or saved.get('backend')!='openrgb':raise ValueError('Unsupported snapshot')
    if saved['protocol']!=client.protocol_version:raise ValueError('SDK protocol changed; restoration blocked')
    devices=identities(client);results=[]
    for row in saved['devices']:
        result={'id':row['id'],'status':'fail'}
        try:
            d=devices[row['id']]
            if d.name!=row['name'] or len(d.leds)!=row['led_count']:raise ValueError('Device identity/LED count changed')
            raw=base64.b64decode(row['mode_packet'],validate=True)
            if len(raw)>16384:raise ValueError('Snapshot mode too large')
            # ModeData.pack adds request size + mode ID; unpack expects controller-data body.
            if len(raw)<8:raise ValueError('Truncated mode snapshot')
            size,index=struct.unpack_from('<Ii',raw)
            if size!=len(raw) or index!=row['mode_index']:raise ValueError('Invalid mode snapshot header')
            mode=ModeData.unpack(iter(raw[8:]),saved['protocol'],row['mode_index'])
            if mode.name!=row['mode_name'] or mode.name.lower() not in SAFE_MODES:raise ValueError('Snapshot mode mismatch')
            # Decode and validate all stored colors before touching this device.
            colors=row['colors']
            if len(colors)!=len(d.leds) or any(len(c)!=3 or any(type(v) is not int or not 0<=v<=255 for v in c) for c in colors):
                raise ValueError('Invalid saved colors')
            mode.validate(saved['protocol'])
            d.set_mode(mode);sleep(.15)
            if mode.color_mode==ModeColors.PER_LED:
                d.set_colors([RGBColor(*c) for c in colors]);sleep(.15)
            elif mode.color_mode==ModeColors.MODE_SPECIFIC:
                # set_mode already sends the saved mode-specific colors and brightness.
                pass
            else:raise ValueError('Saved mode does not support explicit colors')
            client.update();current=identities(client)[row['id']]
            actual=current.modes[current.active_mode]
            match=actual.pack(saved['protocol'])==mode.pack(saved['protocol'])
            if mode.color_mode==ModeColors.PER_LED:match=match and [rgb(c) for c in current.colors]==colors
            result['status']='server_state_match' if match else 'server_state_mismatch'
        except Exception as exc:result['error']=str(exc)
        results.append(result)
    return results
