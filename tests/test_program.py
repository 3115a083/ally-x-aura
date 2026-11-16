import copy
import json
import multiprocessing as mp
import os
from pathlib import Path
import queue
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from allylight.config import default_config,validate,save,load,new_zone
from allylight.backend import OpenRGBBackend
from allylight.openrgb_state import identities
from allylight.sources import choose_profile,matches,read_zomboid,dominant_color,smooth,ScreenSource
from allylight.engine import output_frames,worker
from allylight.windows import SingleInstance
from helpers import Client
from PIL import Image,ImageDraw


def configured():
    cfg=default_config();cfg['automation']=True
    cfg['zones']=[{'id':'left','name':'Links','device':'test','leds':[0,1],'offset':0,'reverse':False},
                  {'id':'right','name':'Rechts','device':'test','leds':[2,3],'offset':0,'reverse':False}]
    p=cfg['profiles'][0];p['enabled']=True
    p['routes']=[{'zone':'left','mode':'health','brightness':1.,'player':0,'category':'all','color':[0,0,255]},
                 {'zone':'right','mode':'endurance','brightness':.5,'player':0,'category':'all','color':[0,0,255]}]
    return cfg


class ConfigTests(unittest.TestCase):
    def test_first_run_does_not_take_control(self):
        c=validate(default_config());self.assertFalse(c['automation']);self.assertFalse(c['start_openrgb'])
        self.assertTrue(all(not p['enabled'] for p in c['profiles']))
    def test_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'config.json';save(p,configured());self.assertEqual(load(p),configured())
    def test_overlapping_zones_rejected(self):
        c=configured();c['zones'][1]['leds']=[1,2]
        with self.assertRaises(ValueError):validate(c)
    def test_missing_zone_rejected(self):
        c=configured();c['zones'].pop()
        with self.assertRaises(ValueError):validate(c)
    def test_invalid_numeric_values(self):
        for value in (float('nan'),float('inf'),-1,2,True):
            c=configured();c['profiles'][0]['routes'][0]['brightness']=value
            with self.assertRaises(ValueError):validate(c)
    def test_profile_source_modes_are_checked(self):
        c=configured();c['profiles'][0]['routes'][0]['mode']='screen'
        with self.assertRaises(ValueError):validate(c)
    def test_no_executable_is_guessed_from_substring(self):
        self.assertTrue(matches(r'C:\Games\Hue.exe',['Hue.exe']))
        self.assertFalse(matches(r'C:\Games\Hue.exe.old',['Hue.exe']))
        self.assertFalse(matches(r'C:\Other\Hue.exe',[r'C:\Games\Hue.exe']))
    def test_desktop_restores_by_matching_no_profile(self):
        c=configured()
        self.assertIsNone(choose_profile(c,{'exe':r'C:\Windows\explorer.exe'}))
        self.assertEqual(choose_profile(c,{'exe':r'C:\Games\ProjectZomboid64.exe'})['id'],'zomboid')
        c['automation']=False;self.assertIsNone(choose_profile(c,{'exe':'ProjectZomboid64.exe'}))


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.client=Client()
        self.backend=OpenRGBBackend(self.temp.name,self.client);self.key=next(iter(identities(self.client)))
    def tearDown(self):self.temp.cleanup()
    def test_partial_zone_keeps_other_leds_and_restores(self):
        self.backend.apply({self.key:{0:(30,0,0)}})
        d=self.client.devices[0]
        self.assertEqual((d.colors[0].red,d.colors[1].blue),(30,160))
        self.assertTrue(self.backend.pending.exists())
        self.backend.release();self.assertEqual(d.colors[0].blue,160)
        self.assertFalse(self.backend.pending.exists())
    def test_repeated_frames_do_not_write_again(self):
        frame={self.key:{1:(30,0,0)}};self.backend.apply(frame);count=len(self.client.devices[0].history)
        self.backend.apply(frame);self.assertEqual(len(self.client.devices[0].history),count)
        self.backend.close();self.assertTrue(self.client.disconnected)
    def test_saved_before_first_mode_change(self):
        d=self.client.devices[0];original=d.set_custom_mode
        def check():self.assertTrue(self.backend.pending.exists());original()
        d.set_custom_mode=check;self.backend.apply({self.key:{0:(0,30,0)}});self.backend.release()
    def test_failed_restore_keeps_recovery_file(self):
        self.backend.apply({self.key:{0:(30,0,0)}});self.client.devices[0].fail_restore=True
        with self.assertRaises(RuntimeError):self.backend.release()
        self.assertTrue(self.backend.pending.exists())
    def test_new_session_recovers_pending_snapshot(self):
        self.backend.apply({self.key:{0:(30,0,0)}})
        second=OpenRGBBackend(self.temp.name,self.client);second.recover()
        self.assertEqual(self.client.devices[0].colors[0].blue,160);self.assertFalse(second.pending.exists())
    def test_black_baseline_is_blocked(self):
        from openrgb.utils import RGBColor
        self.client.devices[0].colors=[RGBColor(0,0,0)]*4
        with self.assertRaises(ValueError):self.backend.apply({self.key:{0:(30,0,0)}})
        self.assertEqual(self.client.devices[0].history,[])
    def test_stop_without_claim_does_not_touch_lights(self):
        self.backend.close();self.assertEqual(self.client.devices[0].history,[])


class SourceTests(unittest.TestCase):
    def test_black_geometry_does_not_darken_hue(self):
        image=Image.new('RGB',(300,200),(200,30,100));ImageDraw.Draw(image).rectangle((0,150,299,199),fill='black')
        color=dominant_color(image)
        self.assertLess(abs(color[0]-200),5);self.assertLess(abs(color[2]-100),5)
    def test_most_common_hue_not_rgb_average(self):
        image=Image.new('RGB',(300,200),(0,0,220));ImageDraw.Draw(image).rectangle((0,0,80,199),fill=(220,0,0))
        color=dominant_color(image);self.assertGreater(color[2],200);self.assertLess(color[0],10)
    def test_black_and_white_menu_have_no_color(self):
        self.assertIsNone(dominant_color(Image.new('RGB',(100,100),'black')))
        self.assertIsNone(dominant_color(Image.new('RGB',(100,100),'white')))
    def test_smoothing(self):self.assertEqual(smooth((0,0,0),(100,200,250),.5),(50,100,125))
    def test_stale_and_partial_telemetry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'za-frame-0.json'
            frame={'protocol':1,'seq':1,'session':'test','players':[{'id':0,'health':.7,'endurance':.4,'sounds':[]}],'routes':[]}
            path.write_text(json.dumps(frame));self.assertEqual(read_zomboid(tmp)['players'][0]['health'],.7)
            (Path(tmp)/'za-frame-1.json').write_text('{')
            self.assertIsNotNone(read_zomboid(tmp));os.utime(path,(time.time()-5,time.time()-5));self.assertIsNone(read_zomboid(tmp))
    def test_hue_frame_discarded_when_focus_changes(self):
        class Reader:
            count=0
            def current(self):
                self.count+=1;return {'hwnd':1 if self.count==1 else 2,'exe':'Hue.exe','rect':{}}
        class Capture:
            def grab(self,rect):return object()
        screen=ScreenSource();screen.capture=Capture()
        self.assertIsNone(screen.color({'hwnd':1,'exe':'Hue.exe','rect':{}},Reader()))
    def test_two_zones_receive_different_game_values(self):
        c=configured();frames=output_frames(c,c['profiles'][0],[{'id':0,'health':0.,'endurance':1.,'sounds':[]}])
        self.assertEqual(frames['test'][0],(255,0,0));self.assertEqual(frames['test'][2],(0,100,128))
    def test_missing_player_does_not_claim_zone(self):
        c=configured();self.assertEqual(output_frames(c,c['profiles'][0],[]),{})


class LifecycleTests(unittest.TestCase):
    def test_single_instance_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=SingleInstance(Path(tmp)/'lock');b=SingleInstance(Path(tmp)/'lock')
            self.assertTrue(a.acquire());self.assertFalse(b.acquire());a.close()
            self.assertTrue(b.acquire());b.close()
    def test_isolated_demo_engine_stops_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            commands=mp.Queue();events=mp.Queue()
            p=mp.Process(target=worker,args=(commands,events,default_config(),tmp,True));p.start()
            try:
                event=events.get(timeout=5);self.assertEqual(event['type'],'status')
                commands.put({'type':'stop'});p.join(5);self.assertFalse(p.is_alive())
                self.assertFalse((Path(tmp)/'snapshots/pending.json').exists())
            finally:
                if p.is_alive():p.terminate();p.join()


if __name__=='__main__':unittest.main()
