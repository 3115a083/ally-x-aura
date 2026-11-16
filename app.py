from __future__ import annotations
import argparse
import multiprocessing as mp
import os
from pathlib import Path
import sys


def main():
    mp.freeze_support()
    # Windows GUI bundles have no console streams. Some dependencies expect them.
    if sys.stdout is None:sys.stdout=open(os.devnull,'w')
    if sys.stderr is None:sys.stderr=open(os.devnull,'w')
    parser=argparse.ArgumentParser(description='AllyLight Spielbeleuchtung')
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--tray',action='store_true')
    parser.add_argument('--smoke-test',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if sys.platform=='win32':
        import ctypes
        try:ctypes.windll.user32.SetProcessDPIAware()
        except Exception:pass
    if args.smoke_test:
        from allylight.smoke import run_smoke
        return run_smoke(args.smoke_test,args.data_dir)
    import tkinter as tk
    from tkinter import messagebox
    from allylight.windows import SingleInstance
    from allylight.ui import App
    data=args.data_dir or ((Path(os.environ['LOCALAPPDATA'])/'AllyLight') if sys.platform=='win32' else Path(__file__).resolve().parent/'data')
    data.mkdir(parents=True,exist_ok=True)
    lock=SingleInstance(data/'instance.lock')
    root=tk.Tk()
    if not lock.acquire():
        root.withdraw();messagebox.showinfo('AllyLight','AllyLight laeuft bereits. Das Symbol im Windows-Infobereich oeffnen.');root.destroy();return
    try:
        App(root,data,args.demo,args.tray);root.mainloop()
    finally:lock.close()


if __name__=='__main__':
    try:
        code=main()
    except Exception:
        import traceback
        log_dir=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'AllyLight'/'logs'
        log_dir.mkdir(parents=True,exist_ok=True)
        path=log_dir/'startup-error.log';path.write_text(traceback.format_exc(),encoding='utf-8')
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,'AllyLight konnte nicht starten. Fehlerbericht: '+str(path),'AllyLight',0x10)
        except Exception:pass
        code=1
    raise SystemExit(code or 0)
