# Report dimostrativo — Forecast del rendimento

> Esempio sintetico. Tutti i valori e le date sono fittizi.

## Perimetro

| Campo | Valore dimostrativo |
|---|---|
| Asset | DEMO-ASSET |
| Frequenza | 1 ora |
| Orizzonte | 1 periodo |
| Task | Rendimento |
| Modello | Ridge regression |
| Baseline | Rendimento nullo |
| Schema di validazione | Walk-forward |

## Confronto predittivo

| Metrica | Modello | Baseline | Lettura |
|---|---:|---:|---|
| MAE | 0,84% | 0,88% | Miglioramento contenuto |
| RMSE | 1,21% | 1,24% | Differenza marginale |
| Information coefficient | 0,06 | 0,00 | Segnale debole |
| Stabilità finestre | 61% | 50% | Da confermare |

## Gate

| Controllo | Esito dimostrativo |
|---|---|
| Migliora la baseline | Pass |
| Significatività statistica | Warning |
| Stabilità per regime | Warning |
| Performance dopo i costi | Fail |

## Sintesi

Il modello mostra un vantaggio predittivo limitato, ma il beneficio non rimane positivo nello scenario base dei costi. Il risultato dimostrativo non supererebbe il gate di promozione.

## Limiti

- campione sintetico;
- nessuna interpretazione economica reale;
- nessuna indicazione operativa;
- valori non confrontabili con mercati o asset reali.
