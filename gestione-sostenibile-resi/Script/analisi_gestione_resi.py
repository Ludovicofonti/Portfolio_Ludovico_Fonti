"""
Gestione Sostenibile dei Resi — Stella McCartney
=================================================
Analisi delle emissioni di CO₂ generate dalla logistica inversa nel fashion.

Obiettivi:
- Stimare le emissioni di CO₂ associate ai resi
- Identificare i driver principali (distanza, peso, paese)
- Costruire un modello di regressione per la previsione delle emissioni
- Proporre strategie di riduzione dell'impatto ambientale

Dataset: dati_resi_distanze.csv (7990 resi con emissioni calcolate via EcoTransit)
"""

import os
import pickle
import time
import warnings

import folium
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from geopy.geocoders import Nominatim
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["figure.dpi"] = 120

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# 1. CARICAMENTO E PULIZIA DATI
# ============================================================================

def load_data(filepath: str) -> pd.DataFrame:
    """Carica il dataset e normalizza i tipi di dato."""
    df = pd.read_csv(filepath, sep=";")

    # Conversione colonne numeriche (formato europeo con virgola)
    numeric_cols = ["weight", "emission", "price", "distance"]
    for col in numeric_cols:
        df[col] = df[col].astype(str).str.replace(",", ".").pipe(pd.to_numeric, errors="coerce")

    # Conversione data
    df["creation_date"] = pd.to_datetime(df["creation_date"], errors="coerce")

    # Rimozione colonne inutili
    df = df.drop(columns=["...11"], errors="ignore")

    # Rimozione righe con valori critici mancanti
    df = df.dropna(subset=["emission", "distance", "weight"])

    # Conversione refund in EUR
    df["exchange_rate"] = pd.to_numeric(df["exchange_rate"], errors="coerce")
    df["total_refund"] = pd.to_numeric(df["total_refund"], errors="coerce")
    df["refund_eur"] = (df["total_refund"] * df["exchange_rate"]).round(2)

    # Estrazione anno e mese
    df["anno"] = df["creation_date"].dt.year
    df["mese"] = df["creation_date"].dt.month

    return df


def print_summary(df: pd.DataFrame) -> None:
    """Stampa un riepilogo del dataset."""
    print("=" * 60)
    print("RIEPILOGO DATASET")
    print("=" * 60)
    print(f"Righe: {len(df):,}")
    print(f"Paesi: {df['country_code'].nunique()}")
    print(f"Città: {df['city'].nunique()}")
    print(f"Resi unici: {df['return_case_id'].nunique()}")
    print(f"Periodo: {df['creation_date'].min():%Y-%m-%d} → {df['creation_date'].max():%Y-%m-%d}")
    print(f"\nEmissioni CO₂ (kg): media={df['emission'].mean():.2f}, "
          f"mediana={df['emission'].median():.2f}, max={df['emission'].max():.2f}")
    print(f"Distanza (km):      media={df['distance'].mean():.0f}, "
          f"mediana={df['distance'].median():.0f}, max={df['distance'].max():.0f}")
    print(f"Peso (kg):          media={df['weight'].mean():.2f}")
    print()


# ============================================================================
# 2. ANALISI ESPLORATIVA (EDA)
# ============================================================================

def plot_items_per_return(df: pd.DataFrame) -> None:
    """Distribuzione del numero di item per reso."""
    items_per_return = df.groupby("return_case_id").size().reset_index(name="n_items")
    dist = items_per_return["n_items"].value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    dist.plot(kind="bar", color="#4C72B0", edgecolor="black", ax=ax)
    ax.set_title("Distribuzione del numero di prodotti per reso")
    ax.set_xlabel("Numero di item per reso")
    ax.set_ylabel("Numero di resi")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    media = items_per_return["n_items"].mean()
    ax.axvline(x=media - 1, color="red", linestyle="--", alpha=0.8, label=f"Media: {media:.1f}")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_items_per_reso.png"), bbox_inches="tight")
    plt.show()

    print(f"Media item per reso: {media:.2f}")
    print(f"Distribuzione:\n{dist}\n")


def plot_emissions_by_country(df: pd.DataFrame) -> None:
    """Emissioni medie e totali per paese."""
    country_stats = (
        df.groupby("country_code")["emission"]
        .agg(["mean", "sum", "count"])
        .rename(columns={"mean": "media_emissione", "sum": "totale_emissione", "count": "n_resi"})
        .sort_values("totale_emissione", ascending=False)
    )

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Top 15 paesi per emissioni totali
    top15 = country_stats.head(15)
    axes[0].barh(top15.index[::-1], top15["totale_emissione"][::-1], color="#E07B54")
    axes[0].set_title("Top 15 paesi — Emissioni totali CO₂ (kg)")
    axes[0].set_xlabel("Emissioni totali (kg CO₂)")

    # Top 15 paesi per emissione media
    top15_avg = country_stats.sort_values("media_emissione", ascending=False).head(15)
    axes[1].barh(top15_avg.index[::-1], top15_avg["media_emissione"][::-1], color="#5B8DBE")
    axes[1].set_title("Top 15 paesi — Emissione media per reso (kg CO₂)")
    axes[1].set_xlabel("Emissione media (kg CO₂)")

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_emissioni_per_paese.png"), bbox_inches="tight")
    plt.show()


def plot_emission_distribution(df: pd.DataFrame) -> None:
    """Distribuzione delle emissioni e della distanza."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].hist(df["emission"], bins=50, color="#4C72B0", edgecolor="black", alpha=0.8)
    axes[0].set_title("Distribuzione emissioni CO₂ per reso")
    axes[0].set_xlabel("Emissioni (kg CO₂)")
    axes[0].set_ylabel("Frequenza")
    axes[0].axvline(df["emission"].mean(), color="red", linestyle="--", label=f"Media: {df['emission'].mean():.2f}")
    axes[0].legend()

    axes[1].hist(df["distance"], bins=50, color="#55A868", edgecolor="black", alpha=0.8)
    axes[1].set_title("Distribuzione distanze dal centro logistico")
    axes[1].set_xlabel("Distanza (km)")
    axes[1].set_ylabel("Frequenza")
    axes[1].axvline(df["distance"].mean(), color="red", linestyle="--", label=f"Media: {df['distance'].mean():.0f} km")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_distribuzioni.png"), bbox_inches="tight")
    plt.show()


def plot_correlation_matrix(df: pd.DataFrame) -> None:
    """Matrice di correlazione delle variabili numeriche."""
    numeric_df = df[["emission", "distance", "weight", "quantity", "refund_eur"]].dropna()
    corr = numeric_df.corr()

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                square=True, linewidths=0.5, ax=ax)
    ax.set_title("Matrice di correlazione")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_correlazione.png"), bbox_inches="tight")
    plt.show()


def plot_temporal_trend(df: pd.DataFrame) -> None:
    """Andamento temporale delle emissioni."""
    monthly = (
        df.set_index("creation_date")
        .resample("ME")["emission"]
        .agg(["sum", "mean", "count"])
    )

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.bar(monthly.index, monthly["count"], width=25, alpha=0.3, color="#4C72B0", label="N. resi")
    ax1.set_ylabel("Numero di resi", color="#4C72B0")
    ax1.tick_params(axis="y", labelcolor="#4C72B0")

    ax2 = ax1.twinx()
    ax2.plot(monthly.index, monthly["sum"], color="#E07B54", linewidth=2, marker="o",
             markersize=4, label="Emissioni totali")
    ax2.set_ylabel("Emissioni totali (kg CO₂)", color="#E07B54")
    ax2.tick_params(axis="y", labelcolor="#E07B54")

    ax1.set_title("Andamento mensile: resi ed emissioni CO₂")
    fig.legend(loc="upper left", bbox_to_anchor=(0.12, 0.88))
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_trend_temporale.png"), bbox_inches="tight")
    plt.show()


# ============================================================================
# 3. MODELLO DI REGRESSIONE
# ============================================================================

def build_regression_model(df: pd.DataFrame) -> None:
    """Regressione lineare multipla: emission ~ distance + weight."""
    features = ["distance", "weight"]
    target = "emission"

    model_df = df[features + [target]].dropna()

    X = model_df[features]
    y = model_df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # Metriche
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print("=" * 60)
    print("MODELLO DI REGRESSIONE LINEARE MULTIPLA")
    print("=" * 60)
    print(f"Target:     {target}")
    print(f"Features:   {features}")
    print(f"Train size: {len(X_train):,} | Test size: {len(X_test):,}")
    print(f"\nCoefficienti:")
    for feat, coef in zip(features, model.coef_):
        print(f"  {feat:>10}: {coef:+.4f}")
    print(f"  {'intercept':>10}: {model.intercept_:+.4f}")
    print(f"\nMetriche (test set):")
    print(f"  R²:   {r2:.4f}")
    print(f"  MAE:  {mae:.4f} kg CO₂")
    print(f"  RMSE: {rmse:.4f} kg CO₂")
    print()

    # Grafico predizioni vs valori reali
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].scatter(y_test, y_pred, alpha=0.3, s=10, color="#4C72B0")
    lims = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
    axes[0].plot(lims, lims, "r--", linewidth=1.5, label="Predizione perfetta")
    axes[0].set_xlabel("Emissioni reali (kg CO₂)")
    axes[0].set_ylabel("Emissioni predette (kg CO₂)")
    axes[0].set_title(f"Predizioni vs Reali (R² = {r2:.3f})")
    axes[0].legend()

    residuals = y_test - y_pred
    axes[1].hist(residuals, bins=50, color="#55A868", edgecolor="black", alpha=0.8)
    axes[1].set_xlabel("Residui (kg CO₂)")
    axes[1].set_ylabel("Frequenza")
    axes[1].set_title("Distribuzione dei residui")
    axes[1].axvline(0, color="red", linestyle="--", linewidth=1.5)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_regressione.png"), bbox_inches="tight")
    plt.show()


# ============================================================================
# 4. MAPPA INTERATTIVA DELLE EMISSIONI
# ============================================================================

def create_emission_map(df: pd.DataFrame) -> None:
    """Genera una mappa interattiva delle emissioni per città."""
    coords_cache = os.path.join(OUTPUT_DIR, "city_coords.pkl")

    # Carica cache coordinate se disponibile
    if os.path.exists(coords_cache):
        with open(coords_cache, "rb") as f:
            city_coords = pickle.load(f)
        print(f"Cache coordinate caricata ({len(city_coords)} città)")
    else:
        city_coords = {}

    # Geocodifica le città mancanti
    cities = df["city"].dropna().unique()
    missing = [c for c in cities if c not in city_coords]

    if missing:
        print(f"Geocodifica di {len(missing)} città mancanti...")
        geolocator = Nominatim(user_agent="portfolio_emissioni_resi")
        for city in missing:
            try:
                location = geolocator.geocode(city)
                city_coords[city] = (location.latitude, location.longitude) if location else None
            except Exception:
                city_coords[city] = None
            time.sleep(1)

        with open(coords_cache, "wb") as f:
            pickle.dump(city_coords, f)
        print("Cache coordinate aggiornata.")

    # Aggiungi coordinate al DataFrame
    def _get_coord(city, idx):
        coords = city_coords.get(city)
        return coords[idx] if coords else None

    df_map = df.copy()
    df_map["latitude"] = df_map["city"].map(lambda x: _get_coord(x, 0))
    df_map["longitude"] = df_map["city"].map(lambda x: _get_coord(x, 1))
    df_map = df_map.dropna(subset=["latitude", "longitude"])

    # Aggregazione per città
    city_agg = (
        df_map.groupby(["city", "latitude", "longitude"])
        .agg(emissione_totale=("emission", "sum"), n_resi=("emission", "count"),
             emissione_media=("emission", "mean"))
        .reset_index()
    )

    # Creazione mappa
    mappa = folium.Map(location=[45.0, 10.0], zoom_start=3, tiles="CartoDB positron")

    max_emission = city_agg["emissione_totale"].max()

    for _, row in city_agg.iterrows():
        radius = max(3, min(row["emissione_totale"] / max_emission * 30, 25))
        folium.CircleMarker(
            location=(row["latitude"], row["longitude"]),
            radius=radius,
            popup=(f"<b>{row['city']}</b><br>"
                   f"Resi: {row['n_resi']}<br>"
                   f"Emissioni totali: {row['emissione_totale']:.1f} kg CO₂<br>"
                   f"Media per reso: {row['emissione_media']:.2f} kg CO₂"),
            color="#E07B54",
            fill=True,
            fill_color="#E07B54",
            fill_opacity=0.5,
        ).add_to(mappa)

    output_path = os.path.join(OUTPUT_DIR, "mappa_emissioni.html")
    mappa.save(output_path)
    print(f"Mappa salvata: {output_path}")


# ============================================================================
# 5. SCENARI DI RIDUZIONE
# ============================================================================

def analyze_reduction_scenarios(df: pd.DataFrame) -> None:
    """Confronto scenari di riduzione emissioni."""
    total_emission = df["emission"].sum()
    total_returns = df["return_case_id"].nunique()

    print("=" * 60)
    print("SCENARI DI RIDUZIONE EMISSIONI")
    print("=" * 60)
    print(f"Emissioni attuali totali: {total_emission:,.1f} kg CO₂")
    print(f"Resi totali: {total_returns:,}\n")

    # Scenario 1: Riduzione resi del 10% (eliminando i più distanti)
    df_sorted = df.sort_values("distance", ascending=False)
    n_remove = int(len(df_sorted) * 0.10)
    reduced = df_sorted.iloc[n_remove:]
    saving_1 = total_emission - reduced["emission"].sum()
    print(f"Scenario 1 — Riduzione 10% resi (più distanti):")
    print(f"  Risparmio: {saving_1:,.1f} kg CO₂ ({saving_1 / total_emission:.1%})\n")

    # Scenario 2: Centro resi locale in Europa (distanza dimezzata per EU)
    eu_countries = ["IT", "FR", "DE", "ES", "GB", "NL", "BE", "AT", "CH", "PT", "SE", "DK", "NO", "FI", "IE", "PL"]
    df_scenario2 = df.copy()
    eu_mask = df_scenario2["country_code"].isin(eu_countries)
    df_scenario2.loc[eu_mask, "emission"] = df_scenario2.loc[eu_mask, "emission"] * 0.5
    saving_2 = total_emission - df_scenario2["emission"].sum()
    print(f"Scenario 2 — Centro resi locale EU (emissioni dimezzate):")
    print(f"  Risparmio: {saving_2:,.1f} kg CO₂ ({saving_2 / total_emission:.1%})\n")

    # Scenario 3: Consolidamento spedizioni (resi multipli stessa città raggruppati)
    city_counts = df.groupby("city")["city"].transform("count")
    df_scenario3 = df.copy()
    df_scenario3.loc[city_counts > 1, "emission"] = df_scenario3.loc[city_counts > 1, "emission"] * 0.7
    saving_3 = total_emission - df_scenario3["emission"].sum()
    print(f"Scenario 3 — Consolidamento spedizioni (stessa città):")
    print(f"  Risparmio: {saving_3:,.1f} kg CO₂ ({saving_3 / total_emission:.1%})\n")

    # Grafico riepilogativo
    scenarios = ["Attuale", "Riduz. resi\n(-10% distanti)", "Centro EU\nlocale", "Consolidamento\nspedizioni"]
    values = [total_emission,
              total_emission - saving_1,
              total_emission - saving_2,
              total_emission - saving_3]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#C44E52", "#55A868", "#4C72B0", "#8172B2"]
    bars = ax.bar(scenarios, values, color=colors, edgecolor="black", alpha=0.85)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + total_emission * 0.01,
                f"{val:,.0f}", ha="center", va="bottom", fontweight="bold", fontsize=10)

    ax.set_ylabel("Emissioni totali (kg CO₂)")
    ax.set_title("Confronto scenari di riduzione emissioni CO₂")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_scenari_riduzione.png"), bbox_inches="tight")
    plt.show()


# ============================================================================
# MAIN
# ============================================================================

def main():
    filepath = os.path.join(SCRIPT_DIR, "dati_resi_distanze.csv")

    # 1. Caricamento dati
    print("Caricamento dati...\n")
    df = load_data(filepath)
    print_summary(df)

    # 2. Analisi esplorativa
    print("— Analisi esplorativa —\n")
    plot_items_per_return(df)
    plot_emissions_by_country(df)
    plot_emission_distribution(df)
    plot_correlation_matrix(df)
    plot_temporal_trend(df)

    # 3. Modello di regressione
    build_regression_model(df)

    # 4. Scenari di riduzione
    analyze_reduction_scenarios(df)

    # 5. Mappa interattiva
    print("Generazione mappa interattiva...")
    create_emission_map(df)

    print("\n✓ Analisi completata. Output salvati nella directory corrente.")


if __name__ == "__main__":
    main()
