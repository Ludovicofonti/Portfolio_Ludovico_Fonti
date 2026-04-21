# 👥 Segmentazione Clienti — Cluster Analysis sulle Vendite

> **Progetto Universitario** · Università Politecnica delle Marche

## 📌 Contesto

Dataset di **2.999 osservazioni** e 18 variabili, con dati di vendita raccolti dal 01/01/2018 al 28/04/2019. L'obiettivo è identificare gruppi di clienti con comportamenti d'acquisto simili per sviluppare strategie di marketing mirate ed efficaci.

## 🏗️ Pipeline di Analisi

### 1. Preprocessing & Pulizia
- Rilevazione e correzione di **valori incoerenti**: es. sconti superiori al prezzo lordo del prodotto
- Ricalcolo di `Net Sales` come differenza corretta tra `Gross Sales` e `Discounts`
- Creazione di `Total.Sales.Correct` (Net Sales + Taxes)
- Rimozione delle righe con `Net Sales = 0` e `Return Item Quantity = 0` contemporaneamente
- **Standardizzazione Z-score** su tutte le variabili numeriche

### 2. Analisi della Correlazione
- Costruzione della matrice di correlazione per identificare ridondanze
- Variabili ad alta correlazione escluse dal clustering: `Total.Sales.Correct`, `Taxes`, `Gross Sales`, `Net Quantity` (correlazione con altre variabili ≥ 0.84–0.99)
- Variabili selezionate per il clustering: `Net.Sales`, `Discounts`, `Returned.Item.Quantity`, `Ordered.Item.Quantity`

### 3. Clustering — PAM (Partitioning Around Medoids)
- Algoritmo scelto per la **robustezza agli outlier** e la gestione di variabili numeriche
- Distanza di **Manhattan** per trattare ogni dimensione in modo indipendente
- Numero ottimale di cluster determinato con **metodo del gomito** + **indice di Silhouette**: **3 cluster**

## 👥 Profili dei Cluster

| Cluster | Profilo | Net Sales (media) | Sconti (media) | Prodotti per ordine |
|---------|---------|:-----------------:|:--------------:|:-------------------:|
| **1 — Low Spenders** | Clienti a bassa spesa, sensibili al prezzo | ~875 | ~-229 | 1 |
| **2 — Regular Buyers** | Acquirenti abituali, acquisti frequenti ma singoli | ~6.117 | significativi | 1 |
| **3 — Big Spenders** | Clienti premium, ordini multipli e alto valore | ~12.600 (max 29.583) | ~-2.941 | 2 (max 4) |

## 🔍 Insight sui Prodotti

- **Prodotto P** (frequenza più alta): acquistato principalmente dal Cluster 2 — prodotto di punta per acquirenti abituali
- **Prodotto A**: prevalente nel Cluster 1 — posizionamento entry-level, clienti price-sensitive
- **Prodotto R**: acquistato **esclusivamente dal Cluster 3** — prodotto premium/nicchia per i Big Spenders

## 💡 Raccomandazioni Strategiche

| Cluster | Strategia consigliata |
|---------|----------------------|
| **Low Spenders** | Sconti progressivi e promozioni a tempo limitato per creare senso di urgenza |
| **Regular Buyers** | Cross-selling (prodotti complementari) e up-selling (fascia più alta) per aumentare il valore per ordine |
| **Big Spenders** | Esperienze esclusive, edizioni limitate, servizi personalizzati — senza stravolgere l'esperienza d'acquisto |

## 🧰 Tech Stack

`R` · `PAM (Partitioning Around Medoids)` · `Distanza di Manhattan` · `Indice di Silhouette` · `Metodo del Gomito` · `Z-score Standardization`

## 🏷️ Tags

`Clustering` · `CRM` · `Apprendimento Non Supervisionato` · `Marketing` · `Sales Analytics` · `PAM`
