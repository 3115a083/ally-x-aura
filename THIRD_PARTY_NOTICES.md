# Abhaengigkeiten

Dieses Repository enthaelt eigenen Python- und Lua-Code. Bibliotheken werden fuer Quellstarts ueber requirements.txt installiert. Der Windows-
Build buendelt sie in der EXE und legt Lizenztexte sowie Quellen der GPL-/LGPL-
Bibliotheken dem Download bei.

- openrgb-python 0.3.8: GPL-3.0, https://github.com/jath03/openrgb-python
- Pillow: HPND, https://github.com/python-pillow/Pillow
- MSS: MIT, https://github.com/BoboTiG/python-mss
- pystray: LGPL-3.0, https://github.com/moses-palmer/pystray
- pywin32: PSF-orientierte Projektlizenz; die jeweilige Lizenzdatei der installierten
  Distribution beachten, https://github.com/mhammond/pywin32
- Python/Tk und OpenRGB bleiben eigenstaendige Voraussetzungen mit eigenen Lizenzen.

Die MIT-Lizenz dieses Repositories aendert keine Drittanbieter-Lizenz. Eine spaetere
Binaerdistribution muss insbesondere GPL-/LGPL-Pflichten beruecksichtigen.

Buildwerkzeug: PyInstaller 6.22.3, GPL mit Bootloader-Ausnahme, https://pyinstaller.org/
Die kombinierte Binaerfassung wird unter GPL-3.0 verteilt; eigener Quellcode bleibt MIT.

Hue-Farberkennung: Algorithmusreferenz und HSV-Palettengrenzen nach jath03,
https://gist.github.com/jath03/a775de26d03812ee58faa94593955f1b .
Das Gist nennt keine ausdrueckliche Lizenz. Es wird kein Skript daraus gebuendelt;
das Verfahren ist eigenstaendig mit Pillow/colorsys implementiert.
Xlib, NumPy und OpenCV werden dafuer nicht eingebunden.
