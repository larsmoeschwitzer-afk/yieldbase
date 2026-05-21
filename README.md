# YieldBase v3 — Immobilien-Investment-Analyse

Python/Streamlit-App für professionelle Immobilien-Investment-Analysen.

## Features

- **Bundesland-Selektor** → Grunderwerbsteuer automatisch (3,5 %–6,5 %)
- **AfA-Automatik** aus Baujahr nach § 7 Abs. 4 EStG (2,0 % / 2,5 % / 3,0 %)
- **KNK-Aufschlüsselung**: Grunderwerbsteuer + Notar/Grundbuch + Makler
- **Alle KPIs**: Bruttorendite, Netto-Rendite, Cap Rate, DSCR, LTV, ROE, IRR, NPV, MOIC, Break-Even u.v.m.
- **Szenario-Vergleich**: Optimistisch / Realistisch / Pessimistisch
- **Interaktive Charts**: Cashflow-Projektion, Equity Buildup, Kostenstruktur-Donut
- **Ampel-System**: Grün / Gelb / Rot mit Branchen-Benchmarks
- **Premium Light-Design** mit Custom CSS

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Geprüfte Formeln (Audit v2.1)

| KPI | Formel | Korrektur |
|-----|--------|-----------|
| LTV | FK / **Kaufpreis** | ✅ (nicht / Gesamtinvestition) |
| MOIC | (kum. CFs + Terminal Equity) / EK | ✅ (inkl. Cashflows) |
| Break-Even-Miete | KD / (1 − bew% − **leerstand%**) | ✅ (inkl. Leerstand) |
| Tilgungsmodell | Annuitätendarlehen (konstante Rate) | ✅ (nicht feste Tilgungs-%) |
| nettoMiete | Miete − Bew. − Leerstand − **IHR** | ✅ (konsistente Basis) |
| IHR | Kaufpreis × altersgestaffelter Satz | ✅ (reduzierte Sätze) |

## Verzeichnisstruktur

```
.
├── app.py             # Haupt-App
├── requirements.txt   # Python-Abhängigkeiten
└── README.md          # Diese Datei
```
