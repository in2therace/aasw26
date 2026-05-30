# Slider-Bilder

Lege deine Slider-Bilder einfach **in diesen Ordner** (per Drag & Drop hochladen
über die GitHub-Weboberfläche oder lokal hinzufügen und pushen).

- Unterstützte Formate: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`
- Die Website erkennt neue Bilder **automatisch** über die GitHub-API – kein Code-Eingriff nötig.
- Reihenfolge = alphabetisch/numerisch nach Dateiname (z. B. `01.jpg`, `02.jpg`, …).
- Die beiden `sample-*.svg` sind nur Platzhalter – einfach löschen, wenn du eigene Bilder hast.

## Fallback (optional)
Falls die GitHub-API mal nicht erreichbar ist (z. B. Rate-Limit), nutzt die Seite
`images.json` als Reserve-Liste. Wer ganz auf Nummer sicher gehen will, kann die
Dateinamen dort eintragen:

```json
["01.jpg", "02.jpg", "03.jpg"]
```

Für den Normalbetrieb ist das **nicht** nötig.
