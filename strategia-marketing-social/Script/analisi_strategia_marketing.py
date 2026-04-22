# ============================================================================
# Strategia Marketing e Analisi Social — Nuova Comes
# ============================================================================
# Analisi multi-canale delle performance digitali:
#   1. EDA sui contatti HubSpot (provenienza, tipologia, ciclo di vita)
#   2. Analisi delle sorgenti di traffico web (URL di ingresso/uscita)
#   3. Sentiment Analysis delle recensioni (Facebook + Google Maps)
#   4. Text Mining: word cloud e frequenza delle parole chiave
#   5. Analisi delle campagne pubblicitarie Meta (FB / IG)
# ============================================================================

import os
import re
from collections import Counter
from urllib.parse import urlparse

import matplotlib.pyplot as plt
import nltk
import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from wordcloud import WordCloud

# --- Configurazione percorsi e stile -------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Corretto")

HUBSPOT_FILE = os.path.join(
    DATA_DIR, "HUBSPOT",
    "[Comes] - Database Contatti Hubspot 1_10_2023-1_10_2024.xlsx"
)
META_FILE = os.path.join(
    DATA_DIR, "META",
    "FILE SISTEMATO CAMPAGNE META.xlsx"
)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {
    "primary": "#2E86AB",
    "secondary": "#A23B72",
    "accent": "#F18F01",
    "positive": "#2E8B57",
    "negative": "#C0392B",
    "neutral": "#7F8C8D",
}
FIGSIZE = (10, 6)

plt.rcParams.update({
    "figure.dpi": 120,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 11,
})

STOP_WORDS_EXTRA = {
    "più", "tanta", "guidati", "vivamente", "averli", "ben", "ritrovo", "ce",
    "sentire", "assolutamente", "molto", "disponibili", "lascia", "perché",
    "perchè", "è", "realizzare", "finito", "solo", "tutte", "perso", "poco",
    "neanche", "farmi", "progetto", "prossima", "azienda", "infine", "colpa",
    "completamente", "accusato", "saputo", "ancora", "parlare", "presente",
    "ordinando", "potessero", "nonostante", "dopo", "seguiti", "pagato",
    "stati", "trovare", "ora", "consiglio",
}

# --- Dati recensioni ----------------------------------------------------------

FACEBOOK_COMMENTS = [
    "Ci hanno consigliato un pavimento non utilizzabile per l'interno e che si macchia in continuazione (macchie che non vanno via). Piatto doccia che si è imbombato e scolava fuori dalla doccia allagando il bagno ad ogni volta. Il rivestimento del bagno che al momento la posa abbiamo scoperto non potersi posare come avremmo voluto inizialmente fare. Con loro abbiamo avuto solo che problemi, non andateci.",
    "Condivido in maniera assoluta. Consiglio di NON ANDARCI ASSOLUTAMENTE, ora che dopo appena 4 anni da una importante ristrutturazione mi ritrovo a dover completamente rifare un bagno e dovrei rifare il parquet in tutta casa, ecco... CONSIGLIO VIVAMENTE DI NON METTERE PIEDE IN QUESTO POSTO",
    "Precisi e professionali, materiali e mobili di primo livello, venditori top!",
    "Cortesi veloci e professionali!!!",
    "Per il completamento dell'appartamento, in Comes, abbiamo trovato uno showroom eccezionale, con ampia scelta e materiali di qualità. Siamo stati seguiti dall'architetto Paolo Rossini, con cortesia, disponibilità, competenza e professionalità nel proporci e consigliarci al meglio nella scelta.",
    "Professionalità, cortesia e grande disponibilità contraddistinguono Comes e i suoi collaboratori. Uno showroom eccezionale e materiali di qualità sono i loro punti forti, ma il valore aggiunto nella realizzazione del nostro appartamento sono stati Roberto e Vanessa con favolose proposte e tanta pazienza!",
    "Siamo stati seguiti per l'arredamento di tutta la casa con soluzioni belle e funzionali. Roberto ci ha consigliato con grande professionalità e disponibilità riuscendo sempre a trovare risposte efficaci ed eleganti alle nostre esigenze.",
    "Ottimi prodotti, grande team e bella organizzazione!! Un grande showrom dove scegliere materiali arredo bagno, cucine, soggiorni e zona notte!! Consiglio vivamente!!!",
    "Ampia scelta, cortesia e professionalità. Mia moglie ed io siamo stati seguiti da Jessica, la quale oltre ad essere stata estremamente cortese, ci ha consigliato al meglio ed affiancato nella ristrutturazione del nostro appartamento.",
    "Basterebbe poco per capire..",
    "No comment. La mia recensione arriverà appena avrò finito di pulire il bagno dopo che la vasca idro è partita da sola. Per non parlare di tutti gli errori fatti in mille casi. Metterò una stella solo perché 0 non è possibile.",
    "Ma fosse solo la vasca! Ora mi tocca rifare completamente un bagno, per non parlare del parquet.",
    "Un team di professionisti competenti, seri e gentili (cosa per nulla scontata da trovare!!!). Consigliati",
    "Ottimo",
    "Grande professionalità e qualità",
]

GOOGLE_MAPS_REVIEWS = [
    "Dovendo ristrutturare il bagno di casa ci siamo rivolti alla Comes di Ancona perché secondo noi è sinonimo di alta qualità dei materiali e dei prodotti trattati. Nel nostro percorso siamo stati guidati dalla grande professionalità e bravura di Alice Pierantoni che ha saputo soddisfare tutte le nostre richieste con un ottimo risultato finale! Un pensiero particolare va anche a Francesca Belfiori che con la sua simpatia ed i suoi modi garbati ti fa sentire subito ben accolto! Tenetevi pronti per la prossima ristrutturazione.",
    "Abbiamo da poco finito di ristrutturare la nostra casa e ci siamo affidati alla Comes Ancona per la fornitura di pavimenti, rivestimenti, sanitari, arredi bagno ed infine anche per la cucina. Alice ci ha accompagnato in questo lungo viaggio, si é dedicata completamente a noi e al nostro progetto, capendo le nostre necessità e il nostro gusto, sempre presente anche in cantiere quando ce n'era bisogno, grazie a lei e ai materiali, ricercati, presenti nello show-room siamo riusciti a realizzare la nostra casa nei minimi dettagli proprio come la immaginavamo. Completamente soddisfatti",
    "Showroom grande e variegato, lascia spazio a più soluzioni interessanti. Solo che... stiamo aspettando i preventivi richiesti da più di tre settimane...e, nonostante il sollecito, nessuno si è fatto ancora sentire. Peccato. Atteggiamento superficiale e poco professionale.",
    "Non sono mai stato trattato così male da una azienda in vita mia. Finché stai ordinando sono tutti carini e disponibili, dopo che hai pagato ti sputerebbero in faccia se potessero. Hanno perso i miei pezzi e mi hanno accusato di averli rubati (mi hanno dato del ladro e bugiardo e, dopo che li hanno ritrovati perché li avevano persi loro, neanche le scuse mi hanno fatto), hanno sbagliato le misure (hanno venduto rubinetti e lavandini con misure che non erano compatibili e non solo dicendo che era colpa mia che dovevo controllare, ma volevano farmi anche pagare i pezzi sbagliati perché l'idraulico li aveva montati prima di notare l'errore), non rispondevano al telefono quando c'erano problemi. Pessimo!!",
    "Comes: una volta (trenta e passa anni fa) era un luogo mitico per me in cui trovare il meglio. Oggi mi pare il cimitero degli elefanti... tanta tristezza nel guardare ciò che espongono e vendono. La qualità e la bellezza è altrove.",
    "Ottimo showroom ma peccato per i venditori che anche se siamo stati li per circa 1 ora nessuno ci ha chiesto nulla a differenza del centro di Civitanova Marche che sono stati gentilissimi e disponibili anche se non avevamo Appuntamento",
    "Trovi ampia scelta di materiale e di ottima fattura. I prezzi nella media. Puoi trovare anche il top.",
    "Prima era una sorta di oasi felice che richiamava elementi veramente particolari ed eleganti, ora é molto più scarno e ridotto.",
    "Showroom di vastissima scelta e di qualità a prezzi giusti  peccato che l'accoglienza lascia a desiderare.",
    "Prodotti belli e di qualità. Personale cordiale e competente. Assolutamente da evitare per i tempi di consegna!!!!Tempi lunghi e pezzi dimenticati....",
    "La Comes negozio molto fornito con arredo e accessori bagno ,cucine ,camere un un'arredamento per la casa ,negozio pulito ,personale gentile.",
    "Forniture edili e di arredo bagno tra le più complete per scelta e qualità.",
    "Filiare di Ancona ' magazzino' personale inospitale e scortese. Non mi hanno calcolato di una virgola. Hanno perso un cliente , non lo consiglio a nessuno",
    "Negozio fornito. Ottima location e ritrovo x gente del mestiere",
    "Bellissima esposizione, ben tenuta e con articoli di qualità",
    "Showroom molto bello e fornito. Personale gentile. Prezzi salati.",
    "Qua ho ordinato l intero bagno,accessori compresi,ottima la consulenza.",
    "Sono stata seguita da Laura e mi sono trovata davvero molto bene",
    "Gentilissimi e molto professionali",
    "20 camioncini di artigiani e un solo magazziniere tempi molto lunghi",
    "Gentilezza, cortesia e grande varietà di scelta",
    "Gentilezza e professionalità. Articoli medio alti.",
    "Ottimo prodotti, personale gentile e preparato",
    "Offerta variegata personale gentile e competente",
    "Vasta scelta di materiale. Personale freddo",
    "Qualità e attenzione al cliente",
    "Piccolo negozio di materiale edile",
    "Tante soluzioni per tutti i problemi",
    "Ragazzi cordiali è ben forniti",
    "Gentili ottima scelta",
    "La mia casa, i loro prodotti",
    "Superiore",
]

GOOGLE_MAPS_RATINGS = [
    5, 5, 1, 1, 1, 5, 5, 3, 3, 3, 4, 5, 1, 1, 5, 4, 5, 4, 5, 1,
    4, 4, 5, 4, 1, 4, 3, 5, 5, 5, 5, 5, 5, 5, 5, 4, 4, 3, 4, 5,
    5, 4, 5, 5, 5, 3, 4, 5, 5, 5, 2, 5, 5, 4, 3, 4, 5, 5, 4, 5,
    5, 2, 5, 5, 1, 5, 4, 4, 3, 5, 5, 4, 4, 5, 5, 5, 4, 4, 5, 5, 5,
]


# === FUNZIONI AUSILIARIE ======================================================

def _save_and_show(filename: str) -> None:
    """Salva la figura corrente nella cartella output e la visualizza."""
    plt.savefig(os.path.join(OUTPUT_DIR, filename), bbox_inches="tight")
    plt.show()


def _extract_domain(url) -> str | None:
    """Estrae il dominio da un URL, restituisce None se non valido."""
    if isinstance(url, str):
        return urlparse(url).netloc or None
    return None


def _get_stop_words() -> set:
    """Restituisce l'insieme delle stop-words italiane + parole custom."""
    nltk.download("stopwords", quiet=True)
    sw = set(stopwords.words("italian"))
    sw.update(STOP_WORDS_EXTRA)
    return sw


def _classify_sentiment(score: dict) -> str:
    """Classifica il sentiment in base al compound score VADER."""
    compound = score["compound"]
    if compound > 0.05:
        return "Positivo"
    elif compound < -0.05:
        return "Negativo"
    return "Neutro"


# === 1. EDA CONTATTI HUBSPOT ==================================================

def eda_contatti(df: pd.DataFrame) -> None:
    """Analisi esplorativa dei contatti HubSpot."""
    campi = {
        "Citta": "Città di provenienza",
        "Tipologia Contatto": "Tipologia contatto",
        "Fase del ciclo di vita": "Fase del ciclo di vita",
        "Fonte record": "Fonte record",
    }

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("EDA — Contatti HubSpot", fontsize=16, fontweight="bold")

    for ax, (col, titolo) in zip(axes.flatten(), campi.items()):
        conteggio = df[col].value_counts()
        conteggio.plot(kind="bar", ax=ax, color=COLORS["primary"], edgecolor="white")
        ax.set_title(titolo)
        ax.set_ylabel("Conteggio")
        ax.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    _save_and_show("01_eda_contatti_hubspot.png")


# === 2. ANALISI SORGENTI DI TRAFFICO WEB =====================================

def analisi_traffico(df: pd.DataFrame) -> pd.DataFrame:
    """Estrae i domini dalle colonne URL e produce visualizzazioni."""
    url_cols = {
        "Prima pagina visitata": "Prima Pagina Visitata",
        "Primo sito di riferimento": "Primo Sito di Riferimento",
        "Ultima pagina visualizzata": "Ultima Pagina Visualizzata",
        "Ultimo sito di riferimento": "Ultimo Sito di Riferimento",
    }

    conteggi = {}
    for col_orig, label in url_cols.items():
        domini = df[col_orig].apply(_extract_domain)
        conteggi[label] = domini.value_counts()

    # Grafici a barre (2x2)
    colori_barre = [COLORS["primary"], COLORS["positive"],
                    COLORS["secondary"], COLORS["accent"]]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Analisi Sorgenti di Traffico Web", fontsize=16, fontweight="bold")

    for ax, ((label, serie), colore) in zip(axes.flatten(),
                                            zip(conteggi.items(), colori_barre)):
        serie.plot(kind="bar", ax=ax, color=colore, edgecolor="white")
        ax.set_title(label)
        ax.set_ylabel("Conteggio")
        ax.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    _save_and_show("02_sorgenti_traffico_barre.png")

    # Grafici a torta con raggruppamento soglia
    soglia = 10
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle("Distribuzione Sorgenti (soglia < 10 → Altro)",
                 fontsize=16, fontweight="bold")

    for ax, (label, serie) in zip(axes.flatten(), conteggi.items()):
        principali = serie[serie >= soglia].copy()
        principali["Altro"] = serie[serie < soglia].sum()
        ax.pie(principali, labels=principali.index, autopct="%1.1f%%",
               startangle=140, colors=plt.cm.Paired.colors)
        ax.set_title(label)

    plt.tight_layout()
    _save_and_show("03_sorgenti_traffico_torta.png")

    # Tabella riepilogativa
    riepilogo = pd.DataFrame(conteggi).fillna(0).astype(int)
    riepilogo.to_excel(os.path.join(OUTPUT_DIR, "riepilogo_sorgenti.xlsx"))
    print("\nTabella riepilogativa sorgenti di traffico:")
    print(riepilogo)

    return riepilogo


# === 3. TIPOLOGIE DI INTERVENTO ==============================================

def analisi_interventi(df: pd.DataFrame) -> Counter:
    """Conta le tipologie di intervento (campo multi-valore con separatore ';')."""
    interventi = (
        df["Tipologia intervento"]
        .fillna("")
        .str.split(";")
        .explode()
        .str.strip()
    )
    conteggio = Counter(interventi[interventi != ""])
    print("\nConteggio tipologie di intervento:")
    for tipo, n in conteggio.most_common():
        print(f"  {tipo}: {n}")
    return conteggio


# === 4. SENTIMENT ANALYSIS ===================================================

def sentiment_analysis(commenti: list[str], fonte: str) -> pd.DataFrame:
    """Esegue sentiment analysis VADER su una lista di commenti."""
    nltk.download("vader_lexicon", quiet=True)
    sia = SentimentIntensityAnalyzer()

    risultati = []
    for commento in commenti:
        score = sia.polarity_scores(commento)
        risultati.append({
            "Commento": commento,
            "Sentiment": _classify_sentiment(score),
            "Compound": score["compound"],
        })

    df_sent = pd.DataFrame(risultati)
    conteggio = df_sent["Sentiment"].value_counts()

    print(f"\n--- Sentiment Analysis: {fonte} ---")
    print(f"  Positivo: {conteggio.get('Positivo', 0)}")
    print(f"  Negativo: {conteggio.get('Negativo', 0)}")
    print(f"  Neutro:   {conteggio.get('Neutro', 0)}")

    # Grafico distribuzione sentiment
    color_map = {
        "Positivo": COLORS["positive"],
        "Negativo": COLORS["negative"],
        "Neutro": COLORS["neutral"],
    }
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f"Sentiment Analysis — {fonte}", fontsize=14, fontweight="bold")

    conteggio.plot(
        kind="bar", ax=axes[0],
        color=[color_map.get(s, COLORS["primary"]) for s in conteggio.index],
        edgecolor="white",
    )
    axes[0].set_title("Distribuzione sentiment")
    axes[0].set_ylabel("N. recensioni")
    axes[0].tick_params(axis="x", rotation=0)

    axes[1].hist(df_sent["Compound"], bins=10, color=COLORS["primary"],
                 edgecolor="white", alpha=0.85)
    axes[1].axvline(0, color=COLORS["negative"], linestyle="--", linewidth=1)
    axes[1].set_title("Distribuzione compound score")
    axes[1].set_xlabel("Compound score")
    axes[1].set_ylabel("Frequenza")

    plt.tight_layout()
    filename = f"04_sentiment_{fonte.lower().replace(' ', '_')}.png"
    _save_and_show(filename)

    return df_sent


# === 5. TEXT MINING (WORD CLOUD + FREQUENZE) ==================================

def text_mining(recensioni: list[str]) -> dict:
    """Genera word cloud e grafico delle parole più frequenti."""
    sw = _get_stop_words()
    testo = " ".join(recensioni)

    # Word cloud
    wc = WordCloud(
        stopwords=sw, background_color="white",
        width=800, height=400, colormap="viridis",
    ).generate(testo)

    plt.figure(figsize=FIGSIZE)
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.title("Word Cloud — Recensioni aggregate", fontsize=14, fontweight="bold")
    _save_and_show("05_wordcloud.png")

    # Frequenza parole
    testo_pulito = re.sub(r"[^\w\s]", "", testo).lower()
    parole = [p for p in testo_pulito.split() if p not in sw]
    conteggio = Counter(parole)

    min_occorrenze = 3
    frequenti = {k: v for k, v in conteggio.items() if v > min_occorrenze}
    frequenti = dict(sorted(frequenti.items(), key=lambda x: x[1], reverse=True))

    plt.figure(figsize=FIGSIZE)
    plt.bar(frequenti.keys(), frequenti.values(), color=COLORS["primary"],
            edgecolor="white")
    plt.title(f"Parole più frequenti (>{min_occorrenze} occorrenze)",
              fontsize=14, fontweight="bold")
    plt.xlabel("Parola")
    plt.ylabel("Conteggio")
    plt.xticks(rotation=90)
    plt.tight_layout()
    _save_and_show("06_frequenza_parole.png")

    return frequenti


# === 6. ANALISI VOTI GOOGLE MAPS ==============================================

def analisi_voti(voti: list[int]) -> None:
    """Statistiche descrittive e distribuzione dei voti Google Maps."""
    voti_s = pd.Series(voti)
    print("\n--- Voti Google Maps ---")
    print(f"  Media:   {voti_s.mean():.2f}")
    print(f"  Mediana: {voti_s.median():.1f}")
    print(f"  Moda:    {voti_s.mode().iloc[0]}")

    plt.figure(figsize=(8, 5))
    voti_s.value_counts().sort_index().plot(
        kind="bar", color=COLORS["accent"], edgecolor="white"
    )
    plt.title("Distribuzione Voti — Google Maps", fontsize=14, fontweight="bold")
    plt.xlabel("Voto")
    plt.ylabel("Frequenza")
    plt.xticks(rotation=0)
    plt.tight_layout()
    _save_and_show("07_distribuzione_voti.png")


# === 7. ANALISI CAMPAGNE META ================================================

def analisi_meta(filepath: str) -> pd.DataFrame:
    """Analizza le campagne pubblicitarie Meta (Facebook / Instagram)."""
    meta_df = pd.read_excel(filepath, sheet_name="Foglio1")

    meta_df["Social"] = (
        meta_df["Campaign name"]
        .str.extract(r"\b(IG|FB)\b", expand=False)
        .fillna("Altro")
    )

    meta_df["Starts"] = pd.to_datetime(meta_df["Starts"])
    meta_df["Ends"] = pd.to_datetime(meta_df["Ends"], errors="coerce")
    meta_df["Reporting ends"] = pd.to_datetime(meta_df["Reporting ends"])
    meta_df["Ends"] = meta_df["Ends"].fillna(meta_df["Reporting ends"])
    meta_df["Durata"] = (meta_df["Ends"] - meta_df["Starts"]).dt.days

    # CTR ponderato per durata della campagna
    def ctr_ponderato(g):
        return np.average(
            g["CTR (link click-through rate)"], weights=g["Durata"]
        )

    ctr_per_social = meta_df.groupby("Social").apply(ctr_ponderato)
    print("\n--- CTR medio ponderato per piattaforma ---")
    for social, ctr in ctr_per_social.items():
        print(f"  {social}: {ctr:.4f}")

    # Metriche aggregate per piattaforma
    metriche = meta_df.groupby("Social")[
        ["Impressions", "Reach", "Frequency", "Link clicks"]
    ].sum()
    print("\nMetriche aggregate per piattaforma:")
    print(metriche)

    # Visualizzazione
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Performance Campagne Meta", fontsize=14, fontweight="bold")

    ctr_per_social.plot(
        kind="bar", ax=axes[0], color=COLORS["secondary"], edgecolor="white"
    )
    axes[0].set_title("CTR medio ponderato")
    axes[0].set_ylabel("CTR")
    axes[0].tick_params(axis="x", rotation=0)

    metriche[["Impressions", "Reach"]].plot(
        kind="bar", ax=axes[1], edgecolor="white",
        color=[COLORS["primary"], COLORS["accent"]],
    )
    axes[1].set_title("Impressions vs Reach")
    axes[1].set_ylabel("Conteggio")
    axes[1].tick_params(axis="x", rotation=0)

    plt.tight_layout()
    _save_and_show("08_campagne_meta.png")

    return meta_df


# === MAIN =====================================================================

def main():
    print("=" * 60)
    print("  ANALISI STRATEGIA MARKETING — NUOVA COMES")
    print("=" * 60)

    # 1. Caricamento dati HubSpot
    df = pd.read_excel(HUBSPOT_FILE)
    print(f"\nDataset HubSpot caricato: {df.shape[0]} righe, {df.shape[1]} colonne")

    # 2. EDA contatti
    eda_contatti(df)

    # 3. Analisi sorgenti di traffico
    analisi_traffico(df)

    # 4. Tipologie di intervento
    analisi_interventi(df)

    # 5. Sentiment analysis
    df_fb = sentiment_analysis(FACEBOOK_COMMENTS, "Facebook")
    df_maps = sentiment_analysis(GOOGLE_MAPS_REVIEWS, "Google Maps")

    # 6. Text mining su tutte le recensioni
    tutte_le_recensioni = FACEBOOK_COMMENTS + GOOGLE_MAPS_REVIEWS
    text_mining(tutte_le_recensioni)

    # 7. Voti Google Maps
    analisi_voti(GOOGLE_MAPS_RATINGS)

    # 8. Campagne Meta
    analisi_meta(META_FILE)

    print("\n" + "=" * 60)
    print(f"  Analisi completata. Output salvati in: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
