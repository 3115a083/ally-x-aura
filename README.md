# AllyLight

**Spielbeleuchtung für den ROG Xbox Ally X und weitere OpenRGB-Geräte.**

AllyLight läuft als eigenes Windows-Programm neben OpenRGB. Es erkennt das aktive
Spiel, lädt das passende Profil und überträgt Spielinformationen auf ausgewählte
LEDs. Nach dem Spiel stellt es die vorherige statische Beleuchtung wieder her.

> **Entwicklungsversion 0.2.0:** Die Windows-EXE enthält Python und die benötigten
> Bibliotheken. OpenRGB bleibt separat erforderlich. Die vollständige Abnahme der
> neuen Anwendung auf dem Ally ist noch offen.

## Download und Start

1. Unter [Actions → tests](https://github.com/3115a083/ally-x-aura/actions/workflows/tests.yml)
   einen erfolgreichen Build des Branches `feat/allylight-desktop` öffnen.
2. Das Artefakt **AllyLight-0.2.0-windows-x64** herunterladen und das ZIP vollständig entpacken.
   Für GitHub-Artefakte ist gegebenenfalls eine Anmeldung nötig. Sie bleiben 30 Tage verfügbar.
3. In OpenRGB die gewünschte Ausgangsbeleuchtung als **Static** oder **Direct** einstellen.
   Unter **SDK Server** den Server auf Port **6742** starten und OpenRGB geöffnet lassen.
4. **AllyLight.exe** starten. Eine separate Python-Installation oder ein `pip`-Befehl ist nicht nötig.

Die EXE ist noch **nicht mit einem Herausgeberzertifikat signiert**. Windows SmartScreen
oder eine Unternehmensrichtlinie kann deshalb weiterhin nachfragen oder den Start
blockieren. Keine Schutzfunktionen pauschal deaktivieren. Zur Integritätsprüfung liegt
`SHA256SUMS.txt` bei.

## Erste Einrichtung

1. Unter **Geraete & Zonen** das erkannte OpenRGB-Gerät auswählen.
2. LED-Indizes einzeln testen. Jede Testanzeige endet nach etwa zwei Sekunden mit einer Wiederherstellung.
3. Selbst beobachtete Bereiche als Zonen anlegen, zum Beispiel einen linken und einen rechten Ring.
4. Unter **Spielprofile** eine Anzeige zuordnen, die Programmdatei prüfen und das Profil speichern und aktivieren.
5. **Automatik einschalten** wählen. Die App reagiert nur auf das passende Vordergrundspiel.

Automatik, Spielprofile und Windows-Autostart sind beim ersten Start ausgeschaltet.
Die Anzahl der SDK-LEDs sagt nichts Verlässliches über ihre physische Position aus.
Zonen mit wenigen LEDs erlauben entsprechend nur eine grobe Richtungsanzeige.

## Funktionen

| Bereich | Enthalten |
| --- | --- |
| Geräte | Mehrere OpenRGB-Geräte, einzelne LED-Tests, frei benannte LED-Zonen |
| Profile | Vordergrundspiel erkennen, Helligkeit und Anzeige je Zone festlegen |
| Project Zomboid | Gesundheit, Ausdauer und vorbereitete Geräuschdaten-Schnittstelle |
| Hue | Hintergrundfarbe des Spielfensters erkennen und Farbwechsel glätten |
| Windows | Infobereich, optionaler Benutzer-Autostart, optionaler OpenRGB-Mitstart |
| Wiederherstellung | Ausgangszustand sichern, bei Pause/Profilwechsel/Ende zurückschreiben |

### Project Zomboid

Unter **Einstellungen** den Lua-Ordner prüfen, normalerweise `%USERPROFILE%\Zomboid\Lua`.
Mit **Zomboid-Mod installieren** wird die mitgelieferte Mod in den zugehörigen
`Zomboid\mods`-Ordner kopiert. Eine vorhandene Version derselben Mod wird aktualisiert.
In Zomboid anschließend **Zomboid Aura (Alpha)** aktivieren und die Partie neu laden.

Gesundheit und Ausdauer stammen aus der lokalen Spieltelemetrie. LED-Zuordnungen
werden in AllyLight eingerichtet. Fehlen länger als drei Sekunden frische Daten,
endet die Ausgabe der betroffenen Anzeigen.

Die direkte Anbindung an **Visual Sounds ist noch nicht enthalten**. Die konkrete
Mod-Version muss dafür geprüft werden. Die vorhandene API heißt
`ZomboidAura.pushSound(x, y, z, strength, category, playerIndex)`.

Ein optionaler Weltgeräusch-Fallback lässt sich im bisherigen F10-/Kontextmenü der Mod
aktivieren. Er basiert auf KI-Geräuschereignissen und bildet das tatsächliche Hören
nur ungefähr ab. B41-/B42-Verzeichnislayouts liegen bei; Live-Kompatibilität und
Mehrspielerbetrieb müssen im konkreten Build geprüft werden.

### Hue

Das mitgelieferte Profil sucht nach `Hue.exe`. Eine abweichende Programmdatei lässt
sich auswählen oder mit **Vordergrundspiel in 5 Sekunden uebernehmen** erfassen.
Danach das Profil speichern und einer Zone **Bildschirmfarbe** zuordnen.

AllyLight wertet die dominante gesättigte Farbe im Spielfenster aus. Schwarze Geometrie
und weiße UI-Flächen werden ausgefiltert. Bei einem Fokuswechsel wird die Probe
verworfen. HDR, Overlays und exklusives Vollbild können das Ergebnis beeinflussen;
zuerst im Fenstermodus testen.

## Wiederherstellung und Daten

Vor dem ersten Zugriff speichert die App Modus, Parameter und Farben unter
`%LOCALAPPDATA%\AllyLight\snapshots\pending.json`. Sie schreibt diesen Zustand bei
Pause, Profilwechsel oder Beenden ausdrücklich über OpenRGB zurück.

- Unterstützte Ausgangsmodi: **Static** und **Direct**. Dynamische Effekte und ein vollständig schwarzer Ausgangszustand werden vorerst abgelehnt.
- OpenRGB bleibt die Hardwareanbindung. Eine Rückgabe an Armoury Crate wird damit nicht zugesichert.
- Schlägt die Wiederherstellung fehl, bleibt die Sicherung erhalten. Beim nächsten Verbinden wird sie zuerst erneut versucht.
- Nach ausbleibender Antwort der Engine versucht ein separater Prozess die Wiederherstellung.
- Bei Stromverlust, nicht erreichbarer Hardware oder beendetem OpenRGB ist keine sofortige Rücksetzung garantiert.

Konfiguration, Sicherungen und begrenzte Logs bleiben im lokalen Datenordner.
Die App benötigt kein Cloudkonto und lädt keine Telemetrie hoch. Bildschirmproben
bleiben im normalen Betrieb im Arbeitsspeicher. Der Build-Selbsttest erzeugt ein
Bild seines eigenen Demo-Fensters zur Prüfung des Programmpakets.

## Autostart

Unter **Einstellungen** kann AllyLight eine Verknüpfung im Autostartordner des aktuellen
Windows-Nutzers anlegen oder entfernen. Administratorrechte sind normalerweise nicht nötig.
Den Programmordner danach nicht verschieben; nach einem Umzug den Autostart neu einrichten.

Optional lässt sich eine selbst ausgewählte `OpenRGB.exe` mitstarten. Die App nutzt
`--server --startminimized` und startet keine zweite Instanz, wenn der lokale SDK-Port
bereits erreichbar ist. Für den Test keine konkurrierenden RGB-Effektprogramme betreiben.

## Aus Quellcode starten

Voraussetzungen: Windows x64, Python 3.12 mit Tkinter und OpenRGB.

```powershell
py -3 -m pip install -r requirements.txt
py -3 app.py
```

Alternativ `Installieren.cmd` und danach `Starten.cmd` verwenden. Bei
`No module named 'pystray'` wurden die Abhängigkeiten nicht vollständig in derselben
Python-Umgebung installiert; der obige Installationsbefehl installiert sie gemeinsam.

```powershell
# Funktionstests
py -3 -m unittest discover -s tests -v

# Oberfläche ohne RGB-Hardware ausprobieren
py -3 app.py --demo --data-dir .\demo-data

# Windows-EXE auf Windows bauen
py -3 -m pip install -r requirements.txt -r requirements-build.txt
py -3 tools\build_windows.py
```

Der EXE-Build prüft die tatsächliche Anwendung mit bereinigtem Suchpfad: Imports,
Mod-Dateien, GUI, native Infobereich-API und den gebündelten Hintergrundprozess.
Der Selbsttest greift nicht auf RGB-Hardware zu. Das fertige Paket liegt unter `dist\package`.

## Projektstruktur und Status

- `allylight/`: Oberfläche, Profile, Datenquellen, OpenRGB und Windows-Funktionen.
- `mods/`: mitgelieferte Zomboid-Mod.
- `tests/`: automatisierte Funktionstests mit simulierten Geräten.
- `tools/build_windows.py`: Windows-Build und Paketprüfung.
- [Testnachweise und offene Abnahme](docs/VALIDATION.md)
- [Sicherheitsgrenzen](docs/SECURITY.md)
- [Abhängigkeiten und Lizenzhinweise](THIRD_PARTY_NOTICES.md)

Der zugrunde liegende OpenRGB-Farbtest und die statische Wiederherstellung wurden
auf einem Ally bestätigt. Das ersetzt keine vollständige Prüfung der neuen Anwendung.
Offen sind insbesondere die Live-Spieltests, die Geräuschintegration und die praktische
Tray-/Autostartabnahme. Linux dient nur als Entwicklungs- und Testumgebung.

## Lizenz

Eigener Quellcode: **MIT**. Das kombinierte EXE-Paket wird unter **GPL-3.0** bereitgestellt;
pystray behält seine **LGPL-3.0**-Lizenz. Das Paket enthält Anwendungscode, die tatsächlich
verwendeten Python-Quellen der GPL-/LGPL-Abhängigkeiten, Lizenztexte, Build-Informationen
und Prüfsummen. OpenRGB und Project Zomboid werden nicht mitgeliefert.
