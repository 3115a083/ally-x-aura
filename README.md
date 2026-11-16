# AllyLight

Windows-Programm fuer Spielbeleuchtung auf dem ROG Xbox Ally X und weiteren
OpenRGB-Geraeten. Eigenstaendige Oberflaeche mit Spielprofilen, LED-Zonen und
Wiederherstellung der vorherigen statischen Beleuchtung.

**Version 0.2 ist eine testbare Programmversion mit Windows-EXE-Build.** Der zugrunde liegende
OpenRGB-Farbtest und die statische Wiederherstellung wurden auf einem Ally
bestaetigt. Die komplette neue Anwendung, Windows-Infobereich, Autostart und
Live-Spielanbindungen muessen auf dem Geraet noch abgenommen werden.

## Windows-EXE ohne Python

Der erfolgreiche GitHub-Actions-Lauf stellt das Artefakt
`AllyLight-0.2.0-windows-x64` bereit. Das ZIP vollstaendig entpacken und
`AllyLight.exe` starten. Python, Tkinter, pystray und die weiteren Python-Bibliotheken
sind in der EXE gebuendelt. OpenRGB bleibt separat erforderlich.

Im Paket liegen Quellcode, Lizenztexte, Bibliotheksquellen, Build-Metadaten und
SHA-256-Pruefsummen. Das Programm ist eine unsignierte Entwicklungsfassung.
Eine Code-Signatur oder SmartScreen-Reputation wird durch das Buendeln nicht erzeugt;
Windows- oder Unternehmensrichtlinien koennen den Start weiterhin blockieren.
Keine Schutzfunktionen pauschal deaktivieren.

Der Windows-Build startet die echte EXE mit bereinigtem Suchpfad und prueft Imports,
Tk-Oberflaeche, Infobereich-API, Mod-Ressourcen und den eingefrorenen Worker. Es gibt
keinen Hardwarezugriff im Build. Der Bericht liegt im Downloadpaket.

## Start aus Python-Quellcode auf Windows

Python 3.12 mit Tkinter und OpenRGB werden vorausgesetzt. OpenRGB ist eine eigene
Anwendung und wird nicht mitgeliefert.

1. Dieses Repository herunterladen oder klonen und vollstaendig entpacken.
2. `Installieren.cmd` ausfuehren. Es installiert die Python-Abhaengigkeiten und startet
   die automatisierten Tests. Es aktiviert keinen Autostart und keine Beleuchtung.
3. OpenRGB oeffnen, gewuenschte Ausgangsbeleuchtung als **Static** oder **Direct**
   einstellen und unter **SDK Server** den Server auf Port **6742** starten.
4. `Starten.cmd` ausfuehren. Die Automatik und beide Spielprofile sind anfangs aus.
5. Unter **Geraete & Zonen** ein Geraet waehlen und LED-Indizes einzeln testen.
   Jeder Test dauert etwa zwei Sekunden und stellt anschliessend den Ausgangszustand wieder her.
6. Zonen mit selbst beobachteten Indizes anlegen, beispielsweise linker und rechter
   Stick-Ring. Die App nimmt keine physische Zuordnung voraus.
7. Unter **Spielprofile** Anzeigen zuordnen, die Programmdatei pruefen, das Profil
   aktivieren und speichern. Dann oben **Automatik einschalten** waehlen.

OpenRGB meldet SDK-LEDs, keine garantierte physische Geometrie. Eine Zone mit zwei
steuerbaren LEDs erlaubt entsprechend nur eine sehr grobe Richtungsanzeige.

## Enthaltene Funktionen

- Mehrere OpenRGB-Geraete und frei benannte, nicht ueberlappende LED-Zonen.
- Test einzelner LEDs, Winkelkorrektur und umgekehrte Reihenfolge fuer Richtungsanzeigen.
- Profile anhand des Vordergrundprozesses, wahlweise exakter Programmdateiname oder voller Pfad.
- Zomboid: Gesundheit, Ausdauer, Geraeuschrichtung oder Kombination, pro lokalem Spieler.
- Hue: dominante gesaettigte Hintergrundfarbe aus dem Spielfenster mit geglaetteten Uebergaengen.
- Feste Profilfarben, Helligkeit und Geraeuschfilter.
- Minimieren in den Windows-Infobereich; ausdrueckliches Beenden mit Wiederherstellung.
- Optionaler Benutzer-Autostart und optionaler Start der gewaehlten OpenRGB.exe.
- Gespeicherter Ausgangszustand, separater Engine-Prozess, Heartbeat und Wiederherstellungsversuch
  nach ausbleibender Antwort. Offene Sicherungen bleiben fuer den naechsten Start erhalten.
- Diagnoseberichte und begrenzte lokale Logs. Keine Bildschirmbilder werden gespeichert.

## Zomboid einrichten

Unter **Einstellungen** den Lua-Cache pruefen, standardmaessig
`%USERPROFILE%\Zomboid\Lua`. **Zomboid-Mod installieren** kopiert ausschliesslich
den mitgelieferten Ordner `mods/ZomboidAura` in den passenden `Zomboid/mods`-Ordner.
Eine bestehende Fassung dieser Mod wird aktualisiert. In Zomboid danach
**Zomboid Aura (Alpha)** aktivieren und die Partie neu laden.

Die Windows-App verwendet die Telemetrie der Mod; LED-Zuordnungen aus einem alten
Mod-Menue werden nicht als Windows-Profile uebernommen. Gesundheit und Ausdauer
benoetigen keine weiteren Mods. Beim Ausbleiben frischer Frames fuer drei Sekunden
endet die Ausgabe der davon abhaengigen Anzeigen.

Die mitgelieferte Mod hat einen optionalen Weltgeraeusch-Fallback und die API
`ZomboidAura.pushSound(x,y,z,strength,category,playerIndex)`. Der Fallback basiert auf
KI-Weltgeraeuschen und ist kein exakter Hoertest. Er ist anfangs aus und laesst sich
im bisherigen F10-/Welt-Kontextmenue der Mod einschalten. Die direkte Anbindung an
Visual Sounds ist noch nicht implementiert; dafuer muss die konkrete Mod-Version
geprueft werden. Kategorien Schuss/Alarm setzen einen passenden Adapter voraus.

Die B41-/B42-Modlayouts liegen bei, Live-Kompatibilitaet ist je Build zu pruefen.
Mehrspieler-Telemetrie ist nur lokal und nicht gesondert validiert.

## Hue einrichten

Das vorgegebene Profil sucht nach `Hue.exe`. Weicht die Programmdatei ab, laesst sie
sich auswaehlen oder ueber **Vordergrundspiel in 5 Sekunden uebernehmen** ermitteln.
Danach das Profil speichern. Den Ringen die Anzeige **Bildschirmfarbe** zuweisen.

Die Erfassung liest nur bei aktivem Hue-Profil das Client-Rechteck des Vordergrundfensters.
Der Vordergrund wird vor und nach der Erfassung verglichen; bei einem Wechsel wird die
Probe verworfen. Bildschirmdaten bleiben im Arbeitsspeicher. Schwarze Geometrie und
weisse UI-Flaechen werden aus der Farbsuche ausgeschlossen. Bei unklarer Farbe wird nach
kurzer Uebergangszeit zur Ausgangsbeleuchtung gewechselt. HDR, exklusives Vollbild und
Overlays koennen die Erfassung beeinflussen; zuerst im Fenstermodus testen.

## Autostart und OpenRGB

Autostart ist standardmaessig aus. In **Einstellungen** laesst sich die Verknuepfung
`AllyLight.lnk` im Autostartordner des aktuellen Windows-Nutzers anlegen oder entfernen.
Dafuer werden normalerweise keine Administratorrechte benoetigt. Der Programmordner
muss danach an seinem Platz bleiben. Beim Umzug den Autostart aus- und erneut einschalten.

Die optionale OpenRGB-Startfunktion verwendet die selbst ausgewaehlte EXE mit
`--server --startminimized`. Ist der lokale SDK-Port bereits erreichbar, wird keine
zweite Instanz angefordert. Fuer den Test keine konkurrierenden RGB-Effektprogramme laufen lassen.
Die App richtet weder Dienste noch eine Firewall-Freigabe ein und verbindet nur zu 127.0.0.1.

## Wiederherstellung und Fehler

Vor dem ersten Farbzugriff wird der Modus mit seinen Parametern und LED-Farben in
`%LOCALAPPDATA%\AllyLight\snapshots\pending.json` gesichert. Andere LED-Bereiche des
Geraetes bleiben im gespeicherten Ausgangszustand. Bei Profilwechsel, Pause oder Beenden
schreibt die App den statischen Zustand ausdruecklich ueber OpenRGB zurueck.

Eine bestaetigte Server-Rueckmeldung ist keine physische Messung. Ein schwarzer
Ausgangszustand und dynamische Ausgangseffekte werden in dieser Version abgelehnt.
OpenRGB bleibt die aktive Hardwareanbindung; eine Rueckgabe an Armoury Crate ist
hiermit nicht zugesichert.

Bei verlorenem SDK-Zugriff bleibt die offene Sicherung erhalten. Beim naechsten Verbinden
wird sie zuerst wiederhergestellt. Nach laengerem Haengen der Engine versucht die UI
in einem neuen Prozess die Wiederherstellung. Bei Stromverlust, ausgefallener Hardware,
beendeter OpenRGB-Anwendung oder einem gleichzeitig beendeten gesamten Programm ist
keine sofortige Ruecksetzung garantiert. OpenRGB dann manuell pruefen.

## Dateien und Entwicklung

- `allylight/`: GUI, Profil-/Datenlogik, Windows-Funktionen und OpenRGB-Anbindung.
- `mods/`: mitgelieferte Zomboid-Mod.
- `tests/`: Funktionstests mit simulierten Geraeten, keine automatischen Hardware-Schreibtests.
- `docs/VALIDATION.md`: Nachweise und offene Abnahme.
- `docs/SECURITY.md`: Sicherheitsgrenzen und Datenhaltung.

```powershell
py -3 app.py
py -3 app.py --demo --data-dir .\demo-data
py -3 -m unittest discover -s tests -v
```

Der Demo-Modus greift nicht auf RGB-Hardware zu. Auf Hosts ohne Display werden die
nativen Formulartests uebersprungen und gesondert ausgewiesen. Windows-CI fuehrt diese
Tests mit einer verfuegbaren Desktop-Sitzung aus. Linux ist eine Entwicklungsumgebung,
kein unterstuetztes Ziel fuer Vordergrunderkennung oder Autostart.

Unter `%LOCALAPPDATA%\AllyLight` liegen Konfiguration, offene Sicherungen, begrenzte
Logs und selbst exportierte Berichte. Kein Upload oder Cloudkonto ist erforderlich.
Persoenliche Profile und Testdaten gehoeren nicht ins Repository.

## Lizenz und Abhaengigkeiten

Eigener Code: MIT. OpenRGB, Project Zomboid und deren Assets werden nicht mitgeliefert.
`openrgb-python` ist eine externe GPL-3.0-lizenzierte Abhaengigkeit; weitere Hinweise
stehen in `THIRD_PARTY_NOTICES.md`. Fuer eine spaetere gebuendelte EXE ist die Lizenzlage
des gesamten Pakets vor Auslieferung zu pruefen. Der Quellcode bleibt MIT. Das kombinierte EXE-Paket wird unter GPL-3.0 mit den
benoetigten Lizenztexten und Quellen bereitgestellt; pystray behaelt seine LGPL-Lizenz.
