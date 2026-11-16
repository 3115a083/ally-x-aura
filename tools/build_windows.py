"""Reproducible Windows one-file build and portable source-complete package."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    if sys.platform!='win32':raise SystemExit('Build on Windows x64; cross compilation is not supported.')
    os.chdir(ROOT)
    from PIL import Image,ImageDraw
    import PyInstaller.__main__
    build=ROOT/'build';build.mkdir(exist_ok=True)
    icon=Image.new('RGBA',(256,256),'#111827');draw=ImageDraw.Draw(icon)
    draw.ellipse((35,35,221,221),fill='#70e1ce');draw.ellipse((90,90,166,166),fill='#172033')
    icon_path=build/'allylight.ico';icon.save(icon_path,sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    PyInstaller.__main__.run([
        'app.py','--name=AllyLight','--onefile','--windowed','--noupx','--clean','--noconfirm',
        '--distpath=dist','--workpath=build/pyinstaller','--specpath=build',
        '--icon='+str(icon_path),'--version-file=packaging/windows-version.txt',
        '--collect-submodules=openrgb','--hidden-import=pystray._win32',
        '--hidden-import=mss.windows','--hidden-import=win32timezone',
        '--copy-metadata=openrgb-python','--copy-metadata=pystray',
        '--add-data=mods;mods','--add-data=LICENSE;licenses',
        '--add-data=THIRD_PARTY_NOTICES.md;licenses'])
    # Run the actual EXE with no Python installation on PATH and no Python env hooks.
    env={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','VIRTUAL_ENV'))}
    env['PATH']=os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),os.environ['SystemRoot']])
    smoke=build/'smoke'/'result.json'
    subprocess.run([str(ROOT/'dist/AllyLight.exe'),'--smoke-test',str(smoke),'--data-dir',str(build/'smoke/user')],env=env,timeout=90,check=True)
    result=json.loads(smoke.read_text(encoding='utf-8'))
    if not result['frozen'] or result['status']!='pass':raise RuntimeError('Frozen executable verification failed')
    package=ROOT/'dist'/'package';package.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'dist/AllyLight.exe',package/'AllyLight.exe')
    shutil.copy2(smoke,package/'build-smoke-result.json')
    shutil.copy2(smoke.with_suffix('.png'),package/'build-smoke-window.png')
    for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):
        shutil.copy2(ROOT/name,package/name)
    shutil.copytree(ROOT/'packaging/notices',package/'LICENSES',dirs_exist_ok=True)
    # Complete application source and build recipe at exactly the built commit.
    tracked=subprocess.check_output(['git','ls-files','-z']).decode().split('\0')
    with zipfile.ZipFile(package/'application-source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in tracked:
            if name and (ROOT/name).is_file():z.write(ROOT/name,'ally-x-aura/'+name)
    sources=package/'dependency-sources';sources.mkdir(exist_ok=True)
    subprocess.run([sys.executable,'-m','pip','download','--no-deps','--no-binary=:all:',
                    '--dest',str(sources),'openrgb-python==0.3.8','pystray==0.19.5'],check=True)
    # Retain installed license files for all bundled runtime distributions.
    licenses=package/'LICENSES'/'installed';licenses.mkdir(parents=True,exist_ok=True)
    for distribution in importlib.metadata.distributions():
        name=distribution.metadata.get('Name','unknown')
        if name.lower() not in {'openrgb-python','pillow','mss','pystray','pywin32','six','pyinstaller'}:continue
        for file in distribution.files or []:
            if any(token in str(file).lower() for token in ('license','copying','notice')):
                source=Path(distribution.locate_file(file))
                if source.is_file():
                    target=licenses/name/str(file).replace('..','_');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    (package/'LIESMICH.txt').write_text(
        'AllyLight 0.2.0 fuer Windows x64\n\nZIP vollstaendig entpacken und AllyLight.exe starten.\n'
        'Python ist enthalten. OpenRGB bleibt separat erforderlich: SDK Server auf Port 6742 starten.\n'
        'Programmeinstellungen bleiben unter %LOCALAPPDATA%\\AllyLight erhalten.\n'
        'Diese Entwicklungsfassung ist nicht mit einem Herausgeberzertifikat codesigniert.\n'
        'Windows SmartScreen oder Richtlinien koennen den Start weiterhin pruefen/blockieren.\n'
        'Keine Schutzfunktionen deaktivieren. Die SHA256SUMS.txt dient zur Integritaetspruefung.\n\n'
        'Quellcode: application-source.zip; GPL-/LGPL-Abhaengigkeitsquellen: dependency-sources.\n'
        'Lizenz des kombinierten Bundles: GPL-3.0; eigener Quellcode zusaetzlich MIT.\n'
        'Die eingebundene pystray-Bibliothek steht unter LGPL-3.0; Hinweise unter LICENSES.\n'
        'Der hardwarefreie Build-Selbsttest ersetzt keinen Spiel-/Geraetetest.\n',encoding='utf-8')
    manifest={'application':'AllyLight','version':'0.2.0','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'python':sys.version.split()[0],'pyinstaller':importlib.metadata.version('pyinstaller'),'codesigned':False,
              'runtime_dependencies':{name:importlib.metadata.version(name) for name in ['openrgb-python','Pillow','mss','pystray','pywin32']}}
    (package/'BUILD-INFO.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    entries=[]
    for file in sorted(package.rglob('*')):
        if file.is_file():entries.append(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+file.relative_to(package).as_posix())
    (package/'SHA256SUMS.txt').write_text('\n'.join(entries)+'\n',encoding='utf-8')
    print('Package:',package)


if __name__=='__main__':main()
