# Report dimostrativo — Rischio di coda

> Esempio sintetico. Tutti i valori e le date sono fittizi.

## Perimetro

| Campo | Valore dimostrativo |
|---|---|
| Asset | DEMO-ASSET |
| Frequenza | 1 giorno |
| Orizzonte | 1 giorno |
| Livello di confidenza | 95% |
| Metodo principale | Quantile model |
| Benchmark | Historical simulation |

## Metriche di rischio

| Metrica | Valore dimostrativo | Interpretazione |
|---|---:|---|
| VaR 95% | -2,10% | Soglia di perdita stimata |
| Expected Shortfall | -3,05% | Perdita media oltre il VaR |
| Violazioni osservate | 4,8% | Vicino al 5% atteso |
| Massima eccedenza | -4,70% | Evento sintetico più severo |

## Test di coverage

| Test | p-value dimostrativo | Esito |
|---|---:|---|
| Kupiec | 0,63 | Pass |
| Christoffersen | 0,18 | Pass |
| Conditional coverage | 0,27 | Pass |

## Stress sintetico

Un aumento del 30% della volatilità porta il VaR dimostrativo a -2,75% e l'Expected Shortfall a -4,10%. L'esempio evidenzia come il report separi scenario base e stress.

## Sintesi

La calibrazione appare coerente nel campione sintetico, ma la decisione richiederebbe verifica su più periodi e regimi. Nessuna metrica è riferita a un asset reale.
