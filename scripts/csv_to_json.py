#!/usr/bin/env python3
"""
csv_to_json.py — Konvertiert eine Regatta-Ergebnis-CSV in das Display-JSON-Format.

Verwendung:
  python3 scripts/csv_to_json.py <csv-datei> [--day "Tag 1"] [--date "2026-05-30"]

Umgebungsvariable:
  ANTHROPIC_API_KEY=sk-ant-...   (erforderlich)

Ablauf:
  1. CSV-Datei lesen
  2. Claude (claude-sonnet-4-6) mit präzisem Prompt aufrufen
  3. JSON validieren und in data/results-YYYY-MM-DD.json speichern
  4. data/manifest.json aktualisieren (current = neuer Tag)
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Fehler: 'anthropic' Paket fehlt. Installieren mit: pip install anthropic")
    sys.exit(1)

SYSTEM_PROMPT = """Du bist ein Datenkonverter für Regatta-Ergebnisse.

Du bekommst eine CSV-Datei mit Ergebnissen eines Renntages.
Die Datei enthält Wertungen mehrerer Bewerbe/Bootsklassen.

Es gibt ZWEI Arten von Klassen — du musst sie unterscheiden:
- ORC-Klassen (nach ORC gewertet, gemischte Flotte, z.B. "Alpe Adria Cup",
  "Kärntner Cruising Trophy"): hier gibt es die Gesamtwertung UND die
  Einzelrennen des Tages. → type "orc"
- Einheitsklassen / One-Design (alle Boote gleich, z.B. "Austria Cup / First 35",
  "Kärntner Racing Cup / Dehler 38 SQ", "Alpe Adria Racing Cup / First 36"):
  hier wird NUR die Gesamtwertung gebraucht, KEINE Einzelrennen. → type "onedesign"

So erkennst du den Typ: Steht "ORC" im Klassennamen oder gibt es ORC-spezifische
Spalten (z.B. berechnete Zeiten, "ORC")? → "orc". Handelt es sich um eine
Einheitsklasse (ein Bootstyp wie "First 35", "Dehler 38", "First 36")? → "onedesign".
Im Zweifel: wenn nur eine Gesamtwertung ohne sinnvolle Einzelrennen vorliegt → "onedesign".

Deine Aufgabe:
1. Erkenne alle enthaltenen Klassen/Bewerbe anhand von Überschriften oder Abschnitten.
2. Bestimme für jede Klasse den type ("orc" oder "onedesign").
3. Erkenne für jede Klasse:
   - Die Gesamtwertung ("Gesamt", "Total", "Punkte", "Net Pts" o.ä.) — immer.
   - NUR bei ORC-Klassen zusätzlich alle Einzelrennen des Tages
     ("R1", "R2", "R3", "Race 1", "Renn 1", "Lauf 1" o.ä.).
   - Bei Einheitsklassen: "races" als leeres Array [] lassen.
4. Extrahiere pro Boot (für Gesamtwertung UND jedes Einzelrennen):
   - pos: Platzierung (String, z.B. "1", "2", "DNF" bei Nichtantritt)
   - sail: Segelnummer (String, exakt wie in CSV)
   - boat: Bootsname (String, exakt wie in CSV)
   - skipper: Skipper/Steuermann (String, exakt wie in CSV)
   - club: Verein oder Club (String, leer "" wenn nicht vorhanden)
   - pts: Punkte oder Ergebnis (String, z.B. "7", "DNF", "DSQ", "DNC", "OCS")

WICHTIG:
- Verändere KEINE Daten: keine Korrekturen, keine Umbenennungen, keine Ergänzungen.
- Alle Felder exakt so übernehmen wie in der CSV (Großschreibung, Sonderzeichen, Leerzeichen).
- Sonderwerte wie DNF, DSQ, DNC, OCS, RET bleiben als String unverändert.
- Wenn ein Feld fehlt, verwende einen leeren String "".
- Die Reihenfolge der Boote entspricht der CSV-Reihenfolge (= Wertungsreihenfolge).

Ausgabeformat (NUR dieses JSON-Objekt, keine Erklärungen, kein Markdown):
{
  "date": "<Datum aus CSV oder Dateiname, Format: TT. Monat JJJJ>",
  "dayLabel": "<Renntag-Bezeichnung, z.B. 'Tag 1', 'Day 1'>",
  "classes": [
    {
      "name": "<Klassenname exakt wie in CSV>",
      "type": "orc",
      "overall": [
        { "pos": "1", "sail": "AUT 123", "boat": "Bootname", "skipper": "Name", "club": "YCA", "pts": "7" }
      ],
      "races": [
        {
          "label": "Rennen 1",
          "rows": [
            { "pos": "1", "sail": "AUT 123", "boat": "Bootname", "skipper": "Name", "club": "YCA", "pts": "1" }
          ]
        }
      ]
    },
    {
      "name": "<Einheitsklasse, z.B. 'Austria Cup / First 35'>",
      "type": "onedesign",
      "overall": [
        { "pos": "1", "sail": "AUT 351", "boat": "Bootname", "skipper": "Name", "club": "YCA", "pts": "5" }
      ],
      "races": []
    }
  ]
}"""


def convert_csv(csv_path: Path, day_label: str, date_str: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Fehler: ANTHROPIC_API_KEY Umgebungsvariable nicht gesetzt.")
        sys.exit(1)

    csv_content = csv_path.read_text(encoding="utf-8-sig", errors="replace")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Renntag: {day_label}\n"
                    f"Datum: {date_str}\n\n"
                    f"CSV-Inhalt:\n```\n{csv_content}\n```"
                ),
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # JSON aus Antwort extrahieren (falls Markdown-Blöcke vorhanden)
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not json_match:
        print("Fehler: Claude hat kein JSON zurückgegeben.")
        print("Antwort:", response_text[:500])
        sys.exit(1)

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"Fehler: JSON-Parsing fehlgeschlagen: {e}")
        print("Antwort:", response_text[:500])
        sys.exit(1)

    # date/dayLabel aus Argumenten überschreiben, falls nicht in JSON
    if date_str:
        data["date"] = date_str
    if day_label:
        data["dayLabel"] = day_label

    return data


def update_manifest(data_dir: Path, day_file: str, date_str: str):
    manifest_path = data_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {"current": "", "days": []}

    if day_file not in manifest["days"]:
        manifest["days"].append(day_file)
    manifest["current"] = date_str

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"  manifest.json aktualisiert: current={date_str}")


def main():
    parser = argparse.ArgumentParser(description="Regatta-CSV → Display-JSON")
    parser.add_argument("csv_file", help="Pfad zur CSV-Datei")
    parser.add_argument("--day", default="", help='Renntag-Bezeichnung, z.B. "Tag 1"')
    parser.add_argument("--date", default="", help='Datum, z.B. "2026-05-30"')
    args = parser.parse_args()

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"Fehler: Datei nicht gefunden: {csv_path}")
        sys.exit(1)

    # Datum aus Argument oder heute
    date_str = args.date or date.today().strftime("%d. %B %Y")
    day_label = args.day or "Tag 1"

    # Ausgabedateiname aus Datum ableiten
    safe_date = re.sub(r"[^\w]", "-", date_str).strip("-")
    day_file = f"results-{safe_date}.json"

    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    out_path = data_dir / day_file

    print(f"Konvertiere: {csv_path} → {out_path}")
    print(f"  Tag: {day_label}, Datum: {date_str}")
    print("  Rufe Claude API auf…")

    data = convert_csv(csv_path, day_label, date_str)

    classes = data.get("classes", [])
    print(f"  Erkannte Klassen: {[c['name'] for c in classes]}")
    for cls in classes:
        races = cls.get("races", [])
        print(f"    {cls['name']}: {len(cls.get('overall',[]))} Boote, {len(races)} Rennen")

    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"  Gespeichert: {out_path}")

    update_manifest(data_dir, day_file, date_str)
    print("Fertig.")


if __name__ == "__main__":
    main()
