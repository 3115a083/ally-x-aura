"""Execute shipped Lua with mocked B41/B42 APIs, without game or hardware."""
import json
from pathlib import Path
import unittest
try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

@unittest.skipIf(LuaRuntime is None, "Install requirements-test.txt for Lua regression tests")
class LuaTelemetryTests(unittest.TestCase):
    def runtime(self, mode):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''now=1000; frames={}; warnings={}; calls=0
getTimestampMs=function() return now end
getFileReader=function() return nil end
getFileWriter=function(path) return {write=function(self,text) frames[#frames+1]=text end,close=function() end} end
print=function(text) warnings[#warnings+1]=text end
Events={OnTick={Add=function(fn) tick=fn end}}
body={getOverallBodyHealth=function() return 75 end}
stats={}
player={getBodyDamage=function() return body end,getStats=function() calls=calls+1; return stats end}
getSpecificPlayer=function(i) if i==0 then return player end end
''')
        if mode == "b42":
            lua.execute('CharacterStat={ENDURANCE="endurance"}; stats.get=function(self,key) assert(key==CharacterStat.ENDURANCE); return 0.6 end')
        elif mode == "b41":
            lua.execute('stats.getEndurance=function() return 0.4 end')
        lua.execute(Path('mods/ZomboidAura/common/media/lua/client/ZomboidAura/Core.lua').read_text())
        return lua

    def test_b42_without_legacy_getter(self):
        lua=self.runtime("b42"); lua.execute('tick()')
        frame=json.loads(lua.globals().frames[1])
        self.assertEqual(frame['players'][0]['endurance'],0.6)
        self.assertEqual(frame['players'][0]['health'],0.75)
        lua.execute('now=1100; tick()')
        self.assertEqual(len(lua.globals().frames),2)

    def test_b41_legacy_getter(self):
        lua=self.runtime("b41"); lua.execute('tick()')
        self.assertEqual(json.loads(lua.globals().frames[1])['players'][0]['endurance'],0.4)

    def test_unknown_api_stops_without_repeated_calls(self):
        lua=self.runtime("missing"); lua.execute('tick(); for i=1,100 do now=now+100; tick() end')
        self.assertEqual(lua.globals().calls,1)
        self.assertEqual(len(lua.globals().warnings),1)
        self.assertEqual(len(lua.globals().frames),0)
        self.assertTrue(lua.globals().ZomboidAura.telemetryStopped)

    def test_layouts_match(self):
        base=Path('mods/ZomboidAura')
        self.assertEqual((base/'media/lua/client/ZomboidAura/Core.lua').read_bytes(),(base/'common/media/lua/client/ZomboidAura/Core.lua').read_bytes())
