# ==============================================================================
# PREVISIONE VENDITE AUTO USA CON VARIABILI MACROECONOMICHE
# ==============================================================================
#
# Serie storica: Gennaio 1992 - Dicembre 2024 (mensile)
# Obiettivo:     Previsione Q1 2025 (Gen-Feb-Mar)
#
# Approccio:
#   Fase 1 - Modello Univariato (ARIMA) sulla serie log-trasformata
#   Fase 2 - Modello Multivariato (ARIMAX) con variabili esogene:
#            prezzo del petrolio, tasso di disoccupazione, tasso d'interesse
#
# Pipeline:
#   EDA -> Stazionarieta' -> ARIMA -> Granger -> ARIMAX -> Shock -> Forecast
#
# ==============================================================================


# --- 0. SETUP ----------------------------------------------------------------

rm(list = ls())

library(readxl)
library(forecast)
library(tseries)
library(urca)
library(lmtest)
library(ggplot2)
library(zoo)
library(dplyr)
library(tictoc)

if (requireNamespace("rstudioapi", quietly = TRUE) && rstudioapi::isAvailable()) {
  setwd(dirname(rstudioapi::getActiveDocumentContext()$path))
}


# --- 1. CARICAMENTO E PREPARAZIONE DATI --------------------------------------

# Dataset con vendite auto USA e variabili macroeconomiche
# Colonne: Date | Value | petrol_price | unemp_rate | interest
df <- read_excel("dati_vendite_auto.xlsx")

# Conversione date (formato "Jan-1992")
old_locale <- Sys.getlocale("LC_TIME")
Sys.setlocale("LC_TIME", "C")
df$Date <- as.yearmon(df$Date, format = "%b-%Y")
df <- df[order(df$Date), ]
Sys.setlocale("LC_TIME", old_locale)

df <- df %>% mutate(across(-Date, as.numeric))

# Separazione dati osservati / periodo di previsione (righe con Value = NA)
df_future <- df[is.na(df$Value), ]
df        <- df[!is.na(df$Value), ]

cat("Periodo:", format(min(df$Date)), "-", format(max(df$Date)), "\n")
cat("Osservazioni:", nrow(df), "\n\n")


# --- 2. ANALISI ESPLORATIVA (EDA) --------------------------------------------

ts_value <- ts(df$Value, start = c(1992, 1), frequency = 12)

# 2a. Serie storica originale
autoplot(ts_value) +
  labs(title = "Vendite Mensili Auto USA (1992-2024)",
       subtitle = "Crescita costante, crisi 2008, shock COVID-19, ripresa post-2021",
       x = "Anno", y = "Vendite (milioni USD)") +
  theme_minimal(base_size = 13)

# 2b. Scomposizione STL (Seasonal-Trend-Loess)
decomp <- stl(ts_value, s.window = "periodic")

autoplot(decomp) +
  labs(title = "Scomposizione STL - Vendite Auto USA",
       x = "Anno", y = "Valori") +
  theme_minimal(base_size = 12) +
  theme(strip.text = element_text(face = "bold"))

# 2c. Varianza spiegata per componente
stagionale <- decomp$time.series[, "seasonal"]
trend_comp <- decomp$time.series[, "trend"]
residuo    <- decomp$time.series[, "remainder"]
var_totale <- var(stagionale) + var(trend_comp) + var(residuo)

varianza_df <- data.frame(
  Componente  = c("Stagionalita", "Trend", "Residuo"),
  Percentuale = round(100 * c(var(stagionale), var(trend_comp), var(residuo)) / var_totale, 2)
)
cat("Varianza spiegata per componente:\n")
print(varianza_df, row.names = FALSE)


# --- 3. TEST DI STAZIONARIETA' -----------------------------------------------

cat("\n--- Serie originale ---\n")
cat("ADF test p-value:", adf.test(ts_value)$p.value, "(non stazionaria)\n")
cat("KPSS test:\n")
print(summary(ur.kpss(ts_value)))

ts_diff <- diff(ts_value)
cat("\n--- Serie differenziata ---\n")
cat("ADF test p-value:", adf.test(ts_diff)$p.value, "(stazionaria)\n\n")


# ==============================================================================
# FASE 1: MODELLO UNIVARIATO — ARIMA
# ==============================================================================

cat(strrep("=", 60), "\n")
cat("FASE 1: MODELLO UNIVARIATO (ARIMA)\n")
cat(strrep("=", 60), "\n\n")

# Train/test split (test = dicembre 2024)
train_ts <- window(ts_value, end = c(2024, 11))
test_ts  <- window(ts_value, start = c(2024, 12))

# Stima ARIMA con ricerca esaustiva
mod_arima <- auto.arima(train_ts,
                        seasonal      = TRUE,
                        stepwise      = FALSE,
                        approximation = FALSE)

cat("Modello selezionato:\n")
summary(mod_arima)

# Diagnostica residui
checkresiduals(mod_arima)

ljung_univ <- Box.test(residuals(mod_arima), lag = 12, type = "Ljung-Box")
cat("\nLjung-Box (lag=12): p-value =", round(ljung_univ$p.value, 4),
    ifelse(ljung_univ$p.value > 0.05,
           "-> Residui non autocorrelati\n",
           "-> Autocorrelazione presente\n"))

# Wald test (significativita' coefficienti)
cat("\nWald Test:\n")
print(coeftest(mod_arima))

# Previsione univariata Q1 2025
forecast_univ <- forecast(mod_arima, h = 4)

autoplot(forecast_univ) +
  labs(title = "Previsione ARIMA Univariato - Vendite Auto USA",
       x = "Anno", y = "Vendite (milioni USD)") +
  theme_minimal(base_size = 13)

cat("\nAccuracy sul training set:\n")
print(accuracy(mod_arima))


# ==============================================================================
# SELEZIONE VARIABILI ESOGENE — TEST DI GRANGER
# ==============================================================================

cat("\n", strrep("=", 60), "\n")
cat("TEST DI CAUSALITA' DI GRANGER\n")
cat(strrep("=", 60), "\n\n")

# Serie differenziate (requisito: stazionarieta')
ts_val_d <- diff(ts(df$Value, frequency = 12))
ts_pet_d <- diff(ts(df$petrol_price, frequency = 12))
ts_une_d <- diff(ts(df$unemp_rate, frequency = 12))
ts_int_d <- diff(ts(df$interest, frequency = 12))

n <- min(length(ts_val_d), length(ts_pet_d), length(ts_une_d), length(ts_int_d))
ts_val_d <- ts_val_d[1:n]
ts_pet_d <- ts_pet_d[1:n]
ts_une_d <- ts_une_d[1:n]
ts_int_d <- ts_int_d[1:n]

granger_pet <- grangertest(ts(ts_val_d) ~ ts(ts_pet_d), order = 7)
granger_une <- grangertest(ts(ts_val_d) ~ ts(ts_une_d), order = 7)
granger_int <- grangertest(ts(ts_val_d) ~ ts(ts_int_d), order = 7)

granger_summary <- data.frame(
  Variabile = c("Prezzo petrolio", "Tasso disoccupazione", "Tasso d'interesse"),
  p_value   = round(c(granger_pet$`Pr(>F)`[2],
                       granger_une$`Pr(>F)`[2],
                       granger_int$`Pr(>F)`[2]), 4),
  Significativa = c(
    ifelse(granger_pet$`Pr(>F)`[2] < 0.05, "Si", "No"),
    ifelse(granger_une$`Pr(>F)`[2] < 0.05, "Si", "No"),
    ifelse(granger_int$`Pr(>F)`[2] < 0.10, "Si (10%)", "No"))
)

cat("Riepilogo test di Granger (H0: la variabile NON causa Vendite):\n")
print(granger_summary, row.names = FALSE)


# ==============================================================================
# FASE 2: MODELLO MULTIVARIATO — ARIMAX
# ==============================================================================

cat("\n", strrep("=", 60), "\n")
cat("FASE 2: MODELLO MULTIVARIATO (ARIMAX)\n")
cat(strrep("=", 60), "\n\n")

# Trasformazione logaritmica per stabilizzare la varianza
df_log <- data.frame(
  Date         = df$Date,
  log_value    = log(df$Value),
  log_petrol   = log(df$petrol_price),
  log_unemp    = log(df$unemp_rate),
  log_interest = log(df$interest)
)

# Rimozione valori non finiti (log(0) = -Inf)
df_log <- df_log[complete.cases(df_log) &
                   apply(df_log[, -1], 1, function(x) all(is.finite(x))), ]

ts_log <- ts(df_log$log_value, start = c(1992, 1), frequency = 12)
xreg   <- as.matrix(df_log[, c("log_petrol", "log_unemp", "log_interest")])

# Grid search: minimizzazione RMSE su (p,d,q)(P,D,Q)[12]
cat("Grid search ARIMAX in corso...\n")

best_rmse  <- Inf
best_model <- NULL
best_order <- NULL

tic("Grid search ARIMAX")

for (p in 0:3) {
  for (q in 0:3) {
    for (P in 0:1) {
      for (Q in 0:1) {
        tryCatch({
          mod <- Arima(ts_log,
                       order    = c(p, 1, q),
                       seasonal = list(order = c(P, 1, Q), period = 12),
                       xreg     = xreg)
          rmse <- accuracy(mod)[, "RMSE"]
          if (!is.na(rmse) && rmse < best_rmse) {
            best_rmse  <- rmse
            best_model <- mod
            best_order <- list(order = c(p, 1, q), seasonal = c(P, 1, Q))
          }
        }, error = function(e) NULL)
      }
    }
  }
}

toc()

cat("\nModello ottimale: ARIMAX(",
    paste(best_order$order, collapse = ","), ")(",
    paste(best_order$seasonal, collapse = ","), ")[12]\n")
cat("RMSE:", round(best_rmse, 6), "\n\n")

# Modello finale
mod_arimax <- best_model
summary(mod_arimax)

# Diagnostica
checkresiduals(mod_arimax)

ljung_multi <- Box.test(residuals(mod_arimax), lag = 12, type = "Ljung-Box")
cat("\nLjung-Box (lag=12): p-value =", round(ljung_multi$p.value, 4),
    ifelse(ljung_multi$p.value > 0.05,
           "-> Residui non autocorrelati\n",
           "-> Autocorrelazione presente\n"))

shapiro_test <- shapiro.test(residuals(mod_arimax))
cat("Shapiro-Wilk (normalita'): p-value =", round(shapiro_test$p.value, 4), "\n")


# ==============================================================================
# ANALISI DEGLI SHOCK STORICI
# ==============================================================================

cat("\n", strrep("=", 60), "\n")
cat("ANALISI DEGLI SHOCK STORICI\n")
cat(strrep("=", 60), "\n\n")

# Variabili dummy per periodi di shock
df_log$dummy_dotcom  <- ifelse(df_log$Date >= as.yearmon("2001-06") &
                                 df_log$Date <= as.yearmon("2002-12"), 1, 0)
df_log$dummy_crisi08 <- ifelse(df_log$Date >= as.yearmon("2008-06") &
                                 df_log$Date <= as.yearmon("2009-12"), 1, 0)
df_log$dummy_covid   <- ifelse(df_log$Date >= as.yearmon("2020-02") &
                                 df_log$Date <= as.yearmon("2020-07"), 1, 0)
df_log$dummy_inflaz  <- ifelse(df_log$Date >= as.yearmon("2022-01") &
                                 df_log$Date <= as.yearmon("2023-01"), 1, 0)

xreg_shock <- as.matrix(df_log[, c("log_petrol", "log_unemp", "log_interest",
                                    "dummy_dotcom", "dummy_crisi08",
                                    "dummy_covid", "dummy_inflaz")])

mod_shock <- Arima(ts_log,
                   order    = best_order$order,
                   seasonal = list(order = best_order$seasonal, period = 12),
                   xreg     = xreg_shock)

shock_coefs <- coef(mod_shock)[c("dummy_dotcom", "dummy_crisi08",
                                  "dummy_covid", "dummy_inflaz")]

shock_df <- data.frame(
  Periodo   = c("Dot-com + 9/11 (giu 2001 - dic 2002)",
                "Crisi finanziaria (giu 2008 - dic 2009)",
                "COVID-19 (feb 2020 - lug 2020)",
                "Inflazione e tassi (gen 2022 - gen 2023)"),
  Impatto   = round(as.numeric(shock_coefs), 4),
  Direzione = ifelse(shock_coefs > 0, "Positivo", "Negativo")
)

cat("Impatto stimato degli shock storici (scala log):\n")
print(shock_df, row.names = FALSE)


# ==============================================================================
# PREVISIONE Q1 2025
# ==============================================================================

cat("\n", strrep("=", 60), "\n")
cat("PREVISIONE Q1 2025\n")
cat(strrep("=", 60), "\n\n")

# Scenario base: valori attesi delle variabili esogene
future_xreg <- matrix(
  c(log(73.82), log(4.0), log(4.33),    # Gennaio 2025
    log(78.16), log(4.1), log(4.33),    # Febbraio 2025
    log(67.82), log(4.2), log(4.33)),   # Marzo 2025
  ncol = 3, byrow = TRUE,
  dimnames = list(NULL, c("log_petrol", "log_unemp", "log_interest"))
)

forecast_arimax <- forecast(mod_arimax, xreg = future_xreg, h = 3)

# Ritorno alla scala originale
pred_orig  <- exp(forecast_arimax$mean)
lower_orig <- exp(forecast_arimax$lower)
upper_orig <- exp(forecast_arimax$upper)

risultati <- data.frame(
  Mese        = c("Gennaio 2025", "Febbraio 2025", "Marzo 2025"),
  Stima       = round(as.numeric(pred_orig), 2),
  IC_80_lower = round(lower_orig[, 1], 2),
  IC_80_upper = round(upper_orig[, 1], 2),
  IC_95_lower = round(lower_orig[, 2], 2),
  IC_95_upper = round(upper_orig[, 2], 2)
)

cat("Previsioni ARIMAX (scala originale, milioni USD):\n")
print(risultati, row.names = FALSE)

# Intervalli basati sui quantili dei residui (1% - 99%)
res_q <- quantile(residuals(mod_arimax), probs = c(0.01, 0.25, 0.75, 0.99))

ci_quantili <- data.frame(
  Mese  = c("Gennaio", "Febbraio", "Marzo"),
  Q01   = round(exp(forecast_arimax$mean + res_q[1]), 2),
  Q25   = round(exp(forecast_arimax$mean + res_q[2]), 2),
  Stima = round(as.numeric(pred_orig), 2),
  Q75   = round(exp(forecast_arimax$mean + res_q[3]), 2),
  Q99   = round(exp(forecast_arimax$mean + res_q[4]), 2)
)

cat("\nIntervalli di confidenza (quantili residui, 1%-99%):\n")
print(ci_quantili, row.names = FALSE)

# Visualizzazione forecast ARIMAX (scala log)
autoplot(forecast_arimax) +
  labs(title = "Previsione ARIMAX - Vendite Auto USA (Q1 2025)",
       subtitle = paste0("Modello: ARIMAX(",
                         paste(best_order$order, collapse = ","), ")(",
                         paste(best_order$seasonal, collapse = ","), ")[12]"),
       x = "Anno", y = "log(Vendite)") +
  theme_minimal(base_size = 13)

# Forecast in scala originale con bande di confidenza
forecast_plot_df <- data.frame(
  Mese     = factor(c("Gen 2025", "Feb 2025", "Mar 2025"),
                    levels = c("Gen 2025", "Feb 2025", "Mar 2025")),
  Forecast = as.numeric(pred_orig),
  Q01      = as.numeric(ci_quantili$Q01),
  Q25      = as.numeric(ci_quantili$Q25),
  Q75      = as.numeric(ci_quantili$Q75),
  Q99      = as.numeric(ci_quantili$Q99)
)

ggplot(forecast_plot_df, aes(x = Mese)) +
  geom_ribbon(aes(ymin = Q01, ymax = Q99, group = 1),
              fill = "gray80", alpha = 0.5) +
  geom_ribbon(aes(ymin = Q25, ymax = Q75, group = 1),
              fill = "steelblue", alpha = 0.4) +
  geom_line(aes(y = Forecast, group = 1),
            color = "purple4", linewidth = 1.2) +
  geom_point(aes(y = Forecast), color = "purple4", size = 3) +
  geom_text(aes(y = Forecast, label = round(Forecast, 1)),
            vjust = -1.5, size = 4, color = "purple4") +
  geom_text(aes(y = Q01, label = paste0("1%: ", round(Q01, 0))),
            vjust = 1.5, size = 3, color = "red") +
  geom_text(aes(y = Q99, label = paste0("99%: ", round(Q99, 0))),
            vjust = -1, size = 3, color = "red") +
  labs(title = "Forecast ARIMAX - Scala Originale",
       subtitle = "Bande: 1%-99% (grigio) e 25%-75% (blu)",
       x = NULL, y = "Vendite (milioni USD)") +
  theme_minimal(base_size = 13)


# ==============================================================================
# RIEPILOGO METRICHE
# ==============================================================================

cat("\n", strrep("=", 60), "\n")
cat("RIEPILOGO METRICHE\n")
cat(strrep("=", 60), "\n\n")

# Metriche ARIMAX sul training set
acc <- accuracy(mod_arimax)

metriche <- data.frame(
  Metrica = c("ME (Mean Error)", "RMSE", "MAE", "MAPE", "ACF1 Residui"),
  Valore  = c(round(acc[1, "ME"], 4),
              round(acc[1, "RMSE"], 4),
              round(acc[1, "MAE"], 4),
              paste0(round(acc[1, "MAPE"], 2), "%"),
              round(acc[1, "ACF1"], 4))
)

cat("Metriche ARIMAX (training set):\n")
print(metriche, row.names = FALSE)

# Influenza delle variabili esogene
coef_xreg <- coef(mod_arimax)[c("log_petrol", "log_unemp", "log_interest")]

influenza <- data.frame(
  Variabile    = c("Prezzo petrolio", "Tasso disoccupazione", "Tasso d'interesse"),
  Coefficiente = round(as.numeric(coef_xreg), 4),
  Direzione    = ifelse(coef_xreg > 0, "Positiva (+)", "Negativa (-)")
)

cat("\nInfluenza variabili esogene:\n")
print(influenza, row.names = FALSE)

cat("\n", strrep("=", 60), "\n")
cat("ANALISI COMPLETATA\n")
cat(strrep("=", 60), "\n")
