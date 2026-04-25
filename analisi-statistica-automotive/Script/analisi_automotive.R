# =============================================================================
# ANALISI STATISTICA DEL MERCATO AUTOMOTIVE
# =============================================================================
# Analisi esplorativa, clustering, PCA e modelli predittivi (regressione e
# classificazione) su un dataset di automobili. L'obiettivo principale è
# prevedere il prezzo consigliato (MSRP) e classificare i veicoli in fasce
# di prezzo tramite diversi algoritmi di machine learning.
# =============================================================================

# --- Librerie ----------------------------------------------------------------
library(tidyverse)
library(readr)
library(corrplot)
library(ggplot2)
library(factoextra)
library(gridExtra)
library(cluster)
library(rgl)
library(caret)
library(car)
library(olsrr)
library(lmtest)
library(rpart)
library(rpart.plot)
library(randomForest)
library(neuralnet)
library(nnet)
library(MASS)
library(pROC)
library(klaR)

# =============================================================================
# 1. DATA CLEANING
# =============================================================================

data <- read_csv("data.csv")

# Standardizzo i nomi delle colonne
names(data) <- gsub(" ", ".", names(data))

# Rimozione outlier e valori non validi
data <- data %>%
  filter(MSRP > 2000, MSRP <= 300000,
         highway.MPG <= 300,
         Market.Category != "N/A")

# Rimozione valori mancanti e duplicati
data <- data %>%
  na.omit() %>%
  distinct()

# --- Raggruppamento tipologie di carburante ----------------------------------
fuel_mapping <- c(
  "flex-fuel \\(premium unleaded recommended/E85\\)" = "unleaded",
  "flex-fuel \\(premium unleaded required/E85\\)"    = "unleaded",
  "flex-fuel \\(unleaded/E85\\)"                     = "unleaded",
  "premium unleaded \\(required\\)"                  = "unleaded",
  "regular unleaded"                                 = "unleaded",
  "premium unleaded \\(recommended\\)"               = "unleaded",
  "flex-fuel \\(unleaded/natural gas\\)"              = "unleaded"
)
for (pattern in names(fuel_mapping)) {
  data$Engine.Fuel.Type <- gsub(pattern, fuel_mapping[pattern], data$Engine.Fuel.Type)
}

# --- Raggruppamento trasmissione e trazione ----------------------------------
data$Transmission.Type <- gsub("DIRECT_DRIVE|UNKNOWN", "AUTOMATED_MANUAL", data$Transmission.Type)
data$Driven.Wheels     <- gsub("four wheel drive", "all wheel drive", data$Driven.Wheels)

# --- Parsing delle categorie di mercato --------------------------------------
categorie_split <- strsplit(data$Market.Category, ",")
max_cat <- max(sapply(categorie_split, length))
cat_matrix <- matrix("", nrow = nrow(data), ncol = max_cat)
for (i in seq_along(categorie_split)) {
  cat_matrix[i, seq_along(categorie_split[[i]])] <- trimws(categorie_split[[i]])
}
cat_df <- as.data.frame(cat_matrix, stringsAsFactors = FALSE)
colnames(cat_df) <- paste0("Category_", seq_len(max_cat))
data <- cbind(data, cat_df)

# Conteggio categorie principali
categorie_target <- c("Factory Tuner", "Luxury", "High-Performance", "Performance",
                      "Flex Fuel", "Hatchback", "Hybrid", "Diesel", "Exotic", "Crossover")
conteggio_categorie <- sapply(categorie_target, function(cat) {
  sum(cat_df == cat)
})
cat_summary <- data.frame(Categoria = names(conteggio_categorie),
                          Conteggio = conteggio_categorie, row.names = NULL)
print(cat_summary)

# =============================================================================
# 2. ANALISI ESPLORATIVA (EDA)
# =============================================================================

# --- Matrice di correlazione -------------------------------------------------
vars_corr <- data %>%
  select(Year, Engine.HP, Engine.Cylinders, Number.of.Doors,
         highway.MPG, city.mpg, Popularity, MSRP) %>%
  mutate(Vehicle.Size = as.integer(factor(data$Vehicle.Size,
                                          levels = c("Compact", "Midsize", "Large"))))

correlation_matrix <- cor(vars_corr)
corrplot(correlation_matrix, method = "square",
         title = "Matrice di Correlazione", mar = c(0, 0, 1, 0))

# --- Statistiche descrittive per dimensione veicolo -------------------------
variabili_interesse <- c("Engine.HP", "Engine.Cylinders", "Number.of.Doors",
                         "MSRP", "city.mpg", "highway.MPG")
summary_by_size <- data %>%
  group_by(Vehicle.Size) %>%
  summarize(across(all_of(variabili_interesse),
                   list(media = mean, mediana = median, dev_std = sd)),
            .groups = "drop")
print(summary_by_size)

# --- Boxplot esplorativi -----------------------------------------------------
par(mfrow = c(2, 3))
boxplot(data$Year,           main = "Anno")
boxplot(data$Engine.HP,      main = "Cavalli")
boxplot(data$MSRP,           main = "MSRP")
boxplot(data$highway.MPG,    main = "Highway MPG")
boxplot(data$city.mpg,       main = "City MPG")
boxplot(data$Engine.Cylinders, main = "Cilindri")
par(mfrow = c(1, 1))

# --- Cilindri vs consumo autostradale ----------------------------------------
corr_df <- data.frame(
  Cilindri = factor(data$Engine.Cylinders),
  HP       = data$Engine.HP,
  Highway  = data$highway.MPG,
  City     = data$city.mpg
)

ggplot(corr_df, aes(x = Cilindri, y = Highway, fill = Cilindri)) +
  geom_boxplot() +
  labs(title = "Consumi in autostrada per numero di cilindri",
       x = "Cilindri", y = "Highway MPG") +
  theme_minimal()

# --- Cavalli vs consumo in citta' --------------------------------------------
fasce_cavalli <- c(0, 180, 250, 350, Inf)
corr_df$Fascia.HP <- cut(corr_df$HP, breaks = fasce_cavalli,
                         labels = c("0-180", "181-250", "251-350", "351+"))

ggplot(corr_df, aes(x = Fascia.HP, y = City, fill = Fascia.HP)) +
  geom_boxplot() +
  labs(title = "Consumo in citta' per fascia di potenza",
       x = "Cavalli (HP)", y = "City MPG") +
  theme_minimal()

# --- Vehicle.Size vs variabili chiave ----------------------------------------
size_plots <- list(
  ggplot(data, aes(x = Vehicle.Size, y = highway.MPG, fill = Vehicle.Size)) +
    geom_boxplot() + labs(title = "Highway MPG per dimensione") + theme_minimal(),
  ggplot(data, aes(x = Vehicle.Size, y = city.mpg, fill = Vehicle.Size)) +
    geom_boxplot() + labs(title = "City MPG per dimensione") + theme_minimal(),
  ggplot(data, aes(x = Vehicle.Size, y = Engine.HP, fill = Vehicle.Size)) +
    geom_boxplot() + labs(title = "Cavalli per dimensione") + theme_minimal(),
  ggplot(data, aes(x = Vehicle.Size, y = MSRP, fill = Vehicle.Size)) +
    geom_boxplot() + labs(title = "MSRP per dimensione") + theme_minimal()
)
grid.arrange(grobs = size_plots, ncol = 2)

# --- Distribuzione temporale -------------------------------------------------
ggplot(data, aes(x = Year)) +
  geom_bar(fill = "skyblue") +
  labs(title = "Distribuzione delle auto nel tempo", x = "Anno", y = "Conteggio") +
  theme_minimal()

# --- Distribuzione cavalli per fascia ----------------------------------------
ggplot(corr_df, aes(x = Fascia.HP)) +
  geom_bar(fill = "skyblue") +
  labs(title = "Distribuzione per fascia di potenza", x = "Cavalli", y = "Conteggio") +
  theme_minimal()

# --- Distribuzione cilindri --------------------------------------------------
ggplot(data, aes(x = factor(Engine.Cylinders))) +
  geom_bar(fill = "skyblue") +
  labs(title = "Distribuzione dei cilindri", x = "N. cilindri", y = "Conteggio") +
  theme_minimal()

# --- Conteggio trasmissione, trazione, alimentazione -------------------------
par(mfrow = c(1, 3))
barplot(table(data$Transmission.Type), main = "Tipo di Trasmissione",
        col = "skyblue", las = 2, cex.names = 0.7)
barplot(table(data$Driven.Wheels), main = "Tipo di Trazione",
        col = "skyblue", las = 2, cex.names = 0.7)
barplot(table(data$Engine.Fuel.Type), main = "Tipo di Carburante",
        col = "skyblue", las = 2, cex.names = 0.7)
par(mfrow = c(1, 1))

# --- Tipologie di carrozzeria ------------------------------------------------
conteggio_style <- data %>% count(Vehicle.Style, sort = TRUE)
ggplot(conteggio_style, aes(x = reorder(Vehicle.Style, -n), y = n)) +
  geom_bar(stat = "identity", fill = "skyblue") +
  labs(title = "Tipologie di carrozzerie", x = "Carrozzeria", y = "Conteggio") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# --- Conteggio categorie di mercato ------------------------------------------
barplot(cat_summary$Conteggio, names.arg = cat_summary$Categoria,
        xlab = "Categorie", ylab = "Conteggio", col = "skyblue",
        main = "Conteggio delle categorie", las = 2, cex.names = 0.7)

# --- Distribuzione MSRP per fasce di prezzo ----------------------------------
fasce_prezzo <- c(0, 15000, 30000, 50000, Inf)
data$Fascia.Prezzo <- cut(data$MSRP, breaks = fasce_prezzo,
                          labels = c("0-15k", "15k-30k", "30k-50k", "50k+"))

ggplot(data, aes(x = Fascia.Prezzo)) +
  geom_bar(fill = "skyblue") +
  labs(title = "Distribuzione per fasce di prezzo",
       x = "Fascia di prezzo", y = "Conteggio") +
  theme_minimal()

# =============================================================================
# 3. PCA - ANALISI DELLE COMPONENTI PRINCIPALI
# =============================================================================

pca_vars <- data %>%
  select(Year, Engine.HP, Engine.Cylinders, Transmission.Type,
         Number.of.Doors, highway.MPG, city.mpg, Popularity) %>%
  mutate(
    Vehicle.Size     = as.numeric(factor(data$Vehicle.Size,
                                        levels = c("Compact", "Midsize", "Large"))),
    Transmission.Type = as.numeric(factor(Transmission.Type))
  )

pca_result <- princomp(pca_vars, cor = TRUE, scores = TRUE)
print(summary(pca_result), loading = TRUE)
fviz_eig(pca_result, main = "Scree Plot - Varianza Spiegata")

fviz_pca_var(pca_result, col.var = "cos2",
             gradient.cols = c("black", "orange", "green"),
             repel = TRUE, title = "Contributo delle variabili alle componenti")

# --- Visualizzazione 2D -----------------------------------------------------
pca_scores <- as.data.frame(pca_result$scores)
pca_scores$Fascia.Prezzo <- data$Fascia.Prezzo

ggplot(pca_scores, aes(x = Comp.1, y = Comp.2, color = Fascia.Prezzo)) +
  geom_point(alpha = 0.5, size = 1.5) +
  labs(title = "PCA - Prime due componenti per fascia di prezzo",
       x = "Componente 1", y = "Componente 2") +
  theme_minimal()

# --- Visualizzazione 3D (interattiva) ----------------------------------------
fascia_colors <- c("0-15k" = "steelblue2", "15k-30k" = "purple",
                   "30k-50k" = "red4", "50k+" = "green3")
plot3d(pca_scores$Comp.1, pca_scores$Comp.2, pca_scores$Comp.3,
       col = fascia_colors[as.character(pca_scores$Fascia.Prezzo)],
       size = 5, xlab = "PC1", ylab = "PC2", zlab = "PC3",
       main = "PCA 3D per fascia di prezzo")

# --- Centroidi per fascia di prezzo ------------------------------------------
centroidi_pca <- pca_scores %>%
  group_by(Fascia.Prezzo) %>%
  summarize(PC1_media = mean(Comp.1),
            PC2_media = mean(Comp.2),
            PC3_media = mean(Comp.3),
            .groups = "drop")
print(centroidi_pca)

# =============================================================================
# 4. CLUSTERING
# =============================================================================

# Preparo il dataset per il clustering (variabili numeriche + encoding manuale)
variabili_numeriche <- data %>%
  select(Year, Engine.HP, Engine.Cylinders, Number.of.Doors,
         city.mpg, highway.MPG, Popularity, MSRP)

variabili_qualitative <- data %>%
  select(Engine.Fuel.Type, Transmission.Type, Driven.Wheels,
         Market.Category, Vehicle.Size, Vehicle.Style)

cluster_df <- variabili_numeriche %>%
  mutate(
    Transmission = as.numeric(factor(data$Transmission.Type,
                                     levels = c("MANUAL", "AUTOMATIC", "AUTOMATED_MANUAL"))),
    Trazione     = as.numeric(factor(data$Driven.Wheels,
                                     levels = c("front wheel drive", "rear wheel drive", "all wheel drive"))),
    Dimensione   = as.numeric(factor(data$Vehicle.Size,
                                     levels = c("Compact", "Midsize", "Large")))
  )

# --- 4a. K-Means -------------------------------------------------------------
wcss <- numeric(10)
for (k in 1:10) {
  wcss[k] <- kmeans(cluster_df, centers = k, nstart = 25)$tot.withinss
}

ggplot(data.frame(k = 1:10, WCSS = wcss), aes(x = k, y = WCSS)) +
  geom_line(color = "blue") +
  geom_point(color = "red", size = 2) +
  labs(title = "Metodo del gomito (Elbow Method)",
       x = "Numero di cluster (k)", y = "WCSS") +
  scale_x_continuous(breaks = 1:10) +
  theme_minimal()

set.seed(6)
kmeans_fit <- kmeans(cluster_df, centers = 2, nstart = 10000)
fviz_cluster(kmeans_fit, cluster_df,
             main = "K-Means Clustering (k = 2)")

cat("\nCentroidi K-Means:\n")
print(aggregate(cluster_df, by = list(Cluster = kmeans_fit$cluster), mean))

# --- 4b. Clustering Gerarchico -----------------------------------------------
d_euclidea <- dist(variabili_numeriche, method = "euclidean")
dendro <- hclust(d_euclidea)
plot(dendro, labels = FALSE, main = "Dendrogramma - Clustering Gerarchico")
abline(h = 200000, lty = "dashed", col = "red")

gruppi_hier <- cutree(dendro, h = 200000)
rect.hclust(dendro, k = 2)

cluster_df$Gruppo <- gruppi_hier
centroidi_hier <- by(cluster_df %>% select(-Gruppo), gruppi_hier, colMeans)
cat("\nCentroidi Gerarchici:\n")
print(centroidi_hier)

# Silhouette
pr_pam <- pam(cluster_df %>% select(-Gruppo), 2)
plot(silhouette(pr_pam), main = "Silhouette Plot")

# Top 10 marchi per MSRP medio
top_brands <- data %>%
  group_by(Make) %>%
  summarize(MSRP_Medio = mean(MSRP, na.rm = TRUE), .groups = "drop") %>%
  arrange(desc(MSRP_Medio)) %>%
  slice_head(n = 10)
print(top_brands)

# =============================================================================
# 5. PREDIZIONE MSRP (REGRESSIONE)
# =============================================================================

# --- Preparazione dataset per la regressione ---------------------------------
regression_df <- variabili_qualitative %>%
  transmute(
    Suv_4dr          = as.integer(grepl("4dr SUV", Vehicle.Style)),
    Sedan            = as.integer(grepl("Sedan", Vehicle.Style)),
    Coupe            = as.integer(grepl("Coupe", Vehicle.Style)),
    Luxury           = as.integer(grepl("\\bLuxury\\b", Market.Category)),
    Crossover        = as.integer(grepl("\\bCrossover\\b", Market.Category)),
    Performance      = as.integer(grepl("\\bPerformance\\b", Market.Category)),
    High.Performance = as.integer(grepl("\\bHigh.Performance\\b", Market.Category)),
    Automatic        = as.integer(grepl("AUTOMATIC", Transmission.Type)),
    Front_WD         = as.integer(grepl("front wheel drive", Driven.Wheels)),
    All_WD           = as.integer(grepl("all wheel drive", Driven.Wheels)),
    Compact          = as.integer(grepl("Compact", Vehicle.Size)),
    Large            = as.integer(grepl("Large", Vehicle.Size))
  )
regression_df <- cbind(variabili_numeriche, regression_df)

# --- Train/Test split --------------------------------------------------------
set.seed(6)
train_idx <- createDataPartition(regression_df$MSRP, p = 0.8, list = FALSE)
train_data <- regression_df[train_idx, ]
test_data  <- regression_df[-train_idx, ]

# --- 5a. Regressione Lineare (OLS) -------------------------------------------
lm_model <- lm(MSRP ~ ., data = train_data)
cat("\n--- Regressione Lineare ---\n")
cat("VIF:\n")
print(vif(lm_model))
print(summary(lm_model))

lm_pred <- predict(lm_model, newdata = test_data)

# Diagnostica residui
e_lm <- lm_model$residuals
cat("Media residui:", round(mean(e_lm), 4), "\n")

ols_plot_resid_qq(lm_model)
ols_plot_resid_hist(lm_model)

cat("Test NCV (eteroschedasticita'):\n")
print(ncvTest(lm_model))

cat("Test autocorrelazione:\n")
print(ols_test_correlation(lm_model))

rmse_ols <- RMSE(lm_pred, test_data$MSRP)
cat("RMSE OLS:", rmse_ols, "\n")

# --- 5b. Regressione Lineare Scalata -----------------------------------------
data_std <- as.data.frame(scale(variabili_numeriche))
data_std <- cbind(data_std, regression_df[, (ncol(variabili_numeriche) + 1):ncol(regression_df)])

train_std <- data_std[train_idx, ]
test_std  <- data_std[-train_idx, ]

lm_scaled <- lm(MSRP ~ ., data = train_std)
cat("\n--- Regressione Lineare Scalata ---\n")
print(summary(lm_scaled))

# --- 5c. Regressione con Componenti Principali -------------------------------
pca_df <- data.frame(MSRP = data$MSRP,
                     PC1  = pca_result$scores[, 1],
                     PC2  = pca_result$scores[, 2],
                     PC3  = pca_result$scores[, 3])
lm_pca <- lm(MSRP ~ ., data = pca_df)
cat("\n--- Regressione con PCA ---\n")
print(summary(lm_pca))

# --- 5d. Decision Tree -------------------------------------------------------
tree_control <- rpart.control(cp = 0.01, maxdepth = 5, minsplit = 20)
tree_model <- rpart(MSRP ~ ., data = train_data, control = tree_control)

bestcp <- tree_model$cptable[which.min(tree_model$cptable[, "xerror"]), "CP"]
tree_pruned <- prune(tree_model, cp = bestcp)
rpart.plot(tree_pruned, main = "Decision Tree - MSRP")

tree_pred <- predict(tree_pruned, newdata = test_data)
rmse_tree <- RMSE(tree_pred, test_data$MSRP)
cat("RMSE Decision Tree:", rmse_tree, "\n")

# --- 5e. Random Forest -------------------------------------------------------
set.seed(6)
rf_model <- randomForest(MSRP ~ ., data = train_data, importance = TRUE)
varImpPlot(rf_model, main = "Importanza variabili - Random Forest")

rf_pred <- predict(rf_model, newdata = test_data)
rmse_rf <- RMSE(rf_pred, test_data$MSRP)
cat("RMSE Random Forest:", rmse_rf, "\n")
cat("R-squared RF:", rf_model$rsq[length(rf_model$rsq)], "\n")

# --- 5f. Rete Neurale --------------------------------------------------------
set.seed(6)
nn_model <- neuralnet(MSRP ~ ., data = train_data,
                      hidden = c(2, 1, 3),
                      linear.output = TRUE,
                      threshold = 0.01)

nn_pred <- compute(nn_model, test_data)
rmse_nn <- RMSE(nn_pred$net.result, test_data$MSRP)
cat("RMSE Neural Network:", rmse_nn, "\n")

# --- 5g. SVM (Lineare e Radiale) ---------------------------------------------
kfolds_reg <- createFolds(train_data$MSRP, k = 10)

svm_linear <- train(MSRP ~ ., data = train_data,
                    method = "svmLinear",
                    trControl = trainControl(method = "cv", indexOut = kfolds_reg))

svm_radial <- train(MSRP ~ ., data = train_data,
                    method = "svmRadial",
                    trControl = trainControl(method = "cv", indexOut = kfolds_reg))

svm_lin_pred <- predict(svm_linear, test_data)
svm_rad_pred <- predict(svm_radial, test_data)

rmse_svm_lin <- RMSE(svm_lin_pred, test_data$MSRP)
rmse_svm_rad <- RMSE(svm_rad_pred, test_data$MSRP)
cat("RMSE SVM Lineare:", rmse_svm_lin, "\n")
cat("RMSE SVM Radiale:", rmse_svm_rad, "\n")

# --- Riepilogo modelli di regressione ----------------------------------------
cat("\n========== CONFRONTO MODELLI DI REGRESSIONE ==========\n")
risultati_reg <- data.frame(
  Modello = c("OLS", "Decision Tree", "Random Forest",
              "Neural Network", "SVM Lineare", "SVM Radiale"),
  RMSE = c(rmse_ols, rmse_tree, rmse_rf,
           rmse_nn, rmse_svm_lin, rmse_svm_rad)
)
risultati_reg <- risultati_reg[order(risultati_reg$RMSE), ]
print(risultati_reg, row.names = FALSE)

# =============================================================================
# 6. CLASSIFICAZIONE PER FASCE DI PREZZO
# =============================================================================

# --- Preparazione dataset per classificazione --------------------------------
class_df <- regression_df
class_df$Fascia.Prezzo <- data$Fascia.Prezzo
class_df$MSRP <- NULL  # Rimuovo MSRP (target della regressione, non della classificazione)

set.seed(6)
train_idx_cls <- createDataPartition(class_df$Fascia.Prezzo, p = 0.8, list = FALSE)
train_cls <- class_df[train_idx_cls, ]
test_cls  <- class_df[-train_idx_cls, ]

# Funzione per calcolare l'accuratezza
calc_accuracy <- function(pred, actual) {
  sum(diag(table(pred, actual))) / length(actual) * 100
}

# --- 6a. Regressione Multinomiale --------------------------------------------
multinom_model <- multinom(Fascia.Prezzo ~ ., data = train_cls, trace = FALSE)
multinom_pred  <- predict(multinom_model, newdata = test_cls)
acc_multinom   <- calc_accuracy(multinom_pred, test_cls$Fascia.Prezzo)
cat("\nAccuratezza Multinomiale:", round(acc_multinom, 2), "%\n")

# --- 6b. LDA -----------------------------------------------------------------
lda_model <- lda(Fascia.Prezzo ~ ., data = train_cls)
lda_pred  <- predict(lda_model, newdata = test_cls)
acc_lda   <- calc_accuracy(lda_pred$class, test_cls$Fascia.Prezzo)
cat("Accuratezza LDA:", round(acc_lda, 2), "%\n")

plot(lda_model, dimen = 1, type = "b", main = "LDA - Discriminante 1")

# --- 6c. Decision Tree -------------------------------------------------------
tree_cls <- rpart(Fascia.Prezzo ~ ., data = train_cls,
                  control = rpart.control(cp = 0.01, maxdepth = 5, minsplit = 20))

bestcp_cls <- tree_cls$cptable[which.min(tree_cls$cptable[, "xerror"]), "CP"]
tree_cls_pruned <- prune(tree_cls, cp = bestcp_cls)
rpart.plot(tree_cls_pruned, main = "Decision Tree - Fasce di Prezzo")

tree_cls_pred <- predict(tree_cls_pruned, test_cls, type = "class")
acc_tree_cls  <- calc_accuracy(tree_cls_pred, test_cls$Fascia.Prezzo)
cat("Accuratezza Decision Tree:", round(acc_tree_cls, 2), "%\n")

# --- 6d. Random Forest -------------------------------------------------------
set.seed(6)
rf_cls <- randomForest(as.factor(Fascia.Prezzo) ~ ., data = train_cls,
                       ntree = 500, importance = TRUE)
varImpPlot(rf_cls, main = "Importanza variabili - RF Classificazione")

rf_cls_pred <- predict(rf_cls, newdata = test_cls)
acc_rf_cls  <- calc_accuracy(rf_cls_pred, test_cls$Fascia.Prezzo)
cat("Accuratezza Random Forest:", round(acc_rf_cls, 2), "%\n")

# --- 6e. SVM (Lineare) -------------------------------------------------------
kfolds_cls <- createFolds(train_cls$Fascia.Prezzo, k = 10)

svm_cls <- train(Fascia.Prezzo ~ ., data = train_cls,
                 method = "svmLinear",
                 trControl = trainControl(method = "cv", indexOut = kfolds_cls),
                 metric = "Accuracy")

svm_cls_pred <- predict(svm_cls, newdata = test_cls)
acc_svm_cls  <- calc_accuracy(svm_cls_pred, test_cls$Fascia.Prezzo)
cat("Accuratezza SVM:", round(acc_svm_cls, 2), "%\n")

# --- 6f. KNN -----------------------------------------------------------------
knn_model <- train(Fascia.Prezzo ~ ., data = train_cls,
                   method = "knn",
                   metric = "Accuracy",
                   tuneGrid = data.frame(k = 1:10),
                   trControl = trainControl(method = "cv", indexOut = kfolds_cls))
plot(knn_model, main = "KNN - Accuratezza per k")

knn_pred <- predict(knn_model, test_cls)
acc_knn  <- calc_accuracy(knn_pred, test_cls$Fascia.Prezzo)
cat("Accuratezza KNN:", round(acc_knn, 2), "%\n")

# --- Riepilogo modelli di classificazione ------------------------------------
cat("\n========== CONFRONTO MODELLI DI CLASSIFICAZIONE ==========\n")
risultati_cls <- data.frame(
  Modello = c("Multinomiale", "LDA", "Decision Tree",
              "Random Forest", "SVM Lineare", "KNN"),
  Accuratezza = c(acc_multinom, acc_lda, acc_tree_cls,
                  acc_rf_cls, acc_svm_cls, acc_knn)
)
risultati_cls <- risultati_cls[order(-risultati_cls$Accuratezza), ]
print(risultati_cls, row.names = FALSE)

cat("\n========== ANALISI COMPLETATA ==========\n")
