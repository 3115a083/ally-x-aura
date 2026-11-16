"""Frozen Windows CI check. No SDK connection, game capture or autostart writes."""
import importlib
from pathlib import Path
import sys
import time
import traceback
from .config import atomic_json


def run_smoke(output,data_dir=None):
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    data_dir=Path(data_dir or output.parent/'smoke-data').resolve()
    result={'frozen':bool(getattr(sys,'frozen',False)),'status':'fail','hardware_access':False,'checks':{}}
    root=None;app=None;icon=None
    try:
        for name in ('tkinter','openrgb','PIL.Image','PIL.ImageGrab','mss.windows','pystray','pystray._win32','win32com.client','win32timezone'):
            importlib.import_module(name);result['checks'][name]='pass'
        from .runtime import resource_root,launch_command
        resources=resource_root()
        for relative in ('mods/ZomboidAura/mod.info','mods/ZomboidAura/common/media/lua/client/ZomboidAura/Core.lua'):
            if not (resources/relative).is_file():raise RuntimeError('Missing bundled resource: '+relative)
        result['checks']['mod_resources']='pass'
        target,args,working=launch_command(resources/'app.py',data_dir)
        if result['frozen'] and target!=Path(sys.executable):raise RuntimeError('Frozen autostart does not target exe')
        result['checks']['autostart_target']='pass'
        import tkinter as tk
        import pystray
        from PIL import Image,ImageGrab
        from .ui import App
        root=tk.Tk();app=App(root,data_dir,demo=True)
        icon=pystray.Icon('AllyLightSmoke',Image.new('RGB',(32,32),'#70e1ce'),'AllyLight smoke')
        icon.run_detached();icon.visible=True
        result['checks']['native_tray_api']='pass'
        deadline=time.monotonic()+15
        def finish():
            if not app.status.get().startswith('Demo:') and time.monotonic()<deadline:
                root.after(200,finish);return
            try:
                if not app.status.get().startswith('Demo:'):raise RuntimeError('Frozen worker did not respond')
                if len(app.notebook.tabs())!=4:raise RuntimeError('Missing GUI pages')
                if not app.process.is_alive():raise RuntimeError('Frozen multiprocessing worker did not start')
                result['checks']['frozen_worker']='pass';result['checks']['gui_pages']='pass'
                root.lift();root.update_idletasks()
                box=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())
                ImageGrab.grab(bbox=box).save(output.with_suffix('.png'))
                result['status']='pass'
            except Exception:result['error']=traceback.format_exc()
            finally:app.quit()
        root.after(2500,finish);root.mainloop()
    except Exception:result['error']=traceback.format_exc()
    finally:
        if icon:
            try:icon.stop()
            except Exception:pass
        if app and app.process and app.process.is_alive():
            app.process.terminate();app.process.join(3)
        atomic_json(output,result)
    return 0 if result['status']=='pass' else 1
