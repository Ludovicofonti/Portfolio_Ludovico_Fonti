# ============================================================================
# Campagna Marketing Bancario - Regressione Logistica
# ============================================================================
# Modello predittivo per stimare la probabilita' di adesione a depositi a
# termine, ottimizzando le risorse della campagna di marketing diretto.
#
# Pipeline: Preprocessing -> Feature Engineering -> SMOTE -> Logistic
#           Regression -> Valutazione -> Diagnostica (ANOVA, Chow Test)
# ============================================================================

rm(list = ls())

# Librerie ----
library(readxl)
library(dplyr)
library(ggplot2)
library(janitor)
library(corrplot)
library(isotree)
library(smotefamily)
library(caTools)
library(caret)
library(car)
library(pROC)


# 1. Caricamento e unione dei dati ----

features <- read_excel("Marketing_Campaign.xlsx", sheet = "Features")
targets  <- read_excel("Marketing_Campaign.xlsx", sheet = "Targets")

marketing_raw <- left_join(features, targets, by = "Record ID")
colnames(marketing_raw) <- make_clean_names(colnames(marketing_raw))

cat("Dimensione dataset:", nrow(marketing_raw), "x", ncol(marketing_raw), "\n")
str(marketing_raw)


# 2. Analisi esplorativa ----

# Valori mancanti
cat("\nValori mancanti per colonna:\n")
print(colSums(is.na(marketing_raw)))

# Distribuzione del target
cat("\nDistribuzione target:\n")
print(table(marketing_raw$target))
print(prop.table(table(marketing_raw$target)))


# 3. Standardizzazione Min-Max ----

# Salva copia originale per back-transformation dei coefficienti
marketing_original <- marketing_raw

min_max_scale <- function(x) (x - min(x)) / (max(x) - min(x))

numeric_cols <- marketing_raw %>% select(where(is.numeric))
non_numeric_cols <- marketing_raw %>% select(where(~ !is.numeric(.)))

marketing_data <- bind_cols(
  as.data.frame(lapply(numeric_cols, min_max_scale)),
  non_numeric_cols
)


# 4. Rilevamento outlier con Isolation Forest ----

set.seed(123)
numeric_for_iso <- marketing_data %>% select(where(is.numeric))
iso_model <- isolation.forest(numeric_for_iso, ntrees = 100, nthreads = 1)
anomaly_scores <- predict(iso_model, numeric_for_iso, type = "score")

threshold_outlier <- quantile(anomaly_scores, 0.90)
is_outlier <- anomaly_scores > threshold_outlier

ggplot(data.frame(score = anomaly_scores), aes(x = score)) +
  geom_histogram(bins = 30, fill = "steelblue", alpha = 0.7) +
  geom_vline(xintercept = threshold_outlier, color = "red", linetype = "dashed") +
  labs(
    title = "Distribuzione dei punteggi di anomalia (Isolation Forest)",
    x = "Anomaly Score", y = "Frequenza"
  ) +
  theme_minimal()

cat("\nOutlier rimossi:", sum(is_outlier), "su", length(is_outlier), "osservazioni\n")
marketing_data <- marketing_data[!is_outlier, ]


# 5. Feature Engineering: Age^2 ----

marketing_data$age2 <- marketing_data$age^2


# 6. Rimozione record con valori 'unknown' ----

marketing_data <- marketing_data %>%
  filter(
    job != "unknown",
    marital_status != "unknown",
    education != "unknown",
    house_ownershi != "unknown",
    existing_loans != "unknown"
  )

cat("Osservazioni dopo pulizia unknown:", nrow(marketing_data), "\n")


# 7. Encoding variabili categoriche ----

# Ordinale: education
marketing_data <- marketing_data %>%
  mutate(education = case_when(
    education == "illiterate"           ~ 1,
    education == "basic.4y"             ~ 2,
    education == "basic.6y"             ~ 3,
    education == "basic.9y"             ~ 4,
    education == "high.school"          ~ 5,
    education == "professional.course"  ~ 6,
    education == "university.degree"    ~ 7,
    TRUE ~ NA_real_
  ))

# Binarie
marketing_data <- marketing_data %>%
  mutate(
    marital_status  = ifelse(marital_status == "married", 1, 0),
    house_ownershi  = ifelse(house_ownershi == "yes", 1, 0),
    existing_loans  = ifelse(existing_loans == "yes", 1, 0),
    contact_channel = ifelse(contact_channel == "cellular", 1, 0)
  )


# 8. Analisi delle correlazioni ----

cor_data <- marketing_data %>% select(-record_id)
cor_matrix <- cor(cor_data %>% select(where(is.numeric)))
corrplot(cor_matrix, method = "square", addCoef.col = "black", number.cex = 0.5,
         title = "Matrice di correlazione - Pre selezione", mar = c(0, 0, 1, 0))


# 9. Selezione variabili per il modello ----

# Escluse:
#   - call_duration: disponibile solo post-chiamata -> data leakage
#   - cons_price_idx, emp_var_rate, cons_conf_idx: alta multicollinearita'
#   - record_id: identificativo, non predittivo
#   - day_of_week, pdays, campaign, previous_default: bassa rilevanza
df_model <- marketing_data %>%
  select(-record_id, -call_duration,
         -cons_price_idx, -emp_var_rate, -cons_conf_idx,
         -day_of_week, -pdays, -campaign, -previous_default)

# Correlazione post-selezione
cor_post <- cor(df_model %>% select(where(is.numeric)))
corrplot(cor_post, method = "square", addCoef.col = "black", number.cex = 0.7,
         title = "Matrice di correlazione - Post selezione", mar = c(0, 0, 1, 0))


# 10. Dummy encoding: job e stagioni ----

# Raggruppamento professionale
job_groups <- list(
  non_occupati   = c("unemployed", "retired", "student", "housemaid"),
  manuali        = c("blue-collar", "services", "technician"),
  amministrativi = c("admin", "management"),
  autonomi       = c("self-employed", "entrepreneur")
)

# Dummy per gruppi professionali (baseline: non_occupati)
df_model <- df_model %>%
  mutate(
    manuali        = as.integer(job %in% job_groups$manuali),
    amministrativi = as.integer(job %in% job_groups$amministrativi),
    autonomi       = as.integer(job %in% job_groups$autonomi)
  ) %>%
  select(-job)

# One-Hot Encoding per variabili rimanenti (month, poutcome)
df_model <- df_model %>%
  mutate(across(where(is.character), as.factor))

df_encoded <- model.matrix(~ . - 1, data = df_model) %>% as.data.frame()

# Aggregazione mesi in stagioni (baseline: inverno)
df_encoded <- df_encoded %>%
  mutate(
    season_spring = monthmar + monthmay,
    season_summer = monthjun + monthjul + monthaug,
    season_autumn = monthsep + monthoct + monthnov
  ) %>%
  select(-starts_with("month"))


# 11. Bilanciamento classi con SMOTE ----

cat("\nDistribuzione target pre-SMOTE:\n")
print(table(df_encoded$target))

X_smote <- df_encoded %>% select(-target)
y_smote <- df_encoded$target

set.seed(123)
smote_result <- SMOTE(X_smote, y_smote, K = 5, dup_size = 10)
df_balanced <- smote_result$data

cat("\nDistribuzione target post-SMOTE:\n")
print(table(df_balanced$class))


# 12. Train / Test split (80/20) ----

set.seed(123)
split_idx <- sample.split(df_balanced$class, SplitRatio = 0.80)

train <- df_balanced[split_idx, ]
test  <- df_balanced[!split_idx, ]

train$class <- as.numeric(as.character(train$class))
test$class  <- as.numeric(as.character(test$class))

cat("\nTrain:", nrow(train), "- Test:", nrow(test), "\n")


# 13. Regressione Logistica ----

model_logit <- glm(class ~ ., data = train, family = binomial)
summary(model_logit)

cat("\nVIF (Variance Inflation Factor):\n")
print(vif(model_logit))


# 14. Odds Ratio ----

coefs <- coef(model_logit)
odds_ratios <- exp(coefs)

odds_table <- data.frame(
  variable   = names(coefs),
  beta       = coefs,
  odds_ratio = odds_ratios,
  pct_change = (odds_ratios - 1) * 100,
  row.names  = NULL
) %>%
  arrange(desc(abs(beta)))

cat("\nOdds Ratio (ordinati per importanza):\n")
print(odds_table, digits = 4)


# 15. Bonta' del modello ----

null_model   <- glm(class ~ 1, data = train, family = binomial)
mcfadden_r2  <- 1 - as.numeric(logLik(model_logit) / logLik(null_model))
aic_value    <- AIC(model_logit)

cat("\nMcFadden R²:", round(mcfadden_r2, 4), "\n")
cat("AIC:", round(aic_value, 2), "\n")


# 16. Soglia ottimale (Youden) ----

prob_train <- predict(model_logit, newdata = train, type = "response")
roc_train  <- roc(train$class, prob_train, quiet = TRUE)

optimal <- coords(roc_train, "best",
                  ret = c("threshold", "sensitivity", "specificity"),
                  best.method = "youden")

optimal_threshold <- optimal$threshold
cat("\nSoglia ottimale (Youden):", round(optimal_threshold, 4), "\n")
cat("Sensitivity:", round(optimal$sensitivity, 4), "\n")
cat("Specificity:", round(optimal$specificity, 4), "\n")


# 17. Valutazione sul Training set ----

pred_train <- ifelse(prob_train > optimal_threshold, 1, 0)
cm_train   <- confusionMatrix(as.factor(pred_train), as.factor(train$class), positive = "1")

cat("\n=== Confusion Matrix - TRAIN ===\n")
print(cm_train)

auc_train <- auc(roc_train)
f1_train  <- cm_train$byClass["F1"]

cat("\nAUC Train:", round(as.numeric(auc_train), 4), "\n")
cat("F1 Train:", round(f1_train, 4), "\n")

plot(roc_train, col = "steelblue", lwd = 2, main = "ROC Curve - Training Set")
abline(a = 0, b = 1, lty = 2, col = "grey50")


# 18. Valutazione sul Test set ----

prob_test  <- predict(model_logit, newdata = test, type = "response")
pred_test  <- ifelse(prob_test > optimal_threshold, 1, 0)
cm_test    <- confusionMatrix(as.factor(pred_test), as.factor(test$class), positive = "1")

cat("\n=== Confusion Matrix - TEST ===\n")
print(cm_test)

roc_test  <- roc(test$class, prob_test, quiet = TRUE)
auc_test  <- auc(roc_test)
f1_test   <- cm_test$byClass["F1"]

cat("\nAUC Test:", round(as.numeric(auc_test), 4), "\n")
cat("F1 Test:", round(f1_test, 4), "\n")

plot(roc_test, col = "coral", lwd = 2, main = "ROC Curve - Test Set")
abline(a = 0, b = 1, lty = 2, col = "grey50")

# Confronto ROC Train vs Test
plot(roc_train, col = "steelblue", lwd = 2, main = "ROC Curve - Train vs Test")
plot(roc_test, col = "coral", lwd = 2, add = TRUE)
abline(a = 0, b = 1, lty = 2, col = "grey50")
legend("bottomright",
       legend = c(paste0("Train (AUC = ", round(as.numeric(auc_train), 4), ")"),
                  paste0("Test  (AUC = ", round(as.numeric(auc_test), 4), ")")),
       col = c("steelblue", "coral"), lwd = 2)


# 19. Back-transformation dei coefficienti ----

# Recupera min/max dalle variabili originali per riportare i beta alla scala naturale
scaling_info <- data.frame(
  variable = names(marketing_original %>% select(where(is.numeric))),
  min_val  = sapply(marketing_original %>% select(where(is.numeric)), min, na.rm = TRUE),
  max_val  = sapply(marketing_original %>% select(where(is.numeric)), max, na.rm = TRUE),
  row.names = NULL
)

coeff_df <- data.frame(
  variable    = names(coefs),
  beta_scaled = coefs,
  row.names   = NULL
)

coeff_merged <- merge(coeff_df, scaling_info, by = "variable", all.x = TRUE)
coeff_merged$beta_original <- ifelse(
  !is.na(coeff_merged$min_val),
  coeff_merged$beta_scaled / (coeff_merged$max_val - coeff_merged$min_val),
  coeff_merged$beta_scaled
)

cat("\nCoefficenti nella scala originale:\n")
print(coeff_merged[, c("variable", "beta_scaled", "beta_original")], digits = 4)


# 20. Diagnostica: ANOVA - Test rapporto di verosimiglianza ----

# Verifica se age^2 migliora significativamente il modello
model_no_age2 <- glm(class ~ . - age2, data = train, family = binomial)

cat("\n=== ANOVA: modello completo vs. modello senza age2 ===\n")
print(anova(model_no_age2, model_logit, test = "Chisq"))


# 21. Diagnostica: Test di Chow ----

# Identifica l'eta' ottimale (vertice della parabola)
b_age  <- coef(model_logit)["age"]
b_age2 <- coef(model_logit)["age2"]
age_optimal_scaled <- -b_age / (2 * b_age2)

min_age <- min(marketing_original$age, na.rm = TRUE)
max_age <- max(marketing_original$age, na.rm = TRUE)
age_optimal_original <- age_optimal_scaled * (max_age - min_age) + min_age

cat("\nEta' ottimale (scala standardizzata):", round(age_optimal_scaled, 4), "\n")
cat("Eta' ottimale (scala originale):", round(age_optimal_original, 2), "anni\n")

# Split per gruppo di eta' e test di Chow
group_young <- train %>% filter(age <= age_optimal_scaled)
group_old   <- train %>% filter(age > age_optimal_scaled)

model_young  <- glm(class ~ ., data = group_young,  family = binomial)
model_old    <- glm(class ~ ., data = group_old,    family = binomial)
model_pooled <- glm(class ~ ., data = train,        family = binomial)

rss_young  <- sum(resid(model_young)^2)
rss_old    <- sum(resid(model_old)^2)
rss_pooled <- sum(resid(model_pooled)^2)

k  <- length(coef(model_pooled))
n1 <- nrow(group_young)
n2 <- nrow(group_old)

f_chow  <- ((rss_pooled - (rss_young + rss_old)) / k) /
           ((rss_young + rss_old) / (n1 + n2 - 2 * k))
p_chow  <- pf(f_chow, df1 = k, df2 = (n1 + n2 - 2 * k), lower.tail = FALSE)

cat("\n=== Test di Chow ===\n")
cat("F-statistic:", round(f_chow, 4), "\n")
cat("p-value:", round(p_chow, 4), "\n")
if (p_chow < 0.05) {
  cat("-> Break strutturale significativo: i coefficienti differiscono tra i due gruppi di eta'.\n")
} else {
  cat("-> Nessun break strutturale significativo.\n")
}


# 22. Riepilogo finale ----

cat("\n")
cat("======================================================\n")
cat("          RIEPILOGO RISULTATI DEL MODELLO\n")
cat("======================================================\n")
cat(sprintf("  %-25s %10s %10s\n", "Metrica", "Train", "Test"))
cat("------------------------------------------------------\n")
cat(sprintf("  %-25s %10.4f %10.4f\n", "Accuracy",
            cm_train$overall["Accuracy"], cm_test$overall["Accuracy"]))
cat(sprintf("  %-25s %10.4f %10.4f\n", "AUC",
            as.numeric(auc_train), as.numeric(auc_test)))
cat(sprintf("  %-25s %10.4f %10.4f\n", "Sensitivity",
            cm_train$byClass["Sensitivity"], cm_test$byClass["Sensitivity"]))
cat(sprintf("  %-25s %10.4f %10.4f\n", "Specificity",
            cm_train$byClass["Specificity"], cm_test$byClass["Specificity"]))
cat(sprintf("  %-25s %10.4f %10.4f\n", "F1-Score", f1_train, f1_test))
cat(sprintf("  %-25s %10.4f %10s\n",   "McFadden R2", mcfadden_r2, "-"))
cat(sprintf("  %-25s %10.2f %10s\n",   "AIC", aic_value, "-"))
cat(sprintf("  %-25s %10.4f %10s\n",   "Soglia ottimale", optimal_threshold, "-"))
cat("======================================================\n")
cat("Eta' ottimale (vertice parabola):", round(age_optimal_original, 1), "anni\n")
cat("Test di Chow (break strutturale): p-value =", round(p_chow, 4), "\n")
cat("======================================================\n")
