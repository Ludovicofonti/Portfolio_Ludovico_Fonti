# 🔧 Documentazione Architetturale — Pipeline ML di Scoring Efficacia

Descrizione dell'architettura, dei componenti e del flusso logico della pipeline di scoring.

## Indice

- [Architettura](#architettura)
- [Componenti principali](#componenti-principali)
- [Flusso di esecuzione](#flusso-di-esecuzione)
- [Approcci tecnici](#approcci-tecnici)
- [Validazione](#validazione)
- [Interpretabilità](#interpretabilità)

---

## Architettura

La pipeline segue un'architettura a **3 componenti indipendenti** che vengono combinati in uno score finale:

```
Dataset Geospaziale
    │
    ├─→ Caricamento & Validazione
    │
    ├─→ Feature Selection (Multi-Stadio)
    │   ├─ Esclusione (varianza quasi-nulla)
    │   ├─ Decorrelazione (correlazione pairwise + VIF)
    │   └─ Importanza (permutazione)
    │
    ├─→ Confronto Algoritmi (Validazione Spaziale)
    │   └─ Gradient Boosting variants vs baseline
    │
    ├─→ Training Modelli Predittivi (in parallelo)
    │   ├─ Modello Componente 1: Flusso pedonale
    │   └─ Modello Componente 2: Esposizione veicolare
    │       └─ (con fallback per basse performance)
    │
    ├─→ Scoring Composito
    │   └─ Aggregazione pesata (30% + 40% + 30%)
    │
    ├─→ Validazione Automatica
    │   └─ Suite di test (distribuzione, face validity, ranking, bias)
    │
    └─→ Interpretazione Multi-Metodo
        ├─ SHAP (feature importance globale)
        ├─ Modelli surrogati (Ridge, alberi)
        ├─ Accumulated Local Effects (ALE)
        ├─ Analisi residui
        └─ Report Markdown
```

---

## Componenti principali

La pipeline è composta da **6 componenti logici indipendenti**:

### 1. Data Loading & Validation
- Caricamento da GeoPackage
- Validazione schema (presence, type, range)
- Filtri geografici e qualità

### 2. Feature Selection (Multi-Stadio)

| Stadio | Criterio | Logica |
|--------|----------|--------|
| **1 — Hard Exclusion** | Varianza quasi-nulla + feature amministrative | Rimozione feature costanti e non informative |
| **2 — Decorrelazione** | Correlazione pairwise + VIF iterativo | Prevenzione multicollinearity; bypass per feature categoriche |
| **3 — Permutation Importance** | Ranking importanza su holdout set | Retention delle feature effettivamente predittive |

**Output**: ~60% riduzione dello spazio features (da ~60 a ~35 feature per modello)

### 3. Algoritmi Comparison

Confronti tramite **Cross-Validazione Spaziale** (griglia geografica):
- **Algoritmi testati**: Gradient Boosting (baseline + varianti), algoritmi alternativi
- **Metrica**: R² medio su fold spaziali
- **Wrapper**: Trasformazione log del target per stabilizzazione variance
- **Output**: Ranking algoritmi con CV estimates

### 4. Training Modelli Predittivi

**Modello 1 — Componente Flusso Pedonale**
- **Target**: Metriche di flusso pedonale (log-trasformato)
- **Training set**: Subset con osservazioni dirette (~55% della popolazione)
- **Predizione**: Coverage 100% (imputazione per missing)
- **Monitoraggio**: R², RMSE, distribuzione predizioni vs osservate

**Modello 2 — Componente Esposizione Veicolare**
- **Target**: Metriche di esposizione veicolare (log-trasformato)
- **Training set**: Subset con osservazioni dirette (~96% della popolazione)
- **Fallback Mechanism**: Se performance modello insufficiente:
  - Divisione geografica in zone
  - Mediana metriche per zona (min 10 campioni; altrimenti globale)
  - Flag per record imputati
- **Monitoraggio**: R², RMSE, trigger fallback

### 5. Scoring Composito

**Aggregazione Pesata** (3 componenti indipendenti):
```
score_finale = w₁·ATTR + w₂·PED + w₃·VEH
```

**Normalizzazione** (configurabile):
- **Relativa** (percentile rank): Ranking all'interno della popolazione
- **Assoluta** (CDF calibrata): Score stabile nel tempo, su scala [0,1]

**Metriche di validità**:
- Variance decomposition: contributo effettivo vs peso nominale
- Sensitivity analysis: stabilità ranking sotto perturbazioni pesi ±5%

### 6. Validazione Automatica

**Suite di test** con esito PASS/FAIL:

| Categoria | Test | Logica |
|-----------|------|--------|
| **Distribuzione** | Media, range, concentrazione | Distribuzioni sensate e senza estremi |
| **Face Validity** | Top-20 vs bottom-20 comparabilità | Coerenza con logica business |
| **Discriminazione** | Potere discriminante, variabilità | Score differenzia adeguatamente |
| **Assenza Bias** | Uniformità per categoria/zona | Nessun bias sistematico per sottogruppi |
| **Stabilità** | Ranking pre/post imputazione, sensibilità pesi | Score robusto a perturbazioni minori |

**Output**: Report PASS/FAIL per ciascun test; abortisce se fail critici.

---

## Flusso di esecuzione

La pipeline è composta da **6 step sequenziali**, ciascuno rieseguibile indipendentemente:

### Step 1: Feature Selection
Eseguita separatamente per ciascun modello predittivo. **Approccio**: Multi-stadio automatico con report dettagliato. Rimuove feature: (1) costanti/near-costanti; (2) altamente correlate; (3) non predittive.

### Step 2: Confronto Algoritmi
Test comparativo di algoritmi di Gradient Boosting e baseline. Validazione incrociata spaziale per prevenire data leakage geografico.

### Step 3-4: Training Modelli
Addestramento separato di due modelli predittivi su subset con osservazioni dirette. Imputazione per coverage 100%.

### Step 5: Scoring Composito
Aggregazione pesata delle 3 componenti con normalizzazione configurabile (relativa o assoluta).

### Step 6: Validazione
Suite automatica di test per verificare distribuzione, coerenza e stabilità dello score.

## Approcci tecnici

### Cross-Validazione Spaziale
**Problema**: Impianti geograficamente vicini sono correlati → validazione standard sovrastima performance.

**Soluzione**: Griglia geografica con train/test split spazialmente separati.
- Previene data leakage
- CV estimate più conservativa e realistica
- Applicabile per qualsiasi target spaziale

### Fallback Mechanism
**Problema**: Modello per esposizione veicolare ha performance variabile tra aree geografiche.

**Soluzione**: Auto-detection di bassa performance e fallback a mediane spaziali.
- Mantiene data-driven dove possibile
- Graceful degradation in aree difficili
- Flag trasparente per record imputati

### Normalizzazione Configurabile
**Modalità Relativa** (percentile rank):
- Score: ranking all'interno della popolazione
- Use case: Confronti interni, identificazione top/bottom performers

**Modalità Assoluta** (CDF calibrata):
- Score: scala [0,1] stable nel tempo
- Use case: Benchmark esterni, transferability tra periodi
- Parametri salvati e versionati

### Trasformazione Log del Target
Stabilizza variance, riduce influenza outlier, migliora fit normale dei residui.

## Validazione

La suite di validazione automatica comprende test su:

- **Distribuzione**: Media, range, concentration dei score
- **Face Validity**: Coerenza top-20 e bottom-20 con logica business
- **Discriminazione**: Potere discriminante dello score, assenza clustering
- **Bias Geografico/Categorico**: Uniformità per sottogruppi
- **Stabilità**: Robustezza del ranking a perturbazioni minori dei parametri
- **Imputazione**: Similarità distribuzione tra osservati e imputati

**Output**: Report PASS/FAIL con annotazioni dettagliate. Abortisce pipeline se fail critici.

## Interpretabilità

Suite completa di metodi di interpretazione incrociati:

| Metodo | Approccio | Caso d'uso |
|--------|-----------|-----------|
| **SHAP** | Feature importance globale (Shapley values) | Ranking feature, importanza media per feature |
| **Ridge Surrogate** | Regressione lineare su feature grezze | Coefficienti interpretabili, segni, sensibilità |
| **Decision Tree Surrogate** | Albero shallow (max_depth=5) | Regole "if-then" estratte, logic interpretabili |
| **ALE** (Accumulated Local Effects) | Effetti marginali locali per feature | Relazioni feature-target non lineari |
| **Analisi Residui** | Esame errori per categoria/zona | Overfitting locale, bias geografico |
| **Aggregazione Macro-Categoria** | Raggruppamento SHAP per dominio | Contributo per macro-area (urbanistica, accessibilità, etc.) |

**Report Multi-Metodo**: Generato in Markdown, confronta i 6 metodi, evidenzia concordanze/discordanze.

---

> **Nota**: I dettagli implementativi specifici, i dati di input e i modelli serializzati non sono inclusi nel portfolio per motivi di riservatezza aziendale.
