# ==============================================================================
# Previsione Trimestrale dei Ricavi Apple — Support Vector Regression
# ==============================================================================
# Obiettivo: prevedere i ricavi trimestrali di Apple a partire da indicatori
# macroeconomici (Fiducia Consumatori, Business Confidence, Prezzo del Rame)
# tramite un modello SVR con kernel radiale.
#
# Pipeline:
#   1. Test di stazionarietà ADF e differenziazione
#   2. SVR con time-series cross-validation e grid search
#   3. Modelli surrogati (albero decisionale + regressione polinomiale)
#   4. Previsione out-of-sample a 4 trimestri (ARIMA sulle esogene)
# ==============================================================================

rm(list = ls())

# --- Librerie ----------------------------------------------------------------

library(readxl)
library(tseries)
library(caret)
library(e1071)
library(corrplot)
library(forecast)
library(rpart)
library(rpart.plot)

# ==============================================================================
# 1. CARICAMENTO DATI E TEST DI STAZIONARIETÀ
# ==============================================================================

ricavi_apple <- read_excel("Ricavi_APPLE.xlsx", sheet = "Dati APPLE")

# Funzione helper per test ADF con output formattato
run_adf <- function(series, name) {
  result <- adf.test(series)
  cat(sprintf("  %-30s p = %.4f  %s\n",
              name, result$p.value,
              ifelse(result$p.value < 0.05, "[Stazionaria]", "[NON stazionaria]")))
  return(result)
}

cat("\n=== Test ADF — Serie originali ===\n")
run_adf(ricavi_apple$Ricavi,                  "Ricavi")
run_adf(ricavi_apple$Fiducia_Consumatori_Usa, "Fiducia Consumatori USA")
run_adf(ricavi_apple$Business_Confidence_Usa, "Business Confidence USA")
run_adf(ricavi_apple$Copper,                  "Copper")

# Differenziazione delle serie non stazionarie
ricavi_diff  <- diff(ricavi_apple$Ricavi)
fiducia_diff <- diff(ricavi_apple$Fiducia_Consumatori_Usa)
copper_diff  <- diff(ricavi_apple$Copper)

cat("\n=== Test ADF — Serie differenziate ===\n")
run_adf(ricavi_diff,  "Ricavi (diff)")
run_adf(fiducia_diff, "Fiducia Consumatori (diff)")
run_adf(copper_diff,  "Copper (diff)")

# ==============================================================================
# 2. PREPARAZIONE DATI
# ==============================================================================

df <- data.frame(
  Business_Confidence_Usa = ricavi_apple$Business_Confidence_Usa[-1],
  ricavi_diff             = ricavi_diff,
  fiducia_diff            = fiducia_diff,
  copper_diff             = copper_diff
)

# Standardizzazione Z-score
scaling_params <- list(center = colMeans(df), scale = apply(df, 2, sd))
df <- as.data.frame(scale(df))

# Train / Test split (ultime 10 osservazioni per il test)
n     <- nrow(df)
train <- df[1:(n - 10), ]
test  <- df[(n - 9):n, ]

cat(sprintf("\nDataset: %d obs | Train: %d | Test: %d\n", n, nrow(train), nrow(test)))

# --- Matrice di correlazione --------------------------------------------------

corrplot(cor(df, use = "complete.obs"),
         method = "color", type = "upper",
         tl.cex = 0.8, tl.col = "black", order = "hclust",
         title = "Correlazione tra variabili",
         mar = c(0, 0, 2, 0))

# ==============================================================================
# 3. SUPPORT VECTOR REGRESSION
# ==============================================================================

# Cross-validation con finestra temporale espandibile
train_control <- trainControl(
  method           = "timeslice",
  initialWindow    = 60,
  horizon          = 10,
  fixedWindow      = FALSE,
  savePredictions  = "final"
)

# Grid search sugli iperparametri C e sigma
tune_grid <- expand.grid(
  C     = 2^(-5:5),
  sigma = 2^(-5:5)
)

set.seed(123)
svm_model <- train(
  ricavi_diff ~ .,
  data      = train,
  method    = "svmRadial",
  trControl = train_control,
  tuneGrid  = tune_grid
)

cat("\n=== Migliori iperparametri SVR ===\n")
print(svm_model$bestTune)

# --- Valutazione sul test set -------------------------------------------------

y_pred <- predict(svm_model, test)

metrics <- data.frame(
  Metrica = c("MAE", "RMSE", "R²"),
  Valore  = c(
    mean(abs(y_pred - test$ricavi_diff)),
    sqrt(mean((y_pred - test$ricavi_diff)^2)),
    cor(y_pred, test$ricavi_diff)^2
  )
)

cat("\n=== Metriche sul Test Set ===\n")
print(metrics, row.names = FALSE, digits = 4)

# ==============================================================================
# 4. MODELLI SURROGATI (interpretabilità)
# ==============================================================================

# --- 4a. Albero decisionale ---------------------------------------------------

surrogate_tree <- rpart(
  y_pred ~ Business_Confidence_Usa + copper_diff + fiducia_diff,
  data    = test,
  method  = "anova",
  control = rpart.control(cp = 0.001, maxdepth = 30, minsplit = 2)
)

rpart.plot(surrogate_tree, type = 3, extra = 101, fallen.leaves = TRUE,
           main = "Albero decisionale surrogato")

if (length(surrogate_tree$variable.importance) > 0) {
  barplot(surrogate_tree$variable.importance,
          main = "Importanza delle variabili (Albero Decisionale)",
          col = "steelblue", las = 2)
}

y_pred_tree <- predict(surrogate_tree, test)
r2_tree     <- cor(y_pred, y_pred_tree)^2
cat(sprintf("\nR² Surrogato (Albero) vs SVR: %.4f\n", r2_tree))

# --- 4b. Regressione polinomiale (grado 2) -----------------------------------

surrogate_poly <- lm(
  y_pred ~ poly(Business_Confidence_Usa, 2) +
           poly(fiducia_diff, 2) +
           poly(copper_diff, 2),
  data = test
)

y_pred_poly <- predict(surrogate_poly, test)
r2_poly     <- cor(y_pred, y_pred_poly)^2

cat(sprintf("R² Surrogato (Polinomiale) vs SVR: %.4f\n", r2_poly))
summary(surrogate_poly)

# --- Confronto visuale sul test set -------------------------------------------

y_range <- range(c(test$ricavi_diff, y_pred, y_pred_tree, y_pred_poly))
plot(test$ricavi_diff, type = "l", col = "black", lwd = 2, ylim = y_range,
     main = "Confronto: Valori Reali vs SVR vs Surrogati",
     xlab = "Osservazione", ylab = "Ricavi (diff, standardizzati)")
lines(y_pred,      col = "blue",      lwd = 2)
lines(y_pred_tree, col = "red",       lwd = 2, lty = 2)
lines(y_pred_poly, col = "darkgreen", lwd = 2, lty = 3)
legend("topright",
       legend = c("Valori Reali", "SVR", "Albero Decisionale", "Regressione Polinomiale"),
       col    = c("black", "blue", "red", "darkgreen"),
       lty    = c(1, 1, 2, 3), lwd = 2)

# ==============================================================================
# 5. PREVISIONE FUTURA (4 trimestri)
# ==============================================================================

# Dummy per la crisi finanziaria 2008 (usata come regressore esterno)
dates <- ricavi_apple$Date[-1]
dummy_crisis_2008 <- ifelse(
  format(dates, "%Y") == "2008" & format(dates, "%m") == "12", 1, 0
)

# ARIMA sulle variabili esogene per generare input futuri alla SVR
fit_consconf <- Arima(df$fiducia_diff,
                      order = c(1, 0, 1),
                      seasonal = list(order = c(1, 0, 0), period = 4))
fcast_consconf <- forecast(fit_consconf, h = 4)

fit_busconf <- Arima(df$Business_Confidence_Usa,
                     order = c(1, 0, 1),
                     seasonal = list(order = c(0, 0, 1), period = 4),
                     xreg = dummy_crisis_2008)
fcast_busconf <- forecast(fit_busconf, xreg = rep(0, 4), h = 4)

fit_copper <- Arima(df$copper_diff,
                    order = c(1, 0, 1),
                    seasonal = list(order = c(0, 0, 1), period = 4))
fcast_copper <- forecast(fit_copper, h = 4)

# Previsione dei ricavi differenziati (scala standardizzata)
future_macro <- data.frame(
  fiducia_diff            = as.numeric(fcast_consconf$mean),
  Business_Confidence_Usa = as.numeric(fcast_busconf$mean),
  copper_diff             = as.numeric(fcast_copper$mean)
)

pred_scaled <- predict(svm_model, newdata = future_macro)

# De-standardizzazione e ricostruzione dei ricavi cumulati
pred_diff <- pred_scaled * scaling_params$scale["ricavi_diff"] +
             scaling_params$center["ricavi_diff"]
last_revenue       <- tail(ricavi_apple$Ricavi, 1)
predicted_revenues <- last_revenue + cumsum(pred_diff)

# Intervallo di confidenza al 95% (basato sui residui del test set)
residuals_test <- test$ricavi_diff - y_pred
sigma_scaled   <- sd(residuals_test) * scaling_params$scale["ricavi_diff"]
lower_ci       <- predicted_revenues - 1.96 * sigma_scaled
upper_ci       <- predicted_revenues + 1.96 * sigma_scaled

results <- data.frame(
  Trimestre        = paste0("Q", 1:4),
  Ricavi_Previsti  = round(predicted_revenues),
  Lower_CI_95      = round(lower_ci),
  Upper_CI_95      = round(upper_ci)
)

cat("\n=== Previsione Ricavi Apple (prossimi 4 trimestri) ===\n")
print(results, row.names = FALSE)
