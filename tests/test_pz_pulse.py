"""Synthetic Pulse fixtures only. Never commit user exports."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from allylight.sources import read_pz_pulse, read_zomboid
from allylight.engine import output_frames
from test_program import configured

class PulseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.pulse=self.root/'PZ_Pulse';self.pulse.mkdir()
        self.now=time.time()
        self.payload={'health':{'overall':63},'needs':[{'label':'Stamina','value':42,'badHigh':False}]}
        self.write()
        (self.pulse/'heartbeat.txt').write_text('synthetic heartbeat')
    def write(self,tail=';\nwindow.PZ_DATA.seq = 35;'):
        (self.pulse/'data.txt').write_text('window.PZ_DATA = '+json.dumps(self.payload)+tail)
    def test_health_and_stamina_percentages(self):
        f=read_pz_pulse(self.root,self.now)
        self.assertEqual(f['players'][0],{'id':0,'health':.63,'endurance':.42,'sounds':[],'sound_available':False})
        self.assertEqual(read_pz_pulse(self.pulse,self.now),f)
    def test_unchanged_data_with_live_heartbeat_is_valid(self):
        os.utime(self.pulse/'data.txt',(self.now-3600,)*2)
        self.assertIsNotNone(read_pz_pulse(self.root,self.now))
    def test_stale_or_missing_heartbeat_releases_data(self):
        os.utime(self.pulse/'heartbeat.txt',(self.now-10,)*2)
        self.assertIsNone(read_pz_pulse(self.root,self.now))
        (self.pulse/'heartbeat.txt').unlink()
        self.assertIsNone(read_pz_pulse(self.root,self.now))
    def test_never_execute_javascript_or_accept_partial_writes(self):
        for tail in ('; alert(1);','; window.PZ_DATA.seq = 35; alert(1);',''):
            self.write(tail);self.assertIsNone(read_pz_pulse(self.root,self.now))
    def test_invalid_or_missing_values_are_not_invented(self):
        for value in (None,True,-1,101,float('nan')):
            self.payload['health']['overall']=value;self.write()
            self.assertIsNone(read_pz_pulse(self.root,self.now))
        self.payload['health']['overall']=100;self.payload['needs']=[];self.write()
        self.assertIsNone(read_pz_pulse(self.root,self.now))
    def test_auto_prefers_pulse_and_never_falls_back_to_old_addon(self):
        addon={'protocol':1,'session':'addon','seq':1,'players':[],'routes':[]}
        (self.root/'za-frame-0.json').write_text(json.dumps(addon))
        self.assertEqual(read_zomboid(self.root,self.now)['source'],'pz-pulse')
        self.assertEqual(read_zomboid(self.root,self.now,source='addon'),addon)
        os.utime(self.pulse/'heartbeat.txt',(self.now-10,)*2)
        self.assertIsNone(read_zomboid(self.root,self.now))
    def test_sound_only_and_other_players_do_not_claim_leds(self):
        cfg=configured();p=cfg['profiles'][0];players=read_pz_pulse(self.root,self.now)['players']
        p['routes'][0]['mode']='sound';p['routes'][1]['player']=1
        self.assertEqual(output_frames(cfg,p,players),{})
    def test_oversize_export_rejected(self):
        (self.pulse/'data.txt').write_bytes(b'x'*2_000_001)
        self.assertIsNone(read_pz_pulse(self.root,self.now))
