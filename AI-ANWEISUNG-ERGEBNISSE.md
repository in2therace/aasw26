# KI-Anweisung: Regatta-Ergebnisse aus CSV konvertieren

Diese Datei enthält den Prompt, mit dem eine KI (z.B. Claude) eine Ergebnis-CSV
in das Display-JSON-Format umwandelt. Entweder manuell (Copy-Paste in Claude.ai)
oder automatisch über `scripts/csv_to_json.py`.

---

## Prompt (kopieren und mit der CSV einfügen)

```
Du bist ein Datenkonverter für Regatta-Ergebnisse.

Du bekommst eine CSV-Datei mit den Ergebnissen eines Renntages.
Die Datei enthält die Wertungen mehrerer Bewerbe/Bootsklassen.

Es gibt ZWEI Arten von Klassen — unterscheide sie:
- ORC-Klassen (gemischte Flotte, nach ORC gewertet, z.B. "Alpe Adria Cup",
  "Kärntner Cruising Trophy"): Gesamtwertung UND Einzelrennen des Tages.
  → "type": "orc"
- Einheitsklassen / One-Design (ein Bootstyp, z.B. "Austria Cup / First 35",
  "Kärntner Racing Cup / Dehler 38 SQ", "Alpe Adria Racing Cup / First 36"):
  NUR die Gesamtwertung wird gebraucht, KEINE Einzelrennen.
  → "type": "onedesign", "races": []

Typ-Erkennung: "ORC" im Namen oder ORC-Spalten (berechnete Zeiten) → "orc".
Reiner Bootstyp-Name als Einheitsklasse → "onedesign". Im Zweifel, wenn keine
sinnvollen Einzelrennen vorliegen → "onedesign".

Deine Aufgabe:
1. Erkenne alle enthaltenen Klassen/Bewerbe (anhand von Abschnittsüberschriften,
   Leerzeilen oder Klassenbezeichnungen in der CSV).
2. Bestimme für jede Klasse den "type" ("orc" oder "onedesign").
3. Erkenne für jede Klasse:
   - Die Gesamtwertung (Spalten wie "Gesamt", "Total", "Net Pts", "Punkte", "Nettopunkte") — immer.
   - NUR bei ORC-Klassen zusätzlich alle Einzelrennen des Tages
     (Spalten wie "R1", "R2", "R3", "Race 1", "Rennen 1", "Lauf 1").
   - Bei Einheitsklassen: "races" als leeres Array [] lassen.
4. Extrahiere pro Boot die folgenden Felder — für die Gesamtwertung UND für jedes Einzelrennen:
   - pos:     Platzierung (String, z.B. "1"; bei Nichtfinish: "DNF", "DSQ" etc.)
   - sail:    Segelnummer (String, exakt wie in CSV)
   - boat:    Bootsname (String, exakt wie in CSV)
   - skipper: Skipper oder Steuermann (String, exakt wie in CSV)
   - club:    Verein oder Club (String, leer "" wenn nicht vorhanden)
   - pts:     Punkte oder Ergebnis des Rennens (String, z.B. "1", "7", "DNF", "DSQ")

WICHTIG — diese Regeln sind absolut verbindlich:
- Verändere KEINE Daten: keine Korrekturen, keine Umbenennungen, keine Normalisierungen.
- Alle Felder exakt so übernehmen wie in der CSV, inklusive Großschreibung, Sonderzeichen
  und Leerzeichen (z.B. "AUT 123" bleibt "AUT 123", nicht "AUT123").
- Sonderwerte wie DNF, DSQ, DNC, OCS, RET, BFD bleiben als String erhalten.
- Wenn ein Feld in der CSV fehlt, verwende einen leeren String "".
- Die Reihenfolge der Boote entspricht der Reihenfolge in der CSV (= Wertungsreihenfolge).
- Antworte NUR mit dem JSON-Objekt, keine Erklärungen, kein Markdown (keine ```-Blöcke).

Ausgabeformat:
{
  "date": "<Datum, z.B. '30. Mai 2026'>",
  "dayLabel": "<Bezeichnung des Renntages, z.B. 'Tag 1'>",
  "classes": [
    {
      "name": "<Klassenname exakt wie in CSV, z.B. 'Alpe Adria Cup (ORC)'>",
      "type": "orc",
      "overall": [
        {
          "pos": "1",
          "sail": "AUT 123",
          "boat": "Segelboot",
          "skipper": "Max Muster",
          "club": "YCA",
          "pts": "7"
        }
      ],
      "races": [
        {
          "label": "Rennen 1",
          "rows": [
            {
              "pos": "1",
              "sail": "AUT 123",
              "boat": "Segelboot",
              "skipper": "Max Muster",
              "club": "YCA",
              "pts": "1"
            }
          ]
        }
      ]
    },
    {
      "name": "<Einheitsklasse, z.B. 'Austria Cup / First 35'>",
      "type": "onedesign",
      "overall": [
        {
          "pos": "1",
          "sail": "AUT 351",
          "boat": "Segelboot",
          "skipper": "Max Muster",
          "club": "YCA",
          "pts": "5"
        }
      ],
      "races": []
    }
  ]
}
```

---

## Verwendung

### Manuell (Claude.ai / beliebige KI)

1. Den Prompt oben kopieren.
2. Darunter den Inhalt der CSV-Datei einfügen (als Text, nicht als Anhang).
3. Oben im Prompt `"date"` und `"dayLabel"` anpassen:
   ```
   Renntag: Tag 1
   Datum: 30. Mai 2026
   ```
4. Das zurückgegebene JSON als `data/results-2026-05-30.json` ins Repo speichern.
5. `data/manifest.json` anpassen:
   ```json
   {
     "current": "2026-05-30",
     "days": ["results-DEMO.json", "results-2026-05-30.json"]
   }
   ```
   `"current"` auf den Dateinamen-Teil des neuen Tages setzen (ohne `results-` und `.json`).

### Automatisiert (GitHub Action)

1. **Einmalige Einrichtung:**
   - GitHub → Repo-Settings → Secrets and variables → Actions
   - Neues Secret: Name `ANTHROPIC_API_KEY`, Wert: dein API-Key von console.anthropic.com
   - Auch sicherstellen: Settings → Actions → General → Workflow permissions → „Read and write permissions" ✓

2. **Pro Renntag:**
   - CSV-Datei in den `csv/`-Ordner legen (z.B. `csv/tag1.csv`)
   - Committen und pushen
   - GitHub Action läuft automatisch (~1 Minute), erzeugt `data/results-*.json`
     und aktualisiert `manifest.json`
   - Display zeigt die neuen Ergebnisse beim nächsten Refresh (alle 3 Min)

   Alternativ manuell starten: GitHub → Actions → „Ergebnis-CSV verarbeiten" → „Run workflow"

### Lokal (Python-Skript direkt)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic

python3 scripts/csv_to_json.py csv/tag1.csv --day "Tag 1" --date "30. Mai 2026"
```

---

## Datenformat erklärt

**`data/manifest.json`** — steuert welcher Tag angezeigt wird:
```json
{
  "current": "2026-05-30",
  "days": ["results-DEMO.json", "results-2026-05-30.json", "results-2026-05-31.json"]
}
```
- `"current"`: muss einen String-Teil des gewünschten Dateinamens enthalten.
- `"days"`: Liste aller vorhandenen Tages-Dateien (ältere bleiben erhalten).

**Pro Tag:** `data/results-YYYY-MM-DD.json`
- `date`: Anzeigedatum (frei formatierbar, z.B. "30. Mai 2026")
- `dayLabel`: Kurzbezeichnung (z.B. "Tag 1")
- `classes`: Array aller Klassen/Bewerbe
  - `type`: `"orc"` (Gesamt + Einzelrennen) oder `"onedesign"` (nur Gesamt)
  - `overall`: Gesamtwertung (Array von Boot-Objekten)
  - `races`: Array der Tagesrennen, jedes mit `label` und `rows`
    (bei `"onedesign"` leer `[]`)

**Anzeige je nach Typ:**
- `"orc"` → 1 Slide Gesamtwertung + 1 Slide pro Rennen (im Lauf der Woche bis zu 10).
- `"onedesign"` → nur 1 Slide Gesamtwertung (keine Einzelrennen/Namenslisten).

**Karussell-Reihenfolge** (Beispiel: 1 ORC-Klasse mit 2 Rennen + 1 Einheitsklasse):
```
Alpe Adria Cup (ORC) — Gesamtwertung  [15 s]
Alpe Adria Cup (ORC) — Rennen 1       [15 s]
Alpe Adria Cup (ORC) — Rennen 2       [15 s]
Austria Cup / First 35 — Gesamtwertung[15 s]
→ Wiederholung
```
