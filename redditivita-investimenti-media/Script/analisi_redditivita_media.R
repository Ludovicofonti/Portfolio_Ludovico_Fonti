# ==============================================================================
# Redditività di un Investimento nel Settore Media USA
# ==============================================================================
# Obiettivo: stimare l'EPS (Earnings Per Share) a 12 mesi per aziende del
# Russell 3000, e applicare il modello a un campione di aziende italiane
# del settore media per valutare la competitività di un ingresso nel mercato USA.
#
# Pipeline: EDA → Outlier Detection → Feature Engineering → Regressione Lineare
#           → Diagnostica → Bootstrap CI → Cross-Validation → Previsioni
# ==============================================================================

# --- 0. Setup -----------------------------------------------------------------
rm(list = ls())

library(rstudioapi)
library(ggplot2)
library(dplyr)
library(readxl)
library(corrplot)
library(GGally)
library(isotree)
library(car)
library(boot)
library(caret)
library(lmtest)
library(olsrr)

current_path <- getActiveDocumentContext()$path
setwd(dirname(current_path))

# --- 1. Caricamento Dati -----------------------------------------------------

# Dataset Russell 3000 (fondamentali finanziari)
file_path <- "Russell_3000_Fundamentals_Enlarged_With_README.xlsx"
sheets <- excel_sheets(file_path)

target  <- read_excel(file_path, sheet = sheets[2]) %>% na.omit()
dataset <- read_excel(file_path, sheet = sheets[3]) %>% na.omit()

df <- left_join(dataset, target, by = "Record ID") %>%
  select(-`Record ID`)

# Dataset aziende italiane del settore media (test set)
test_set <- read.csv("Dati_Sintetici_Settore_Media.csv")

# Rinomina variabili con nomi poco leggibili
df <- df %>%
  rename(
    ROE  = `RETURN_ON_ EQUITY`,
    ROA  = RETURN_ON_ASSET,
    ROIC = RETURN_ON_INVESTED_CAPITAl
  )

cat("Dimensioni dataset:", nrow(df), "osservazioni,", ncol(df), "variabili\n")
str(df)

# --- 2. Analisi Esplorativa (EDA) --------------------------------------------

# 2.1 Distribuzione variabili chiave
vars_hist <- c("EPS_12M_FORWARD", "FREE_CASH_FLOW", "ENTERPRISE_VALUE",
               "NET_SALES", "EBITDA", "ROE", "ROA")

for (var in vars_hist) {
  p <- ggplot(df, aes(x = .data[[var]])) +
    geom_histogram(bins = 30, fill = "steelblue", alpha = 0.7, color = "white") +
    labs(title = paste("Distribuzione:", var), x = var, y = "Frequenza") +
    theme_minimal()
  print(p)
}

# 2.2 Boxplot variabili numeriche principali
par(mfrow = c(2, 3))
boxplot(df$EPS_12M_FORWARD, main = "EPS 12M Forward", col = "steelblue")
boxplot(df$NET_SALES,       main = "Net Sales",       col = "steelblue")
boxplot(df$FREE_CASH_FLOW,  main = "Free Cash Flow",  col = "steelblue")
boxplot(df$ROE,             main = "ROE",             col = "steelblue")
boxplot(df$ROA,             main = "ROA",             col = "steelblue")
boxplot(df$EBITDA,          main = "EBITDA",          col = "steelblue")
par(mfrow = c(1, 1))

# 2.3 Scatterplot: variabili chiave vs EPS
scatter_vars <- c("NET_SALES", "ENTERPRISE_VALUE", "FREE_CASH_FLOW", "ROA")
scatter_cols <- c("steelblue", "forestgreen", "purple", "darkorange")

for (i in seq_along(scatter_vars)) {
  p <- ggplot(df, aes(x = .data[[scatter_vars[i]]], y = EPS_12M_FORWARD)) +
    geom_point(color = scatter_cols[i], alpha = 0.5) +
    geom_smooth(method = "lm", color = "red", se = FALSE) +
    labs(title = paste("EPS vs", scatter_vars[i]),
         x = scatter_vars[i], y = "EPS 12M Forward") +
    theme_minimal()
  print(p)
}

# 2.4 Confronto EBITDA tra settori
ggplot(df, aes(x = INDUSTRY, y = EBITDA)) +
  geom_boxplot(fill = "steelblue", alpha = 0.6) +
  labs(title = "Confronto EBITDA tra settori", x = "Settore", y = "EBITDA") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# 2.5 Matrice di correlazione (dati grezzi)
corr_matrix_raw <- cor(df[, sapply(df, is.numeric)], use = "complete.obs")

corrplot(corr_matrix_raw,
         method = "color", type = "upper", order = "hclust",
         addCoef.col = "black", tl.col = "black", tl.srt = 45,
         tl.cex = 0.7, number.cex = 0.6,
         col = colorRampPalette(c("blue", "white", "red3"))(200),
         title = "Matrice di Correlazione (dati grezzi)")

# --- 3. Rimozione Outlier con Isolation Forest --------------------------------

numeric_cols <- sapply(df, is.numeric)
df_numeric <- df[, numeric_cols]

set.seed(6)
iso_forest <- isolation.forest(df_numeric, ntrees = 100, nthreads = 1)
anomaly_scores <- predict(iso_forest, df_numeric, type = "score")
threshold <- quantile(anomaly_scores, 0.88)  # rimuoviamo il 12% piu' anomalo

# Distribuzione anomaly scores
ggplot(data.frame(score = anomaly_scores), aes(x = score)) +
  geom_histogram(bins = 30, fill = "steelblue", alpha = 0.7, color = "white") +
  geom_vline(xintercept = threshold, color = "red", linetype = "dashed", linewidth = 1) +
  annotate("text", x = threshold + 0.02, y = Inf, label = paste("Soglia:", round(threshold, 3)),
           vjust = 2, color = "red", fontface = "bold") +
  labs(title = "Distribuzione Anomaly Score (Isolation Forest)",
       x = "Anomaly Score", y = "Frequenza") +
  theme_minimal()

n_outlier <- sum(anomaly_scores > threshold)
cat("Outlier rimossi:", n_outlier, "su", nrow(df), "osservazioni\n")

df <- df[anomaly_scores <= threshold, ]

# --- 4. Feature Engineering ---------------------------------------------------

# 4.1 Standardizzazione Z-score (variabili indipendenti)
eps_original <- df$EPS_12M_FORWARD
df_std <- df %>% select(-EPS_12M_FORWARD)
df_std[sapply(df_std, is.numeric)] <- scale(df_std[sapply(df_std, is.numeric)])
df_std$EPS_12M_FORWARD <- eps_original

# 4.2 Trasformazione logaritmica (signed log1p per gestire valori negativi)
signed_log <- function(x) sign(x) * log1p(abs(x))

df_model <- df_std %>%
  mutate(
    log_EPS_12M_FORWARD  = signed_log(EPS_12M_FORWARD),
    log_FREE_CASH_FLOW   = signed_log(FREE_CASH_FLOW),
    log_ENTERPRISE_VALUE = signed_log(ENTERPRISE_VALUE),
    log_NET_SALES        = signed_log(NET_SALES),
    log_EBITDA           = signed_log(EBITDA)
  )

# --- 5. Correlazione e Multicollinearita' Post-Preprocessing ------------------

vars_corr <- c("EPS_12M_FORWARD", "NET_SALES", "ENTERPRISE_VALUE",
               "EBITDA", "FREE_CASH_FLOW", "ROE", "ROA", "ROIC")
cor_matrix <- cor(df_model[, vars_corr], use = "complete.obs")

corrplot(cor_matrix,
         method = "color", type = "upper", order = "hclust",
         addCoef.col = "black", tl.col = "black", tl.srt = 45,
         tl.cex = 0.7, number.cex = 0.6,
         col = colorRampPalette(c("blue", "white", "red3"))(200),
         title = "Matrice di Correlazione (post outlier removal)")

# Analisi autovalori e condition number
eig_values <- eigen(cor_matrix)$values
condition_number <- max(eig_values) / min(eig_values)
cat("Autovalori:", round(eig_values, 3), "\n")
cat("Condition Number (con ROIC):", round(condition_number, 2), "\n")

# Condition number senza ROIC (ridondante con ROA)
vars_no_roic <- setdiff(vars_corr, "ROIC")
cor_matrix_no_roic <- cor(df_model[, vars_no_roic], use = "complete.obs")
eig_no_roic <- eigen(cor_matrix_no_roic)$values
cn_no_roic <- max(eig_no_roic) / min(eig_no_roic)
cat("Condition Number (senza ROIC):", round(cn_no_roic, 2), "\n")

# --- 6. Regressione Lineare --------------------------------------------------

# Selezione variabili: ROIC esclusa per multicollinearita', ROE mantenuto
# Variabili log-trasformate per le distribuzioni asimmetriche
X <- df_model[, c("log_NET_SALES", "log_FREE_CASH_FLOW", "ROE", "ROA",
                   "log_EBITDA", "log_ENTERPRISE_VALUE")]
Y <- df_model$log_EPS_12M_FORWARD
df_lm <- data.frame(Y, X)

lm_model <- lm(Y ~ ., data = df_lm)

cat("\n========== RISULTATI REGRESSIONE LINEARE ==========\n")
summary(lm_model)

# VIF (Variance Inflation Factor)
cat("\nVIF (Variance Inflation Factor):\n")
print(vif(lm_model))

# --- 7. Diagnostica del Modello -----------------------------------------------

# 7.1 Grafici diagnostici standard
par(mfrow = c(2, 2))
plot(lm_model)
par(mfrow = c(1, 1))

# 7.2 Test di normalita' dei residui
residui <- residuals(lm_model)

# Test t: media residui = 0
cat("\nTest t (media residui = 0):\n")
print(t.test(residui))

# Shapiro-Wilk
cat("\nTest di Shapiro-Wilk (normalita'):\n")
print(shapiro.test(residui))

# Kolmogorov-Smirnov, Cramer-von Mises, Anderson-Darling
cat("\nTest di normalita' OLS:\n")
print(ols_test_normality(lm_model))

# QQ-Plot
ols_plot_resid_qq(lm_model)

# Istogramma residui
ols_plot_resid_hist(lm_model)

# 7.3 Test di eteroschedasticita' (Breusch-Pagan)
cat("\nTest di Breusch-Pagan (omoschedasticita'):\n")
print(bptest(formula(lm_model), data = df_lm))

# 7.4 Residui vs Fitted
yfit <- fitted(lm_model)
plot(yfit, residui, xlab = "Fitted", ylab = "Residui",
     main = "Residui vs Fitted", pch = 20, col = "steelblue")
abline(h = 0, col = "red", lwd = 2)

# 7.5 Analisi outlier residuali
rstand <- rstandard(lm_model)
plot(rstand, main = "Residui Standardizzati", pch = 20, col = "steelblue")
abline(h = c(-2, 2), col = "red", lty = 2)
cat("\nResidui standardizzati anomali (|r| > 2):", sum(abs(rstand) > 2), "\n")

# Residui studentizzati (jackknife)
rjack <- rstudent(lm_model)
n <- length(rjack)
p <- lm_model$rank
pv_bonferroni <- 2 * pt(abs(rjack), n - p - 1, lower.tail = FALSE)
cat("Residui jackknife significativi (Bonferroni p < 0.05):", sum(pv_bonferroni < 0.05), "\n")

# --- 8. Bootstrap — Intervalli di Confidenza ----------------------------------

lm_bootstrap <- function(data, indices) {
  df_boot <- data[indices, ]
  model <- lm(Y ~ ., data = df_boot)
  return(coef(model)[-1])  # escludiamo l'intercetta
}

set.seed(123)
boot_results <- boot(data = df_lm, statistic = lm_bootstrap, R = 1000)

cat("\n========== BOOTSTRAP — INTERVALLI DI CONFIDENZA 95% ==========\n")
cat(sprintf("%-25s %12s %12s %20s\n", "Variabile", "Coefficiente", "Std. Error", "IC 95%"))
cat(paste(rep("-", 75), collapse = ""), "\n")

std_err <- summary(lm_model)$coefficients[, 2]

for (i in 1:ncol(X)) {
  ci <- boot.ci(boot_results, type = "perc", index = i)
  coeff_name <- colnames(X)[i]
  coeff_val  <- coef(lm_model)[i + 1]
  se_val     <- std_err[i + 1]
  cat(sprintf("%-25s %12.4f %12.4f   [%7.4f, %7.4f]\n",
              coeff_name, coeff_val, se_val, ci$percent[4], ci$percent[5]))
}

r_squared <- summary(lm_model)$r.squared
adj_r_sq  <- summary(lm_model)$adj.r.squared
cat(sprintf("\nR²: %.4f | R² adj: %.4f\n", r_squared, adj_r_sq))

# --- 9. Cross-Validation (K-Fold) --------------------------------------------

set.seed(42)
ctrl <- trainControl(method = "cv", number = 10)

cv_formula <- Y ~ log_NET_SALES + log_FREE_CASH_FLOW + ROE + ROA +
  log_EBITDA + log_ENTERPRISE_VALUE

cv_model <- train(cv_formula, data = df_lm, method = "lm", trControl = ctrl)

cat("\n========== CROSS-VALIDATION (10-Fold) ==========\n")
print(cv_model)
print(cv_model$results)

# --- 10. Previsione Aziende Italiane (Test Set) -------------------------------

eps_reale <- test_set$EPS_12M_FORWARD
nomi_aziende <- test_set$Azienda

# Preprocessing identico al training
X_test <- test_set %>% select(-EPS_12M_FORWARD, -Azienda)
X_test[sapply(X_test, is.numeric)] <- scale(X_test[sapply(X_test, is.numeric)])

X_test <- X_test %>%
  mutate(
    log_FREE_CASH_FLOW   = signed_log(FREE_CASH_FLOW),
    log_ENTERPRISE_VALUE = signed_log(ENTERPRISE_VALUE),
    log_NET_SALES        = signed_log(NET_SALES),
    log_EBITDA           = signed_log(EBITDA)
  )

# Previsione (scala log) e ritrasformazione
pred_log <- predict(lm_model, newdata = X_test)
pred_originale <- exp(pred_log) - 1

# Risultati
risultati <- data.frame(
  Azienda       = nomi_aziende,
  EPS_reale     = eps_reale,
  EPS_previsto  = round(pred_originale, 2)
) %>%
  mutate(Errore_pct = round((EPS_previsto - EPS_reale) / abs(EPS_reale) * 100, 1))

cat("\n========== PREVISIONI AZIENDE ITALIANE ==========\n")
print(risultati)

# Grafico confronto EPS reale vs previsto
ggplot(risultati, aes(x = reorder(Azienda, EPS_reale))) +
  geom_col(aes(y = EPS_reale, fill = "Reale"), alpha = 0.7, width = 0.4,
           position = position_nudge(x = -0.2)) +
  geom_col(aes(y = EPS_previsto, fill = "Previsto"), alpha = 0.7, width = 0.4,
           position = position_nudge(x = 0.2)) +
  scale_fill_manual(values = c("Reale" = "steelblue", "Previsto" = "darkorange")) +
  labs(title = "EPS Reale vs Previsto — Aziende Italiane Settore Media",
       x = "Azienda", y = "EPS 12M Forward", fill = "") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

cat("\n========== ANALISI COMPLETATA ==========\n")
