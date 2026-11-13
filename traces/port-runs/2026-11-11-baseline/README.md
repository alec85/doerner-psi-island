# Läufe der Portierung: Baseline vom 2026-11-11

Gesicherter Stand des portierten PSI vor Beginn von Phase 3 (ADR 0016). Code: Branch `baseline/referenzmodus-2026-11-11` (Commit `f601e11`, entspricht `main` nach PR #32). Ein Git-Tag und ein GitHub-Release ließen sich aus der Agenten-Session nicht anlegen; Alec kann beides nachholen:

```bash
git tag -a baseline-referenzmodus-2026-11-11 f601e11 -m "Baseline Referenzmodus"
git push origin baseline-referenzmodus-2026-11-11
```

Archive (je Seed die Trace-Datei nach ADR 0006 und `metrics.json`; Prüfsummen in `SHA256SUMS`):

| Datei | Inhalt | Auswertung |
|---|---|---|
| `runs-referenzmodus-1001-1100.tar.gz` | Referenzmodus, Stufe B | `analysis/referenzlaeufe/stufe-b/` |
| `runs-pilot-901-905.tar.gz` | Referenzmodus, Pilot | `analysis/referenzlaeufe/pilot/` |
| `runs-moderner-modus-1001-1100.tar.gz` | alle Schalter aus ADR 0015 | `analysis/grundlinie-modern/`, `analysis/varianten/all-100/` |

Entpacken nach `runs/` stellt die Verzeichnisse wieder her, die `scripts/compare_variants.py` erwartet:

```bash
mkdir -p runs && for f in traces/port-runs/2026-11-11-baseline/*.tar.gz; do tar xzf "$f" -C runs; done
```

Die Rohprotokolle (`raw/`) sind nicht enthalten; `scripts/run_port.py` erzeugt sie für jeden Seed in etwa 4 Minuten neu.
