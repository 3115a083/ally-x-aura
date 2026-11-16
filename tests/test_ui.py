"""Native form checks run only where a display is available; no RGB hardware."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

@unittest.skipUnless(sys.platform=='win32' or os.environ.get('DISPLAY'),'Native display required')
class FormTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from allylight.ui import App
        self.temp=tempfile.TemporaryDirectory();self.root=tk.Tk();self.root.withdraw()
        with patch.object(App,'start_engine'),patch.object(App,'setup_tray'):
            self.app=App(self.root,self.temp.name,demo=True)
        self.root.update_idletasks()
    def tearDown(self):
        self.root.destroy();self.temp.cleanup()
    def test_all_four_pages_exist(self):
        self.assertEqual(len(self.app.notebook.tabs()),4)
        self.assertGreater(self.app.root.winfo_reqwidth(),500)
    def test_unsaved_executable_text_survives_profile_switch(self):
        draft='C:\\Games\\unfinished path; '
        self.app.exe_var.set(draft)
        self.app.profile_combo.current(1);self.app.load_profile_form()
        self.app.profile_combo.current(0);self.app.load_profile_form()
        self.assertEqual(self.app.exe_var.get(),draft)
    def test_background_zone_refresh_does_not_replace_text(self):
        self.app.exe_var.set('')
        self.app.refresh_zones()
        self.assertEqual(self.app.exe_var.get(),'')

    def test_fields_keep_contrast_in_all_states(self):
        from tkinter import ttk
        style=ttk.Style(self.root)
        for kind in ('TEntry','TCombobox','TSpinbox'):
            for state in ((),('readonly',),('disabled',),('focus',)):
                fg=style.lookup(kind,'foreground',state);bg=style.lookup(kind,'fieldbackground',state)
                self.assertNotEqual(fg,bg)
                self.assertIn(fg,('#111827','#475569'))
                self.assertIn(bg,('#f1f5f9','#cbd5e1'))

    def test_touch_targets_and_scrollable_settings(self):
        from tkinter import ttk
        self.assertGreaterEqual(self.app.profile_combo.winfo_reqheight(),44)
        self.assertGreaterEqual(self.app.toggle.winfo_reqheight(),44)
        self.assertGreaterEqual(int(ttk.Style(self.root).lookup('Treeview','rowheight')),44)
        page=self.app.pages['Einstellungen']
        self.assertEqual(page.master.winfo_class(),'Canvas')
        self.assertTrue(any(w.winfo_class()=='TScrollbar' for w in page.master.master.winfo_children()))

if __name__=='__main__':unittest.main()
