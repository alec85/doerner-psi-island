# ADR 0002: Python als Implementierungssprache

- Status: angenommen
- Datum: 2026-11-09
- Autor: Claude Code

## Kontext

Das Original ist in Delphi geschrieben. Die Neuimplementierung soll später Spiking Neural Networks, Robotiksimulation und den PiCrawler einbinden und als Grundlage für Publikationen dienen.

## Entscheidung

Python 3.12 oder neuer, Paketlayout mit `src/psi_gw/`, Tests mit `pytest`, numerische Arbeit mit NumPy.

## Betrachtete Alternativen

- Rust oder C++: schneller, aber deutlich schwerer an SNN-Bibliotheken (snnTorch, Norse, Brian2), MuJoCo-Bindings und das Python-SDK des PiCrawlers anzubinden.
- Julia: gut für Numerik, kleineres Ökosystem für Robotik und weniger verbreitet in der Zielcommunity.

## Konsequenzen

Leistungskritische Teile können später gezielt vektorisiert oder ausgelagert werden. Die Ökosysteme für SNN, Simulation und den PiCrawler sind direkt nutzbar.
