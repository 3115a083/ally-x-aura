import os
from pathlib import Path
import sys
import tempfile
import zipfile
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
    def test_data_sources_are_absolute_independent_of_generated_spec_directory(self):
        from tools.build_windows import bundle_data_args
        root=Path(__file__).resolve().parents[1]
        for argument in bundle_data_args(root):
            source=Path(argument.removeprefix('--add-data=').split(';')[0])
            self.assertTrue(source.is_absolute());self.assertTrue(source.exists())
            self.assertEqual((root/'build'/source).resolve(),source)

    def test_external_program_does_not_inherit_temporary_bundle_path(self):
        from allylight.runtime import external_environment
        root=str(Path('bundle').resolve())
        env={'PATH':os.pathsep.join([str(Path('system').resolve()),root,str(Path(root)/'win32')]),'KEEP':'yes'}
        clean=external_environment(env,root)
        self.assertEqual(clean['PATH'],str(Path('system').resolve()))
        self.assertEqual(clean['KEEP'],'yes')
        self.assertEqual(env['PATH'].count(root),2)

    def test_dependency_source_export_uses_actual_python_wheels(self):
        from tools.build_windows import collect_dependency_sources
        with tempfile.TemporaryDirectory() as tmp:
            def download(command,check):
                self.assertIn('--only-binary=:all:',command)
                self.assertNotIn('--no-binary=:all:',command)
                for name in ['openrgb_python-0.3.8-py3-none-any.whl','pystray-0.19.5-py2.py3-none-any.whl']:
                    with zipfile.ZipFile(Path(tmp)/name,'w') as z:z.writestr('package/__init__.py','# exact Python source')
            with patch('tools.build_windows.subprocess.run',side_effect=download):collect_dependency_sources(tmp)
            self.assertTrue((Path(tmp)/'README.txt').is_file())

    def test_binary_dependency_cannot_be_mislabelled_source(self):
        from tools.build_windows import collect_dependency_sources
        with tempfile.TemporaryDirectory() as tmp:
            for name in ['a.whl','b.whl']:
                with zipfile.ZipFile(Path(tmp)/name,'w') as z:
                    z.writestr('package/__init__.py','# source');z.writestr('package/native.pyd','binary')
            with patch('tools.build_windows.subprocess.run'):
                with self.assertRaises(RuntimeError):collect_dependency_sources(tmp)

    def test_source_mod_resources_exist(self):
        self.assertTrue((resource_root()/'mods/ZomboidAura/mod.info').exists())

if __name__=='__main__':unittest.main()
