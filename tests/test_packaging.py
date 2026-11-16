import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from allylight.runtime import launch_command,resource_root

class BundleTests(unittest.TestCase):
    def test_frozen_autostart_uses_real_exe_not_extracted_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable=str(Path(tmp)/'AllyLight.exe')
            target,args,cwd=launch_command(Path(tmp)/'_MEI'/ 'app.py',Path(tmp)/'settings',True,executable)
            self.assertEqual(target,Path(executable));self.assertEqual(cwd,Path(tmp))
            self.assertIn('--tray',args);self.assertNotIn('app.py',args);self.assertNotIn('_MEI',args)
    def test_python_source_still_uses_pythonw(self):
        with tempfile.TemporaryDirectory() as tmp:
            target,args,cwd=launch_command(Path(tmp)/'app.py',Path(tmp)/'settings',False,str(Path(tmp)/'python.exe'))
            self.assertEqual(target.name,'pythonw.exe');self.assertIn('app.py',args)
    def test_frozen_mod_root_is_bundle_data_root(self):
        with patch.object(sys,'_MEIPASS','bundle-resources',create=True):
            self.assertEqual(resource_root(),Path('bundle-resources'))
    def test_source_mod_resources_exist(self):
        self.assertTrue((resource_root()/'mods/ZomboidAura/mod.info').exists())

if __name__=='__main__':unittest.main()
