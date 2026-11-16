# Verifikation

## 2026-11-16, Entwicklungsstand

25 automatisierte Funktionstests bestehen auf Python 3.12/Linux mit installiertem
OpenRGB-Python. Zusaetzliche native Formulartests sind ohne Display nicht ausfuehrbar
und werden als uebersprungen gemeldet. Python-Quellen kompilieren.

Geprueft: Profilmatching, Konfigurationsvalidierung, LED-Zonen, Speichern vor Zugriff,
Wiederherstellung und deren Fehlerspeicherung, Recovery beim naechsten Verbinden,
Teilzonen ohne Aenderung anderer LEDs, keine doppelten Farb-Schreibbefehle,
Einzelinstanzsperre, isolierte Engine im hardwarefreien Demo-Modus,
Hue-Farbauswahl ohne Verdunklung durch schwarze Geometrie, Fokuswechsel-Verwerfen,
geglaettete Farben und frische/veraltete/defekte Zomboid-Frames.

Der vorangegangene manuelle OpenRGB-Test bestaetigte Farbfolge und Wiederherstellung
am Ally. Das ist ein Nachweis fuer den zugrunde liegenden Restore-Pfad, kein Nachweis
fuer die komplette neue Anwendung. Reale Geraeteberichte werden nicht veroeffentlicht.

## Abnahme auf dem Ally

1. Installation und automatisierte Windows-Tests, einschliesslich Formular-Draft-Regressionschecks.
2. Alle vier Seiten, Dialoge, Touch-/Tastaturbedienung und Infobereich pruefen.
3. Einzelne LED-Indizes testen und Zonen tatsaechlich zuordnen.
4. Statische Ausgangsfarbe nach LED-Test, Pause und Programmende pruefen.
5. Gesundheit/Ausdauer im konkreten Zomboid-Build pruefen; Frames werden nicht automatisch archiviert.
6. Hue im Fenstermodus testen; Farbwechsel und Alt-Tab pruefen.
7. OpenRGB-Verbindungsverlust, Wiederverbinden und offene Sicherung pruefen.
8. Erst anschliessend freiwilligen Autostart, OpenRGB-Mitstart und Deaktivierung pruefen.
9. Visual-Sounds-Version ermitteln und Adapter separat entwickeln/abnehmen.

Die GUI konnte im Entwicklungscontainer mangels erreichbarem X-/Windows-Display
noch nicht visuell geprueft werden. Kein Screenshot- oder Hardware-Erfolg wird daraus abgeleitet.
