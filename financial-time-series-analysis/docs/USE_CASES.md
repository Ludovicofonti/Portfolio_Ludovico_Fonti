# Casi d'uso

## 1. Forecast del rendimento

Domanda: un modello migliora la previsione del rendimento rispetto a una baseline nulla o storica?

Flusso:

1. costruzione del dataset point-in-time;
2. split walk-forward;
3. confronto tra modello e baseline;
4. test di significatività;
5. valutazione al netto dei costi.

Output: metriche predittive, stabilità temporale, decisione di promozione e report forecast.

## 2. Classificazione della direzione

Domanda: il segnale distingue movimenti positivi e negativi con sufficiente stabilità?

Flusso:

1. definizione del target direzionale;
2. addestramento senza leakage;
3. balanced accuracy e hit rate;
4. trasformazione del segnale in esposizione;
5. sensitivity ai costi.

Output: confusion matrix, performance per regime e report strategia.

## 3. Volatilità condizionale

Domanda: la previsione di volatilità è calibrata e utile per controllare l'esposizione?

Flusso:

1. baseline rolling;
2. modello GARCH Student-t;
3. walk-forward;
4. controllo della calibrazione;
5. confronto per regime.

Output: errore di previsione, coverage, serie della volatilità e indicatori di rischio.

## 4. Rischio di coda

Domanda: VaR ed Expected Shortfall descrivono adeguatamente le perdite estreme?

Flusso:

1. stima di quantili e coda;
2. test di Kupiec e Christoffersen;
3. conditional coverage;
4. analisi delle violazioni;
5. confronto con EVT.

Output: report rischio, tasso di violazione, severità delle eccedenze e gate di affidabilità.

## 5. Data quality per ricerca quantitativa

Domanda: il dataset è sufficientemente completo e temporalmente corretto per una valutazione?

Flusso:

1. test dbt su chiavi e range;
2. controllo di continuità e duplicati;
3. verifica del timestamp di disponibilità;
4. test anti-leakage;
5. tracciamento della configurazione.

Output: stato dei mart, test falliti, perimetro della run e motivi di eventuale blocco.

## Limiti

Questi casi d'uso supportano ricerca e formazione. Non sostituiscono due diligence, gestione professionale del rischio o consulenza finanziaria.
