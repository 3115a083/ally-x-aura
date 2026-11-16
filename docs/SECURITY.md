# Sicherheitsgrenzen

Stand: 2026-11-16. Die Anwendung ist eine lokale, noch nicht umfassend auf Windows
abgenommene Quellcodeversion. Sie steuert nur vom Nutzer zugeordnete OpenRGB-Geraete.

- SDK nur 127.0.0.1:6742; kein eigener Netzwerkserver und kein Telemetrie-Upload.
- Der lokale OpenRGB-Server ist eine Vertrauensgrenze. Andere lokale Programme mit
  Zugriff koennen denselben Zustand beeinflussen. Keine Authentisierung des SDKs angenommen.
- Spielprofile sind lokale JSON-Daten. Werte werden validiert, nicht als Code ausgefuehrt.
- Prozessstarts verwenden Argumentlisten. Kein shell=True, kein Download fremder Treiber.
- Bildschirmproben nur fuer ein passendes Vordergrundprofil; Ergebnisse bei Fokuswechsel verwerfen.
  Es werden keine Bildschirmbilder geschrieben. Ein Fokuswechsel waehrend der Erfassung kann
  kurzzeitig andere Bildinhalte im Arbeitsspeicher sichtbar machen; diese werden verworfen.
- Autostart ausschliesslich ueber ausdrueckliche GUI-Auswahl des Nutzers und dessen Startup-Ordner.
- Offene Wiederherstellungsdatei vor dem ersten Hardwarezugriff atomar schreiben.
- Worker-Prozess trennt langsame SDK-Aufrufe von der UI. Heartbeat/Timeout und neuer Recovery-Prozess
  sind Wiederherstellungsversuche, keine Garantie bei Hardware-/Stromausfall.
- Geraetepfade/Seriennummern werden nur fuer eine gehashte Identitaet verwendet, nicht in Inventaren ausgegeben.
- Keine Hardware-Testberichte, persoenlichen Konfigurationen oder privaten Projektakten im Repository.
- Arbeitsbranch und PR verwenden; keine Schutzregeln abschwaechen und keine Selbstfreigabe.

Noch offen: native GUI-/Tray-/Autostartabnahme auf Windows, Live-Spieltests,
Abhaengigkeits-/Binaerrelease-Review und vollstaendige Tastatur-/Screenreader-Abnahme.
