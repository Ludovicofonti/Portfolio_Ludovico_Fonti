# ==============================================================================
# HR Analytics - Employee Attrition Analysis
# ==============================================================================
# Comprehensive analysis of employee attrition drivers using:
#   - Exploratory Data Analysis (EDA)
#   - Linear & Logistic Regression
#   - Discriminant Analysis (LDA / QDA)
#   - Principal Component Analysis (PCA)
#   - Clustering (Hierarchical, PAM, K-Means)
# ==============================================================================

# --- Libraries ----------------------------------------------------------------
library(readr)
library(dplyr)
library(ggplot2)
library(gridExtra)
library(corrplot)
library(car)
library(olsrr)
library(lmtest)
library(caret)
library(grid)
library(pscl)
library(aod)
library(MASS)
library(pROC)
library(ROSE)
library(klaR)
library(factoextra)
library(cluster)
library(NbClust)

# ==============================================================================
# 1. DATA LOADING & CLEANING
# ==============================================================================

df <- read.csv("HR_Analytics.csv")

# Remove uninformative columns
df_clean <- df %>%
  select(-EmpID, -EmployeeCount, -EmployeeNumber, -SalarySlab, -Over18, -StandardHours)

# Verifica e rimozione valori mancanti
cat("Missing values per colonna:\n")
print(colSums(is.na(df_clean)))
df_clean <- na.omit(df_clean)

# Fix inconsistent labels
df_clean <- df_clean %>%
  mutate(BusinessTravel = gsub("TravelRarely", "Travel_Rarely", BusinessTravel, fixed = TRUE))

# --- Create binary / dummy variables -----------------------------------------
df_clean <- df_clean %>%
  mutate(
    Attrition_bin   = as.numeric(Attrition == "Yes"),
    Travel          = as.numeric(BusinessTravel %in% c("Travel_Frequently", "Travel_Rarely")),
    Male            = as.numeric(Gender == "Male"),
    Relationship    = as.numeric(MaritalStatus == "Married"),
    OverTime_yes    = as.numeric(OverTime == "Yes")
  )

# --- Build regression dataset (numeric only) ----------------------------------
df_regression <- df_clean %>%
  select(-Attrition, -AgeGroup, -BusinessTravel, -Department,
         -Gender, -MaritalStatus, -OverTime, -EducationField, -JobRole)

# Log-transform MonthlyIncome and drop skewed / low-information rate variables
log_MonthlyIncome <- log(df_regression$MonthlyIncome)

df_regression <- df_regression %>%
  select(-MonthlyIncome, -YearsAtCompany, -TotalWorkingYears,
         -YearsSinceLastPromotion, -HourlyRate, -DailyRate, -MonthlyRate) %>%
  mutate(log_MonthlyIncome = log_MonthlyIncome)

# ==============================================================================
# 2. EXPLORATORY DATA ANALYSIS
# ==============================================================================

# --- 2.1 Boxplots of numeric variables ---------------------------------------
numeric_cols <- df_clean %>% select(where(is.numeric))

for (col_name in names(numeric_cols)) {
  boxplot(numeric_cols[[col_name]],
          main = col_name, ylab = "Value", col = "skyblue", border = "black")
}

# --- 2.2 Scatterplots vs MonthlyIncome ----------------------------------------
scatter_1 <- ggplot(df_clean, aes(x = MonthlyIncome, y = Age^0.5)) +
  geom_point() + labs(x = "Monthly Income", y = "sqrt(Age)") + theme_minimal()

scatter_2 <- ggplot(df_clean, aes(x = MonthlyIncome, y = JobLevel)) +
  geom_point() + labs(x = "Monthly Income", y = "Job Level") + theme_minimal()

scatter_3 <- ggplot(df_clean, aes(x = MonthlyIncome, y = YearsInCurrentRole)) +
  geom_point() + labs(x = "Monthly Income", y = "Years in Current Role") + theme_minimal()

scatter_4 <- ggplot(df_clean, aes(x = MonthlyIncome, y = NumCompaniesWorked)) +
  geom_point() + labs(x = "Monthly Income", y = "Num Companies Worked") + theme_minimal()

grid.arrange(scatter_1, scatter_2, scatter_3, scatter_4, nrow = 2)

# --- 2.3 Monthly Income distribution -----------------------------------------
hist_plot <- ggplot(df_clean, aes(x = MonthlyIncome)) +
  geom_histogram(binwidth = 500, fill = "steelblue", color = "black", alpha = 0.7) +
  labs(title = "Monthly Income Distribution", x = "Monthly Income", y = "Frequency") +
  theme_minimal()

density_plot <- ggplot(df_clean, aes(x = MonthlyIncome)) +
  geom_density(color = "steelblue", linewidth = 1.2) +
  labs(title = "Monthly Income Density", x = "Monthly Income", y = "Density") +
  theme_minimal()

grid.arrange(hist_plot, density_plot, ncol = 2)

# Combined histogram + density
ggplot(df_clean, aes(x = MonthlyIncome)) +
  geom_histogram(binwidth = 500, fill = "steelblue", color = "black", alpha = 0.7) +
  geom_density(aes(y = after_stat(count) * 500), color = "tomato", linewidth = 1) +
  labs(title = "Monthly Income: Histogram + Density",
       x = "Monthly Income", y = "Frequency") +
  theme_minimal()

# --- 2.4 Attrition breakdowns ------------------------------------------------
# Helper: bar chart with percentages
plot_attrition_by <- function(data, group_var, x_label, title) {
  pct <- data %>%
    group_by(across(all_of(c(group_var, "Attrition")))) %>%
    summarise(count = n(), .groups = "drop") %>%
    group_by(across(all_of(group_var))) %>%
    mutate(percentage = count / sum(count) * 100)

  ggplot(pct, aes(x = .data[[group_var]], y = count, fill = Attrition)) +
    geom_col(position = "dodge", color = "black") +
    geom_text(aes(label = sprintf("%.1f%%", percentage)),
              position = position_dodge(width = 0.9), vjust = -0.5, size = 3) +
    labs(x = x_label, y = "Count", title = title) +
    scale_fill_brewer(palette = "Set1", name = "Attrition") +
    theme_minimal() +
    theme(legend.position = "top")
}

plot_attrition_by(df_clean, "Gender",         "Gender",           "Attrition by Gender")
plot_attrition_by(df_clean, "AgeGroup",        "Age Group",        "Attrition by Age Group")
plot_attrition_by(df_clean, "OverTime",        "OverTime",         "Attrition by OverTime")
plot_attrition_by(df_clean, "BusinessTravel",  "Business Travel",  "Attrition by Business Travel")

# --- 2.5 Correlation matrix --------------------------------------------------
cor_matrix <- cor(df_regression)
corrplot(cor_matrix, method = "color", type = "upper",
         addCoef.col = "black", number.cex = 0.5,
         tl.cex = 0.5, tl.srt = 30)

# ==============================================================================
# 3. LINEAR REGRESSION — MonthlyIncome
# ==============================================================================

reg_model <- lm(log_MonthlyIncome ~ I(Age^0.5) + JobLevel +
                  YearsInCurrentRole + NumCompaniesWorked,
                data = df_regression)
summary(reg_model)

# Residual diagnostics
cat("Mean of residuals:", round(mean(reg_model$residuals), 6), "\n")
ols_plot_resid_qq(reg_model)
ols_test_normality(reg_model)
ols_plot_resid_hist(reg_model)
ncvTest(reg_model)                # Heteroscedasticity
ols_test_correlation(reg_model)   # Autocorrelation

# ==============================================================================
# 4. LOGISTIC REGRESSION — Attrition
# ==============================================================================

# --- 4.1 Train / test split --------------------------------------------------
set.seed(6)
train_idx <- createDataPartition(df_regression$Attrition_bin, p = 0.80, list = FALSE)
train_set <- df_regression[train_idx, ]
test_set  <- df_regression[-train_idx, ]

# --- 4.2 Fit model ------------------------------------------------------------
logit_model <- glm(Attrition_bin ~ ., family = binomial(link = "logit"), data = train_set)
summary(logit_model)

# --- 4.3 Evaluation at default threshold (0.5) --------------------------------
evaluate_logit <- function(model, data, threshold = 0.5) {
  probs <- predict(model, newdata = data, type = "response")
  preds <- as.numeric(probs > threshold)
  tab   <- table(Actual = data$Attrition_bin, Predicted = preds)
  n     <- nrow(data)

  accuracy    <- sum(diag(tab)) / n * 100
  sensitivity <- tab["1", "1"] / sum(tab["1", ]) * 100
  specificity <- tab["0", "0"] / sum(tab["0", ]) * 100

  cat(sprintf("Threshold: %.4f\n", threshold))
  cat(sprintf("Accuracy:  %.2f%%\n", accuracy))
  cat(sprintf("Sensitivity: %.2f%%\n", sensitivity))
  cat(sprintf("Specificity: %.2f%%\n", specificity))
  print(tab)
  invisible(list(tab = tab, accuracy = accuracy,
                 sensitivity = sensitivity, specificity = specificity))
}

evaluate_logit(logit_model, train_set, threshold = 0.5)

# --- 4.4 Optimal threshold via ROC / Youden -----------------------------------
roc_curve <- roc(train_set$Attrition_bin, predict(logit_model, type = "response"))
optimal   <- coords(roc_curve, x = "best", input = "threshold", best.method = "youden")
cat("Optimal threshold (Youden):", optimal$threshold, "\n")

evaluate_logit(logit_model, train_set, threshold = optimal$threshold)

# --- 4.5 Test-set performance -------------------------------------------------
cat("\n--- Test Set ---\n")
evaluate_logit(logit_model, test_set, threshold = 0.5)
evaluate_logit(logit_model, test_set, threshold = optimal$threshold)

# --- 4.6 McFadden R² & Wald tests --------------------------------------------
mcFadden <- pR2(logit_model)
print(mcFadden)

wald.test(b = coef(logit_model), Sigma = vcov(logit_model), Terms = 1:length(coef(logit_model)))

# --- 4.7 ROC curve plot -------------------------------------------------------
plot(roc_curve, col = "black", lwd = 2, main = "ROC Curve — Logistic Regression")
abline(v = optimal$specificity, h = optimal$sensitivity, col = "red", lty = 2)
text(optimal$specificity, optimal$sensitivity,
     labels = sprintf("Threshold %.3f", optimal$threshold), pos = 2, col = "red")
cat("AUC:", as.numeric(auc(roc_curve)), "\n")

# --- 4.8 ROC animation -------------------------------------------------------
predicted_probs <- logit_model$fitted.values
thresholds <- sort(unique(predicted_probs), decreasing = TRUE)

tpr <- numeric(length(thresholds))
fpr <- numeric(length(thresholds))

for (i in seq_along(thresholds)) {
  preds <- as.integer(predicted_probs >= thresholds[i])
  cm <- table(Predicted = preds, Actual = train_set$Attrition_bin)
  if (all(dim(cm) == 2)) {
    tpr[i] <- cm["1", "1"] / (cm["1", "1"] + cm["0", "1"])
    fpr[i] <- cm["1", "0"] / (cm["1", "0"] + cm["0", "0"])
  }
}

roc_df <- data.frame(Threshold = thresholds, TPR = tpr, FPR = fpr)

ggplot(roc_df, aes(x = FPR, y = TPR)) +
  geom_line(color = "steelblue", linewidth = 1) +
  geom_point(size = 1.5, color = "tomato") +
  geom_abline(intercept = 0, slope = 1, linetype = "dashed", color = "grey50") +
  labs(title = "ROC Curve — Logistic Regression",
       x = "False Positive Rate (1 - Specificity)",
       y = "True Positive Rate (Sensitivity)") +
  theme_minimal()

# --- 4.9 Likelihood-ratio test ------------------------------------------------
LR <- logit_model$null.deviance - logit_model$deviance
p_value_LR <- pchisq(LR, df = length(coef(logit_model)), lower.tail = FALSE)
cat("Likelihood-Ratio test p-value:", p_value_LR, "\n")

# ==============================================================================
# 5. DISCRIMINANT ANALYSIS (LDA / QDA)
# ==============================================================================

# --- 5.1 Balance the dataset via under-sampling ------------------------------
set.seed(1350)
df_balanced <- ovun.sample(Attrition_bin ~ ., data = df_regression,
                           method = "under", seed = 58, N = 500)$data
table(df_balanced$Attrition_bin)

set.seed(15)
bal_idx   <- createDataPartition(df_balanced$Attrition_bin, p = 0.80, list = FALSE)
bal_train <- df_balanced[bal_idx, ]
bal_test  <- df_balanced[-bal_idx, ]

# --- 5.2 LDA -----------------------------------------------------------------
lda_model <- lda(Attrition_bin ~ ., data = bal_train, CV = FALSE)
print(lda_model)
plot(lda_model, dimen = 1, type = "b")

lda_preds <- predict(lda_model, bal_train)$class
tab_lda   <- table(Actual = bal_train$Attrition_bin, Predicted = lda_preds)
cat("LDA accuracy:", sum(diag(tab_lda)) / nrow(bal_train) * 100, "%\n")

partimat(as.factor(Attrition_bin) ~ Age + DistanceFromHome +
           EnvironmentSatisfaction + JobSatisfaction +
           NumCompaniesWorked + RelationshipSatisfaction + log_MonthlyIncome,
         data = bal_train, method = "lda")

# --- 5.3 QDA -----------------------------------------------------------------
qda_model <- qda(Attrition_bin ~ ., data = bal_train, CV = FALSE)
print(qda_model)

qda_preds <- predict(qda_model, bal_train)$class
tab_qda   <- table(Actual = bal_train$Attrition_bin, Predicted = qda_preds)
cat("QDA accuracy:", sum(diag(tab_qda)) / nrow(bal_train) * 100, "%\n")

partimat(as.factor(Attrition_bin) ~ Age + DistanceFromHome +
           EnvironmentSatisfaction + JobSatisfaction +
           NumCompaniesWorked + RelationshipSatisfaction + log_MonthlyIncome,
         data = bal_train, method = "qda")

# --- 5.4 ROC comparison: Logistic vs LDA vs QDA ------------------------------
roc_lda <- roc(bal_train$Attrition_bin, predict(lda_model, bal_train)$posterior[, "0"])
roc_qda <- roc(bal_train$Attrition_bin, predict(qda_model, bal_train)$posterior[, "0"])

par(pty = "s")
plot(roc_lda, col = "blue", main = "ROC Comparison — Logistic vs LDA vs QDA")
lines(roc_qda, col = "green")
lines(roc_curve, col = "red")
legend("bottomright",
       legend = c(paste0("LDA (AUC = ", round(auc(roc_lda), 3), ")"),
                  paste0("QDA (AUC = ", round(auc(roc_qda), 3), ")"),
                  paste0("Logistic (AUC = ", round(auc(roc_curve), 3), ")")),
       col = c("blue", "green", "red"), lwd = 2)

# ==============================================================================
# 6. PRINCIPAL COMPONENT ANALYSIS (PCA)
# ==============================================================================

pca_result <- princomp(df_regression, cor = TRUE, scores = TRUE)
print(summary(pca_result), loading = TRUE)
fviz_eig(pca_result)

pca_scores <- pca_result$scores

# 2D score plot
plot(pca_scores[, 1], pca_scores[, 2],
     pch = 16, col = ifelse(df_regression$Attrition_bin == 1, "tomato", "steelblue"),
     xlab = "PC1", ylab = "PC2", main = "PCA — Score Plot (PC1 vs PC2)")
legend("topright", legend = c("No Attrition", "Attrition"),
       col = c("steelblue", "tomato"), pch = 16)
abline(h = 0, v = 0, lty = 2, col = "grey50")

# Threshold analysis on PC2
threshold_pc2 <- -1

above <- pca_scores[, 2] > threshold_pc2
pct_attr_above <- mean(df_regression$Attrition_bin[above] == 1) * 100
pct_attr_below <- mean(df_regression$Attrition_bin[!above] == 1) * 100

cat(sprintf("PC2 > %d: %.1f%% attrition (%d obs)\n",
            threshold_pc2, pct_attr_above, sum(above)))
cat(sprintf("PC2 <= %d: %.1f%% attrition (%d obs)\n",
            threshold_pc2, pct_attr_below, sum(!above)))

# ==============================================================================
# 7. CLUSTERING — Attrition cases only
# ==============================================================================

# Subset to attrition = 1 and remove binary flags
df_cluster <- df_regression %>%
  filter(Attrition_bin == 1) %>%
  select(-Attrition_bin, -OverTime_yes, -Relationship, -Male, -Travel)

# --- 7.1 Hierarchical clustering (Canberra + Complete) ------------------------
d_canberra <- dist(df_cluster, method = "canberra")
hc_complete <- hclust(d_canberra, method = "complete")
plot(hc_complete, cex = 0.5, main = "Dendrogram — Canberra / Complete")
rect.hclust(hc_complete, k = 2)

# Aggregation distance plot
matplot((nrow(df_cluster) - 1):1, round(hc_complete$height, 2),
        type = "p", pch = 21, col = "steelblue4",
        xlab = "Observations", ylab = "Aggregation Distance",
        main = "Aggregation Distance")

# Optimal number of clusters
nb_result <- NbClust(df_cluster, distance = "canberra", min.nc = 2, max.nc = 7,
                     method = "complete", index = "all")

sil_values <- nb_result$All.index[, "Silhouette"]
plot(2:7, sil_values, type = "l", col = "steelblue", lwd = 2,
     xlab = "Number of Clusters", ylab = "Silhouette",
     main = "Silhouette vs Number of Clusters")

# --- 7.2 Hierarchical clustering with Ward -----------------------------------
d_euclidean <- dist(df_cluster, method = "euclidean")
hc_ward <- hclust(d_euclidean, method = "ward.D2")
plot(hc_ward, cex = 0.5, main = "Dendrogram — Euclidean / Ward")
rect.hclust(hc_ward, k = 4)

# ANOVA on Ward clusters
ward_groups <- cutree(hc_ward, k = 4)
df_anova <- data.frame(df_cluster, group = as.factor(ward_groups))

for (var in c("Age", "JobLevel", "NumCompaniesWorked",
              "YearsInCurrentRole", "YearsWithCurrManager")) {
  cat("\n--- ANOVA:", var, "---\n")
  print(summary(aov(as.formula(paste(var, "~ group")), data = df_anova)))
}

# --- 7.3 Cluster profiling (Canberra / Complete, k = 2) ----------------------
groups_2 <- cutree(hc_complete, k = 2)
for (g in 1:2) {
  cat(sprintf("\n--- Group %d (n = %d) ---\n", g, sum(groups_2 == g)))
  print(summary(df_cluster[groups_2 == g, ]))
}

# --- 7.4 PAM -----------------------------------------------------------------
pam_result <- pam(df_cluster, 2)
plot(silhouette(pam_result), main = "PAM — k = 2")

for (k in 2:7) {
  plot(silhouette(pam(df_cluster, k = k)),
       main = paste("PAM Silhouette — k =", k), do.n.k = FALSE)
}

# --- 7.5 K-Means -------------------------------------------------------------
set.seed(42)
km_fit <- kmeans(df_cluster, centers = 2, nstart = 10000)
fviz_cluster(km_fit, df_cluster, main = "K-Means — k = 2")
aggregate(df_cluster, by = list(Cluster = km_fit$cluster), mean)

# Selezione variabili chiave per clustering raffinato
df_km_key <- df_cluster %>%
  select(Age, JobLevel, NumCompaniesWorked, YearsInCurrentRole,
         YearsWithCurrManager, log_MonthlyIncome)

km_fit_key <- kmeans(df_km_key, centers = 2, nstart = 10000)
fviz_cluster(km_fit_key, df_km_key, main = "K-Means — Variabili Chiave")

cat("\nCentroidi K-Means (variabili chiave):\n")
print(aggregate(df_km_key, by = list(Cluster = km_fit_key$cluster), mean))

# Elbow analysis: F-statistic and R² across cluster counts
n_obs <- nrow(df_cluster)
f_stat <- r_sq <- p_val <- numeric(10)

for (nc in 2:10) {
  fit <- kmeans(df_cluster, centers = nc, nstart = 1000)
  f_stat[nc] <- (fit$betweenss / (nc - 1)) / (fit$tot.withinss / (n_obs - nc - 1))
  r_sq[nc]   <- fit$betweenss / fit$totss
  p_val[nc]  <- 1 - pf(f_stat[nc], nc - 1, n_obs - nc - 1)
}

par(mfrow = c(1, 2))
plot(2:10, diff(r_sq[-1]),  type = "b", pch = 16, col = "steelblue",
     xlab = "k", ylab = "Delta R²", main = "Elbow Plot — R²")
plot(2:10, diff(f_stat[-1]), type = "b", pch = 16, col = "tomato",
     xlab = "k", ylab = "Delta F", main = "Elbow Plot — F-statistic")
par(mfrow = c(1, 1))

cat("\n========== ANALISI COMPLETATA ==========")
