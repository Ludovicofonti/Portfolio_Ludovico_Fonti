# 🎬 Redditività di un Investimento nel Settore Media USA

> **Progetto Universitario** · Università Politecnica delle Marche · *Lavoro di gruppo*

## 📌 Contesto

Dataset finanziario del **Russell 3000** con **2.493 osservazioni** e 13 variabili. Il progetto analizza la redditività di un investimento nel settore media statunitense, stimando l'**EPS (Earnings Per Share — utile per azione) a 12 mesi** tramite regressione lineare. Il modello viene poi applicato a un campione di **aziende italiane del settore media** per valutare la competitività di un potenziale ingresso nel mercato USA.

## 🏗️ Pipeline di Analisi

### 1. Preprocessing & Feature Engineering
- Rilevazione e rimozione degli outlier con **Isolation Forest** (tecnica ML per anomaly detection)
- **Z-score standardization** su tutte le variabili numeriche
- **Trasformazione logaritmica** sulle variabili con distribuzione asimmetrica: `Net Sales`, `Free Cash Flow`, `EPS 12M Forward`, `Enterprise Value`, `EBITDA`

### 2. Analisi della Correlazione e Multicollinearità
- Costruzione della matrice di correlazione e analisi degli autovalori
- Condition Number iniziale: **105.775** (forte multicollinearità) → dopo rimozione di `ROIC`: **17.883** (accettabile)
- Scelta motivata: `ROIC` rimossa (ridondante con `ROA`); `EBITDA` e `Free Cash Flow` mantenute nonostante correlazione 0.80, perché misurano dimensioni finanziarie distinte

### 3. Modellazione — Regressione Lineare
- Variabile target: `EPS 12M Forward` (utile per azione previsto a 12 mesi)
- Test diagnostici: Shapiro-Wilk, Kolmogorov-Smirnov, Cramer-von Mises (normalità residui), test di Breusch-Pagan (eteroschedasticità)

## 📊 Risultati del Modello

| Metrica | Valore |
|---------|--------|
| R² | **0.5236** (il modello spiega il 52% della variabilità dell'EPS) |
| Errore residuo standard | 0.7303 |
| p-value globale | < 2.2e⁻¹⁶ |

## 🔍 Driver dell'EPS — Coefficienti e Interpretazione

| Variabile | Coefficiente | Impatto sull'EPS | IC 95% |
|-----------|:-----------:|-----------------|--------|
| `ROA` | +0.542 | **+54.2%** per σ — uso efficiente degli asset | 0.488 – 0.592 |
| `Free Cash Flow` | +0.456 | **+45.6%** per σ — liquidità disponibile post-investimenti | 0.324 – 0.617 |
| `EBITDA` | +0.368 | **+36.8%** per σ — solidità operativa | 0.199 – 0.536 |
| `Net Sales` | +0.219 | **+21.9%** per σ — fatturato come motore di redditività | 0.136 – 0.314 |
| `Enterprise Value` | −0.352 | **−35.2%** per σ — crescita dimensionale non garantisce EPS più alto | −0.449 – −0.265 |
| `ROE` | ~0 | Effetto non significativo | −0.034 – 0.053 |

> **Nota sull'Enterprise Value:** l'impatto negativo riflette la legge dei rendimenti decrescenti — oltre una certa soglia, la crescita del valore d'impresa si accompagna a costi operativi più elevati e investimenti meno efficienti, comprimendo l'EPS.

## 🌍 Applicazione al Mercato Italiano

Il modello è stato applicato a un campione di **aziende italiane del settore media** per confrontarne l'EPS stimato con quello delle aziende americane del Russell 3000:

- Le aziende italiane mostrano **forte variabilità** e sono generalmente **meno competitive** rispetto alle americane
- Il mercato USA è più strutturato, con economie di scala e maggiore accesso ai capitali
- Solo le aziende italiane con solidi `Net Sales`, `Free Cash Flow` e `ROA` avrebbero reali possibilità di competere

## 💡 Insight Operativi

- **Ottimizzare il ROA**: massimizzare il valore generato dalle risorse disponibili è il principale driver di EPS
- **Evitare crescita non controllata dell'Enterprise Value**: rischio di rendimenti decrescenti e perdita di efficienza
- **Monitorare il ROE** senza farne una priorità: non è un fattore chiave nel modello, ma va tenuto sotto controllo per intercettare inefficienze

## 🧰 Tech Stack

`R` · `Regressione Lineare` · `Isolation Forest` · `Z-score Standardization` · `Trasformazione Logaritmica` · `Test di Breusch-Pagan` · `Shapiro-Wilk`

## 🏷️ Tags

`Regressione` · `Finance` · `Media` · `Russell 3000` · `EPS Forecasting` · `Analisi Finanziaria`
