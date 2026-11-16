from types import SimpleNamespace
import copy
from openrgb.utils import ModeData,ModeColors,ModeFlags,RGBColor

class Device:
    def __init__(self,name='Ally',leds=4):
        self.name=name;self.type=10;self.metadata=SimpleNamespace(serial='',location=name,description='test')
        self.leds=list(range(leds));self.colors=[RGBColor(0,0,160) for _ in self.leds]
        self.modes=[ModeData(0,'Direct',0,ModeFlags(0),None,None,None,None,None,None,None,None,None,ModeColors.PER_LED,None)]
        self.active_mode=0;self.history=[];self.fail_restore=False
    def set_custom_mode(self):self.history.append('custom')
    def set_mode(self,mode):
        if self.fail_restore:raise RuntimeError('restore failed')
        self.history.append('mode');self.modes[0]=copy.deepcopy(mode)
    def set_colors(self,colors):self.history.append('colors');self.colors=copy.deepcopy(colors)

class Client:
    protocol_version=4
    def __init__(self):self.devices=[Device()];self.disconnected=False
    def update(self):pass
    def disconnect(self):self.disconnected=True
