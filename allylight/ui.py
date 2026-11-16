from __future__ import annotations
import copy
import json
import multiprocessing as mp
import os
from pathlib import Path
import queue
import shutil
import sys
import time
import tkinter as tk
from tkinter import ttk,messagebox,filedialog,colorchooser
import uuid
from . import __version__
from .config import load,save,validate,new_zone,MODES
from .engine import worker,recover_process
from .windows import set_autostart,autostart_enabled,launch_openrgb

MODE_LABELS={'health':'Gesundheit','endurance':'Ausdauer','sound':'Geraeuschrichtung','combined':'Gesundheit + Geraeusch','screen':'Bildschirmfarbe','static':'Feste Farbe'}
LABEL_MODES={v:k for k,v in MODE_LABELS.items()}


class App:
    def __init__(self,root,data_dir,demo=False,start_tray=False):
        self.root=root;self.data_dir=Path(data_dir);self.demo=demo
        self.config_path=self.data_dir/'config.json'
        try:self.cfg=load(self.config_path)
        except Exception as exc:
            messagebox.showerror('Konfiguration kann nicht geladen werden',str(exc));raise
        self.devices=[];self.events=mp.Queue();self.commands=None;self.process=None
        self.last_seen=time.monotonic();self.last_heartbeat=0;self.closing=False;self.close_at=0;self.recovering=False;self.tray=None
        self.tray_actions=queue.Queue();self.messages=[];self.profile_drafts={};self._loading_profile=False
        self.root.title('AllyLight | Spielbeleuchtung');self.root.geometry('1060x720');self.root.minsize(850,620)
        self.root.configure(bg='#111827');self.style()
        top=ttk.Frame(root,padding=(22,18));top.pack(fill='x')
        ttk.Label(top,text='AllyLight',style='Title.TLabel').pack(side='left')
        ttk.Label(top,text='  '+__version__+'  |  OpenRGB',style='Muted.TLabel').pack(side='left',padx=8)
        self.toggle=ttk.Button(top,text='',command=self.toggle_automation);self.toggle.pack(side='right')
        self.notebook=ttk.Notebook(root);self.notebook.pack(fill='both',expand=True,padx=20,pady=(0,16))
        self.pages={}
        for name in ('Uebersicht','Geraete & Zonen','Spielprofile','Einstellungen'):
            page=ttk.Frame(self.notebook,padding=20);self.notebook.add(page,text=name);self.pages[name]=page
        self.build_overview();self.build_devices();self.build_profiles();self.build_settings()
        self.root.protocol('WM_DELETE_WINDOW',self.close_window)
        self.set_toggle();self.refresh_profiles();self.refresh_zones()
        self.setup_tray()
        if start_tray and self.tray:self.root.withdraw()
        if self.cfg['start_openrgb'] and self.cfg['openrgb_exe'] and not demo:
            try:launch_openrgb(self.cfg['openrgb_exe'])
            except Exception as exc:self.log(str(exc))
        self.start_engine()
        if demo:self.events.put({'type':'devices','devices':[{'id':'demo-device','name':'Demo-Handheld (keine Hardware)','led_count':4,'active_mode':'Demo'}]})
        self.root.after(150,self.poll)

    def style(self):
        s=ttk.Style();s.theme_use('clam')
        s.configure('.',font=('Segoe UI',11),background='#172033',foreground='#e5e7eb')
        s.configure('TFrame',background='#172033');s.configure('TLabel',background='#172033',foreground='#e5e7eb')
        s.configure('Title.TLabel',font=('Segoe UI',25,'bold'),foreground='#70e1ce')
        s.configure('Heading.TLabel',font=('Segoe UI',17,'bold'))
        s.configure('Muted.TLabel',foreground='#a7b3c8')
        s.configure('TButton',padding=(12,9),background='#283850',foreground='#f3f4f6',borderwidth=0)
        s.map('TButton',background=[('active','#375071')])
        s.configure('TNotebook',background='#111827',borderwidth=0)
        s.configure('TNotebook.Tab',padding=(20,12),background='#1d2b42',foreground='#b8c6db')
        s.map('TNotebook.Tab',background=[('selected','#29455a')],foreground=[('selected','#91f3de')])
        s.configure('Treeview',rowheight=32,fieldbackground='#111b2b',background='#111b2b',foreground='#e5e7eb',borderwidth=0)
        s.configure('Treeview.Heading',background='#283850',foreground='#dfe8f4',padding=6)
        s.map('Treeview',background=[('selected','#235c68')])
        s.configure('TEntry',fieldbackground='#0e1727',foreground='#edf2f7',padding=7)
        s.configure('TCombobox',fieldbackground='#e2e8f0',foreground='#111827',padding=5)
        s.map('TCombobox',fieldbackground=[('readonly','#e2e8f0')],foreground=[('readonly','#111827')])
        s.configure('TCheckbutton',background='#172033',foreground='#e5e7eb',padding=5)

    def heading(self,parent,title,subtitle):
        ttk.Label(parent,text=title,style='Heading.TLabel').pack(anchor='w')
        ttk.Label(parent,text=subtitle,style='Muted.TLabel',wraplength=900).pack(anchor='w',pady=(5,18))

    def build_overview(self):
        p=self.pages['Uebersicht'];self.heading(p,'Beleuchtung passend zum Spiel','OpenRGB steuert die LEDs. AllyLight verbindet sie mit deinen Spielprofilen.')
        self.status=tk.StringVar(value='Verbinde mit OpenRGB ...');self.game_status=tk.StringVar(value='Kein aktives Spielprofil')
        ttk.Label(p,textvariable=self.status,font=('Segoe UI',15),wraplength=900).pack(anchor='w',pady=12)
        ttk.Label(p,textvariable=self.game_status,style='Muted.TLabel').pack(anchor='w')
        self.swatch=tk.Canvas(p,width=100,height=50,bg='#111827',highlightthickness=0);self.swatch.pack(anchor='w',pady=15)
        row=ttk.Frame(p);row.pack(fill='x',pady=8)
        for label,fn in [('Neu verbinden',self.refresh_devices),('Wiederherstellen',self.restore),('In den Infobereich',self.hide),('Beenden',self.quit)]:
            ttk.Button(row,text=label,command=fn).pack(side='left',padx=(0,10))
        ttk.Label(p,text='Start: Geraete laden, LEDs einzeln testen, Zonen anlegen und einem Spielprofil zuordnen.',wraplength=900,style='Muted.TLabel').pack(anchor='w',pady=14)
        self.logbox=tk.Text(p,height=9,bg='#101827',fg='#a9bdd6',font=('Consolas',10),relief='flat',padx=12,pady=10,state='disabled')
        self.logbox.pack(fill='both',expand=True)

    def build_devices(self):
        p=self.pages['Geraete & Zonen'];self.heading(p,'Geraete und LED-Zonen','Erst einzeln testen. Vier SDK-LEDs bedeuten nicht zwingend vier physisch getrennte Leuchten.')
        self.device_tree=ttk.Treeview(p,columns=('name','leds','mode'),show='headings',height=3)
        for col,label,w in [('name','OpenRGB-Geraet',490),('leds','LEDs',75),('mode','Modus',160)]:self.device_tree.heading(col,text=label);self.device_tree.column(col,width=w)
        self.device_tree.pack(fill='x');self.device_tree.bind('<<TreeviewSelect>>',self.device_selected)
        test=ttk.Frame(p);test.pack(fill='x',pady=10)
        ttk.Label(test,text='LED-Index:').pack(side='left');self.led_index=tk.StringVar(value='0')
        ttk.Spinbox(test,from_=0,to=8191,textvariable=self.led_index,width=6).pack(side='left',padx=8)
        ttk.Button(test,text='Diese LED 2 Sekunden testen',command=self.test_led).pack(side='left')
        ttk.Button(test,text='Geraete neu laden',command=self.refresh_devices).pack(side='right')
        self.zone_tree=ttk.Treeview(p,columns=('name','device','leds'),show='headings',height=5)
        for col,label,w in [('name','Zone',220),('device','Geraet',370),('leds','LED-Indizes in Reihenfolge',200)]:self.zone_tree.heading(col,text=label);self.zone_tree.column(col,width=w)
        self.zone_tree.pack(fill='both',expand=True,pady=8)
        row=ttk.Frame(p);row.pack(fill='x')
        for label,fn in [('Zone anlegen',lambda:self.zone_dialog()),('Zone bearbeiten',self.edit_zone),('Zone entfernen',self.remove_zone)]:ttk.Button(row,text=label,command=fn).pack(side='left',padx=(0,10))

    def device_selected(self,event=None):
        ids=self.device_tree.selection()
        if ids:
            device=next(d for d in self.devices if d['id']==ids[0]);self.led_index.set('0')

    def build_profiles(self):
        p=self.pages['Spielprofile'];self.heading(p,'Profile fuer deine Spiele','Aktiv wird nur das Profil des Vordergrundspiels. Auf dem Desktop kehrt die Ausgangsbeleuchtung zurueck.')
        row=ttk.Frame(p);row.pack(fill='x')
        self.profile_choice=tk.StringVar();self.profile_combo=ttk.Combobox(row,textvariable=self.profile_choice,state='readonly',width=30)
        self.profile_combo.pack(side='left');self.profile_combo.bind('<<ComboboxSelected>>',lambda e:self.load_profile_form())
        ttk.Button(row,text='Profil hinzufuegen',command=self.add_profile).pack(side='left',padx=10)
        self.profile_enabled=tk.BooleanVar();ttk.Checkbutton(row,text='Profil aktiv',variable=self.profile_enabled).pack(side='right')
        ttk.Label(p,text='Programmdateien oder volle Pfade, durch Semikolon getrennt',style='Muted.TLabel').pack(anchor='w',pady=(18,4))
        self.exe_var=tk.StringVar();ttk.Entry(p,textvariable=self.exe_var).pack(fill='x')
        self.exe_var.trace_add('write',self.keep_profile_draft)
        self.profile_enabled.trace_add('write',self.keep_profile_draft)
        row=ttk.Frame(p);row.pack(fill='x',pady=8)
        ttk.Button(row,text='Programmdatei waehlen',command=self.pick_game).pack(side='left')
        ttk.Button(row,text='Vordergrundspiel in 5 Sekunden uebernehmen',command=self.capture_foreground).pack(side='left',padx=8)
        self.route_tree=ttk.Treeview(p,columns=('zone','mode','brightness','player'),show='headings',height=5)
        for col,label,w in [('zone','LED-Zone',260),('mode','Anzeige',250),('brightness','Helligkeit',100),('player','Spieler',80)]:self.route_tree.heading(col,text=label);self.route_tree.column(col,width=w)
        self.route_tree.pack(fill='both',expand=True,pady=12)
        row=ttk.Frame(p);row.pack(fill='x')
        for label,fn in [('Anzeige zuordnen',lambda:self.route_dialog()),('Anzeige bearbeiten',self.edit_route),('Entfernen',self.remove_route),('Profil speichern',self.save_profile_form)]:ttk.Button(row,text=label,command=fn).pack(side='left',padx=(0,8))

    def build_settings(self):
        p=self.pages['Einstellungen'];self.heading(p,'Verbindungen und Start','AllyLight verbindet sich lokal mit dem OpenRGB-SDK-Server auf Port 6742.')
        ttk.Label(p,text='Zomboid-Lua-Ordner').pack(anchor='w')
        self.cache_var=tk.StringVar(value=self.cfg['cache']);ttk.Entry(p,textvariable=self.cache_var).pack(fill='x',pady=6)
        row=ttk.Frame(p);row.pack(fill='x')
        ttk.Button(row,text='Ordner waehlen',command=self.pick_cache).pack(side='left')
        ttk.Button(row,text='Zomboid-Mod installieren',command=self.install_mod).pack(side='left',padx=10)
        ttk.Label(p,text='OpenRGB.exe, optional fuer den gemeinsamen Start').pack(anchor='w',pady=(22,0))
        self.openrgb_var=tk.StringVar(value=self.cfg['openrgb_exe']);ttk.Entry(p,textvariable=self.openrgb_var).pack(fill='x',pady=6)
        row=ttk.Frame(p);row.pack(fill='x')
        ttk.Button(row,text='OpenRGB.exe waehlen',command=self.pick_openrgb).pack(side='left')
        ttk.Button(row,text='OpenRGB jetzt starten',command=self.openrgb_now).pack(side='left',padx=10)
        self.start_rgb=tk.BooleanVar(value=self.cfg['start_openrgb']);ttk.Checkbutton(p,text='OpenRGB beim Start von AllyLight mitstarten',variable=self.start_rgb).pack(anchor='w',pady=(14,0))
        self.autostart=tk.BooleanVar(value=autostart_enabled());ttk.Checkbutton(p,text='AllyLight bei der Windows-Anmeldung starten',variable=self.autostart,command=self.change_autostart).pack(anchor='w')
        ttk.Label(p,text='Autostart ist optional. OpenRGB muss im Direct- oder Static-Modus starten. Dynamische Ausgangseffekte werden vorerst abgelehnt.',wraplength=900,style='Muted.TLabel').pack(anchor='w',pady=12)
        row=ttk.Frame(p);row.pack(fill='x',pady=8)
        ttk.Button(row,text='Einstellungen speichern',command=self.save_settings).pack(side='left')
        ttk.Button(row,text='Datenordner oeffnen',command=self.open_data).pack(side='left',padx=10)
        ttk.Button(row,text='Diagnosebericht speichern',command=self.export_report).pack(side='left')

    def start_engine(self):
        self.commands=mp.Queue();self.process=mp.Process(target=worker,args=(self.commands,self.events,self.cfg,str(self.data_dir),self.demo),daemon=False)
        self.process.start();self.last_seen=time.monotonic();self.recovering=False

    def send(self,message):
        if self.process and self.process.is_alive() and not self.recovering:self.commands.put(message)

    def commit(self):
        validate(self.cfg);save(self.config_path,self.cfg);self.send({'type':'config','config':self.cfg});self.set_toggle()

    def set_toggle(self):self.toggle.configure(text='Automatik pausieren' if self.cfg['automation'] else 'Automatik einschalten')

    def toggle_automation(self):
        self.cfg['automation']=not self.cfg['automation'];self.commit()

    def refresh_devices(self):
        if self.process and not self.process.is_alive() and not self.closing:self.start_engine()
        self.send({'type':'refresh'})

    def restore(self):
        self.cfg['automation']=False;self.commit();self.send({'type':'restore'})

    def test_led(self):
        try:
            ids=self.device_tree.selection()
            if not ids:raise ValueError('Zuerst ein Geraet waehlen.')
            device=next(d for d in self.devices if d['id']==ids[0]);index=int(self.led_index.get())
            if not 0<=index<device['led_count']:raise ValueError('Index liegt ausserhalb des Geraets.')
            self.send({'type':'preview','device':device['id'],'leds':[index]})
        except Exception as exc:self.error(exc)

    def refresh_zones(self):
        self.zone_tree.delete(*self.zone_tree.get_children());names={d['id']:d['name'] for d in self.devices}
        for z in self.cfg['zones']:
            self.zone_tree.insert('', 'end',iid=z['id'],values=(z['name'],names.get(z['device'],'Nicht verbunden'),','.join(map(str,z['leds']))))
        if hasattr(self,'route_tree'):self.refresh_routes()

    def edit_zone(self):
        ids=self.zone_tree.selection()
        if ids:self.zone_dialog(next(z for z in self.cfg['zones'] if z['id']==ids[0]))

    def zone_dialog(self,existing=None):
        if not self.devices:self.error('Keine OpenRGB-Geraete. SDK-Server starten und neu verbinden.');return
        win=tk.Toplevel(self.root);win.title('LED-Zone');win.geometry('540x400');win.transient(self.root);win.grab_set()
        box=ttk.Frame(win,padding=22);box.pack(fill='both',expand=True)
        name=tk.StringVar(value=existing['name'] if existing else 'Neue Zone')
        leds=tk.StringVar(value=','.join(map(str,existing['leds'])) if existing else '0')
        labels=[f"{i}: {d['name']} ({d['led_count']} LEDs)" for i,d in enumerate(self.devices)]
        selected=next((i for i,d in enumerate(self.devices) if existing and d['id']==existing['device']),0)
        device=tk.StringVar(value=labels[selected]);offset=tk.StringVar(value=str(existing.get('offset',0)) if existing else '0');reverse=tk.BooleanVar(value=existing.get('reverse',False) if existing else False)
        for title,var in [('Name',name)]:ttk.Label(box,text=title).pack(anchor='w');ttk.Entry(box,textvariable=var).pack(fill='x',pady=(3,10))
        ttk.Label(box,text='Geraet').pack(anchor='w');ttk.Combobox(box,textvariable=device,values=labels,state='readonly').pack(fill='x',pady=(3,10))
        ttk.Label(box,text='LED-Indizes, z. B. 0,1. Reihenfolge bestimmt die Richtung.').pack(anchor='w');ttk.Entry(box,textvariable=leds).pack(fill='x',pady=(3,10))
        ttk.Label(box,text='Winkelkorrektur in Grad').pack(anchor='w');ttk.Entry(box,textvariable=offset).pack(fill='x',pady=(3,8));ttk.Checkbutton(box,text='Richtungsreihenfolge umkehren',variable=reverse).pack(anchor='w')
        def apply():
            try:
                d=self.devices[labels.index(device.get())];indices=[int(i.strip()) for i in leds.get().split(',')]
                if any(i>=d['led_count'] for i in indices):raise ValueError('LED-Index zu gross.')
                z=new_zone(name.get().strip(),d['id'],indices,float(offset.get()),reverse.get())
                if existing:z['id']=existing['id']
                candidate=copy.deepcopy(self.cfg);candidate['zones']=[x for x in candidate['zones'] if x['id']!=z['id']]+[z];validate(candidate)
                self.cfg=candidate;self.commit();self.refresh_zones();win.destroy()
            except Exception as exc:self.error(exc)
        ttk.Button(box,text='Zone speichern',command=apply).pack(anchor='e',pady=10)

    def remove_zone(self):
        ids=self.zone_tree.selection()
        if not ids:return
        self.cfg['zones']=[z for z in self.cfg['zones'] if z['id']!=ids[0]]
        for p in self.cfg['profiles']:p['routes']=[r for r in p['routes'] if r['zone']!=ids[0]]
        self.commit();self.refresh_zones()

    def profile(self):
        index=self.profile_combo.current()
        return self.cfg['profiles'][index] if index>=0 else None

    def refresh_profiles(self):
        self.profile_combo['values']=[p['name'] for p in self.cfg['profiles']]
        if self.cfg['profiles']:self.profile_combo.current(0);self.load_profile_form()

    def keep_profile_draft(self,*args):
        p=self.profile()
        if p and not self._loading_profile:
            self.profile_drafts[p['id']]={'executables':self.exe_var.get(),'enabled':self.profile_enabled.get()}

    def load_profile_form(self):
        p=self.profile()
        if p:
            draft=self.profile_drafts.get(p['id'],{'executables':'; '.join(p['executables']),'enabled':p['enabled']})
            self._loading_profile=True
            try:self.exe_var.set(draft['executables']);self.profile_enabled.set(draft['enabled'])
            finally:self._loading_profile=False
        self.refresh_routes()

    def refresh_routes(self):
        self.route_tree.delete(*self.route_tree.get_children());p=self.profile()
        names={z['id']:z['name'] for z in self.cfg['zones']}
        if p:
            for i,r in enumerate(p['routes']):self.route_tree.insert('', 'end',iid=str(i),values=(names.get(r['zone'],'?'),MODE_LABELS[r['mode']],f"{round(r['brightness']*100)} %",r['player']+1))

    def save_profile_form(self):
        try:
            p=self.profile()
            if not p:return
            p['executables']=[s.strip().strip('"') for s in self.exe_var.get().split(';') if s.strip()];p['enabled']=self.profile_enabled.get()
            self.commit();self.log('Profil gespeichert: '+p['name'])
        except Exception as exc:self.error(exc)

    def add_profile(self):
        win=tk.Toplevel(self.root);win.title('Profil hinzufuegen');win.geometry('430x250');win.transient(self.root);win.grab_set()
        b=ttk.Frame(win,padding=20);b.pack(fill='both',expand=True)
        name=tk.StringVar(value='Neues Profil');source=tk.StringVar(value='hue')
        ttk.Label(b,text='Profilname').pack(anchor='w');ttk.Entry(b,textvariable=name).pack(fill='x',pady=8)
        ttk.Label(b,text='Datenquelle: hue oder zomboid').pack(anchor='w');ttk.Combobox(b,textvariable=source,values=['hue','zomboid'],state='readonly').pack(fill='x',pady=8)
        def add():
            self.cfg['profiles'].append({'id':uuid.uuid4().hex,'name':name.get().strip() or 'Profil','source':source.get(),'enabled':False,'executables':[],'routes':[]})
            self.commit();self.refresh_profiles();self.profile_combo.current(len(self.cfg['profiles'])-1);self.load_profile_form();win.destroy()
        ttk.Button(b,text='Hinzufuegen',command=add).pack(anchor='e',pady=8)

    def pick_game(self):
        value=filedialog.askopenfilename(filetypes=[('Windows-Programm','*.exe'),('Alle Dateien','*')])
        if value:self.exe_var.set(value)

    def capture_foreground(self):
        self.log('Jetzt zum Spiel wechseln. Erkennung in 5 Sekunden ...')
        def read():
            try:
                from .sources import WindowsForeground
                current=WindowsForeground().current()
                if not current:raise ValueError('Vordergrundprogramm konnte nicht erkannt werden.')
                self.exe_var.set(current['exe']);self.log('Programmdatei uebernommen. Profil speichern.')
            except Exception as exc:self.error(exc)
        self.root.after(5000,read)

    def edit_route(self):
        selected=self.route_tree.selection()
        if selected:self.route_dialog(int(selected[0]))

    def route_dialog(self,index=None):
        p=self.profile()
        if not p or not self.cfg['zones']:self.error('Zuerst eine LED-Zone anlegen.');return
        route=p['routes'][index] if index is not None else None
        win=tk.Toplevel(self.root);win.title('Anzeige zuordnen');win.geometry('520x460');win.transient(self.root);win.grab_set()
        b=ttk.Frame(win,padding=22);b.pack(fill='both',expand=True)
        zones=self.cfg['zones'];labels=[f"{i+1}: {z['name']}" for i,z in enumerate(zones)]
        selected=next((i for i,z in enumerate(zones) if route and route['zone']==z['id']),0)
        zone=tk.StringVar(value=labels[selected]);modes=['screen','static'] if p['source']=='hue' else ['health','endurance','sound','combined','static']
        mode=tk.StringVar(value=MODE_LABELS[route['mode'] if route else modes[0]])
        brightness=tk.StringVar(value=str(round(route['brightness']*100)) if route else '35')
        player=tk.StringVar(value=str(route['player']+1) if route else '1');category=tk.StringVar(value=route['category'] if route else 'all')
        color=list(route['color']) if route else [0,80,255]
        for label,var,values in [('Zone',zone,labels),('Anzeige',mode,[MODE_LABELS[m] for m in modes])]:
            ttk.Label(b,text=label).pack(anchor='w');ttk.Combobox(b,textvariable=var,values=values,state='readonly').pack(fill='x',pady=(3,12))
        row=ttk.Frame(b);row.pack(fill='x',pady=8)
        ttk.Label(row,text='Helligkeit %').pack(side='left');ttk.Spinbox(row,from_=0,to=100,textvariable=brightness,width=6).pack(side='left',padx=10)
        ttk.Label(row,text='Spieler').pack(side='left');ttk.Combobox(row,textvariable=player,values=['1','2','3','4'],state='readonly',width=5).pack(side='left',padx=10)
        ttk.Label(b,text='Geraeuschfilter').pack(anchor='w');ttk.Combobox(b,textvariable=category,values=['all','world','zombie','vehicle','player','gunshot','alarm'],state='readonly').pack(fill='x',pady=8)
        def choose():
            result=colorchooser.askcolor(color='#%02x%02x%02x'%tuple(color),parent=win)
            if result[0]:color[:]=[round(v) for v in result[0]]
        ttk.Button(b,text='Feste Farbe waehlen',command=choose).pack(anchor='w',pady=10)
        ttk.Label(b,text='Geraeusche benoetigen Mod-Daten. Eine direkte Visual-Sounds-Anbindung ist noch nicht enthalten.',wraplength=450,style='Muted.TLabel').pack(anchor='w',pady=8)
        def apply():
            try:
                r={'zone':zones[labels.index(zone.get())]['id'],'mode':LABEL_MODES[mode.get()],'brightness':float(brightness.get())/100,'player':int(player.get())-1,'category':category.get(),'color':color}
                candidate=copy.deepcopy(self.cfg);cp=candidate['profiles'][self.profile_combo.current()]
                if index is None:cp['routes'].append(r)
                else:cp['routes'][index]=r
                validate(candidate);self.cfg=candidate;self.commit();self.refresh_routes();win.destroy()
            except Exception as exc:self.error(exc)
        ttk.Button(b,text='Anzeige speichern',command=apply).pack(anchor='e',pady=10)

    def remove_route(self):
        ids=self.route_tree.selection();p=self.profile()
        if ids and p:p['routes'].pop(int(ids[0]));self.commit();self.refresh_routes()

    def pick_cache(self):
        path=filedialog.askdirectory()
        if path:self.cache_var.set(path)

    def pick_openrgb(self):
        path=filedialog.askopenfilename(filetypes=[('OpenRGB','*.exe')])
        if path:self.openrgb_var.set(path)

    def openrgb_now(self):
        try:
            if self.demo:raise ValueError('Demo startet keine Programme.')
            launch_openrgb(self.openrgb_var.get());self.log('OpenRGB-Start angefordert. Danach neu verbinden.')
        except Exception as exc:self.error(exc)

    def save_settings(self):
        try:
            self.cfg['cache']=self.cache_var.get().strip();self.cfg['openrgb_exe']=self.openrgb_var.get().strip();self.cfg['start_openrgb']=self.start_rgb.get()
            self.commit();self.log('Einstellungen gespeichert.')
        except Exception as exc:self.error(exc)

    def change_autostart(self):
        try:
            if self.demo:raise ValueError('Autostart ist in der Demo deaktiviert.')
            set_autostart(self.autostart.get(),Path(__file__).resolve().parents[1]/'app.py',self.data_dir)
            self.log('Autostart eingeschaltet.' if self.autostart.get() else 'Autostart ausgeschaltet.')
        except Exception as exc:self.autostart.set(autostart_enabled());self.error(exc)

    def install_mod(self):
        try:
            target=Path(self.cache_var.get()).parent/'mods'/'ZomboidAura'
            from .runtime import resource_root
            source=resource_root()/'mods'/'ZomboidAura'
            shutil.copytree(source,target,dirs_exist_ok=True)
            self.log('Mod installiert. In Zomboid aktivieren: Zomboid Aura (Alpha).')
            messagebox.showinfo('Mod installiert','In Zomboid die Mod Zomboid Aura (Alpha) aktivieren. Nach Aenderung der Mod-Liste neu laden.')
        except Exception as exc:self.error(exc)

    def open_data(self):
        if sys.platform=='win32':os.startfile(str(self.data_dir))
        else:self.log(str(self.data_dir))

    def export_report(self):
        from .config import atomic_json
        path=self.data_dir/'reports'/(time.strftime('%Y%m%d-%H%M%S')+'.json')
        atomic_json(path,{'version':__version__,'devices':self.devices,'status':self.status.get(),'profile':self.game_status.get(),'messages':self.messages[-20:],'pending_restoration':(self.data_dir/'snapshots/pending.json').exists(),'demo':self.demo})
        self.log('Diagnosebericht gespeichert: '+path.name)

    def log(self,text):
        text=str(text).replace(str(Path.home()),'<USER_HOME>');self.messages.append(text)
        self.logbox.configure(state='normal');self.logbox.insert('end',time.strftime('%H:%M:%S')+'  '+text+'\n');self.logbox.see('end');self.logbox.configure(state='disabled')

    def error(self,exc):
        self.log(str(exc));messagebox.showerror('AllyLight',str(exc),parent=self.root)

    def setup_tray(self):
        if sys.platform!='win32' or self.demo:return
        try:
            import pystray
            from PIL import Image,ImageDraw
            image=Image.new('RGB',(64,64),'#111827');draw=ImageDraw.Draw(image);draw.ellipse((10,10,54,54),fill='#70e1ce');draw.ellipse((24,24,40,40),fill='#172033')
            menu=pystray.Menu(pystray.MenuItem('Oeffnen',lambda:self.tray_actions.put('show'),default=True),pystray.MenuItem('Automatik umschalten',lambda:self.tray_actions.put('toggle')),pystray.MenuItem('Beenden und wiederherstellen',lambda:self.tray_actions.put('quit')))
            self.tray=pystray.Icon('AllyLight',image,'AllyLight',menu);self.tray.run_detached()
        except Exception as exc:self.log('Infobereich nicht verfuegbar: '+str(exc));self.tray=None

    def hide(self):
        if self.tray:self.root.withdraw()
        else:self.root.iconify()

    def close_window(self):
        if self.tray:self.hide()
        else:self.quit()

    def quit(self):
        if self.closing:return
        self.closing=True;self.close_at=time.monotonic();self.status.set('Beleuchtung wird wiederhergestellt ...');self.send({'type':'stop'})
        if self.tray:self.tray.stop();self.tray=None

    def poll(self):
        now=time.monotonic()
        try:
            while True:
                command=self.tray_actions.get_nowait()
                if command=='show':self.root.deiconify();self.root.lift()
                elif command=='toggle':self.toggle_automation()
                elif command=='quit':self.quit()
        except queue.Empty:pass
        try:
            while True:
                event=self.events.get_nowait();self.last_seen=now;kind=event['type']
                if kind=='devices':
                    self.devices=event['devices'];self.device_tree.delete(*self.device_tree.get_children())
                    for d in self.devices:self.device_tree.insert('', 'end',iid=d['id'],values=(d['name'],d['led_count'],d['active_mode']))
                    self.refresh_zones();self.log(f"{len(self.devices)} OpenRGB-Geraet(e) erkannt.")
                elif kind=='status':
                    if not self.closing:self.status.set(event['message']);self.game_status.set(event['profile'] or 'Kein aktives Spielprofil')
                    color=event.get('color');self.swatch.configure(bg='#%02x%02x%02x'%tuple(color) if color else '#111827')
                elif kind=='error':self.status.set(event['message']);self.log(event['message'])
                elif kind=='recovery':
                    self.log(event['message']);self.status.set(event['message']);self.recovering=False
                    if not self.closing:self.log('Zum Fortsetzen Neu verbinden waehlen.')
                elif kind=='stopped':self.log('Engine beendet.')
        except queue.Empty:pass
        if now-self.last_heartbeat>1 and not self.closing:
            self.send({'type':'heartbeat'});self.last_heartbeat=now
        if self.process and self.process.is_alive():
            timeout=20 if not self.recovering else 25
            if (self.closing and now-self.close_at>timeout) or (not self.closing and now-self.last_seen>timeout):
                self.process.terminate();self.process.join(.5)
                if not self.recovering:
                    self.cfg['automation']=False;save(self.config_path,self.cfg);self.set_toggle()
                    self.recovering=True;self.close_at=now;self.last_seen=now
                    self.process=mp.Process(target=recover_process,args=(str(self.data_dir),self.events));self.process.start()
                    self.log('Engine reagiert nicht. Gesicherte Beleuchtung wird separat wiederhergestellt.')
                else:
                    self.log('Wiederherstellung konnte nicht abgeschlossen werden. OpenRGB manuell pruefen.');self.recovering=False
        if self.closing and (not self.process or not self.process.is_alive()):
            if (self.data_dir/'snapshots/pending.json').exists():
                messagebox.showwarning('Wiederherstellung offen','Die Sicherung bleibt im Datenordner erhalten. OpenRGB-Verbindung pruefen und AllyLight erneut starten.',parent=self.root)
            self.root.destroy();return
        self.root.after(150,self.poll)
