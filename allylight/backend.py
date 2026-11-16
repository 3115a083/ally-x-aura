from pathlib import Path
import json
import time
from .config import atomic_json
from .openrgb_state import identities, inventory, snapshot, restore


class OpenRGBBackend:
    def __init__(self,data_dir,client=None):
        if client is None:
            from openrgb import OpenRGBClient
            client=OpenRGBClient('127.0.0.1',6742,'AllyLight 0.1')
        self.client=client;self.data_dir=Path(data_dir)
        self.pending=self.data_dir/'snapshots'/'pending.json'
        self.saved=None;self.keys=set();self.last={}

    def inventory(self):return inventory(self.client)

    def recover(self):
        if self.pending.exists():
            self.saved=json.loads(self.pending.read_text(encoding='utf-8'))
            self.keys={row['id'] for row in self.saved['devices']}
            self.release()

    def claim(self,keys):
        keys=set(keys)
        if self.saved and keys==self.keys:return
        self.release()
        if self.pending.exists():raise RuntimeError('Offene Wiederherstellung. Erst Wiederherstellen waehlen.')
        self.saved=snapshot(self.client,sorted(keys))
        self.keys=keys
        # Durable before hardware access. If it cannot be written no mode is changed.
        try:atomic_json(self.pending,self.saved)
        except Exception:
            self.saved=None;self.keys=set();raise
        try:
            from openrgb.utils import ModeColors
            for key in sorted(keys):
                d=identities(self.client)[key]
                d.set_custom_mode();time.sleep(.12)
                if d.modes[d.active_mode].color_mode!=ModeColors.PER_LED:
                    raise RuntimeError('Geraet unterstuetzt keinen Direct-Modus: '+d.name)
        except Exception:
            self.release();raise

    def apply(self,frames):
        if not frames:self.release();return
        self.claim(frames)
        from openrgb.utils import RGBColor
        devices=identities(self.client)
        for key,changes in frames.items():
            original=next(row for row in self.saved['devices'] if row['id']==key)
            colors=[list(c) for c in original['colors']]
            if not colors or len(colors)!=len(devices[key].leds):raise RuntimeError('LED-Anzahl geaendert')
            for index,color in changes.items():
                if not 0<=index<len(colors):raise ValueError('LED-Zone passt nicht mehr zum Geraet')
                colors[index]=list(color)
            if self.last.get(key)!=colors:
                devices[key].set_colors([RGBColor(*c) for c in colors])
                self.last[key]=colors

    def release(self):
        if self.saved is None:return
        rows=restore(self.client,self.saved)
        atomic_json(self.data_dir/'logs'/'last-restoration.json',{'results':rows,'physical_verification':'not_measured'})
        if not rows or any(r['status']!='server_state_match' for r in rows):
            raise RuntimeError('Wiederherstellung unvollstaendig. Sicherung bleibt erhalten.')
        atomic_json(self.data_dir/'snapshots'/'last-restored.json',self.saved)
        self.pending.unlink(missing_ok=True)
        self.saved=None;self.keys=set();self.last={}

    def close(self):
        try:self.release()
        finally:self.client.disconnect()
