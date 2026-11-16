from __future__ import annotations
import argparse
import multiprocessing as mp
import os
from pathlib import Path
import sys


def main():
    mp.freeze_support()
    parser=argparse.ArgumentParser(description='AllyLight Spielbeleuchtung')
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--tray',action='store_true')
    args=parser.parse_args()
    if sys.platform=='win32':
        import ctypes
        try:ctypes.windll.user32.SetProcessDPIAware()
        except Exception:pass
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


if __name__=='__main__':main()
