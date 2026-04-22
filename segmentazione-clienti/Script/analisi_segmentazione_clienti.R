# ==============================================================================
# Customer Segmentation — PAM Cluster Analysis on Sales Data
# ==============================================================================
# Dataset: 2,999 transactions (01/01/2018 – 28/04/2019)
# Objective: Identify customer segments via unsupervised clustering to support
#            targeted marketing strategies.
# Method: PAM (Partitioning Around Medoids) with Manhattan distance, k = 3
# ==============================================================================

# --- Libraries ----------------------------------------------------------------
library(openxlsx)
library(dplyr)
library(ggplot2)
library(ggcorrplot)
library(factoextra)
library(cluster)

# --- Configuration ------------------------------------------------------------
set.seed(123)
CLUSTERING_VARS <- c("Net.Sales", "Discounts", "Returned.Item.Quantity",
                      "Ordered.Item.Quantity")
K_OPTIMAL <- 3

# ==============================================================================
# 1. DATA LOADING
# ==============================================================================
dataset <- read.xlsx("dati_segmentazione_clienti.xlsx")

cat("Dataset dimensions:", nrow(dataset), "x", ncol(dataset), "\n")
str(dataset)
summary(dataset)

# ==============================================================================
# 2. DATA QUALITY & PREPROCESSING
# ==============================================================================

# 2.1 Convert negative values to absolute (Discounts, Returns, etc.)
numeric_cols <- c("Gross.Sales", "Discounts", "Returns", "Net.Sales",
                  "Taxes", "Total.Sales", "Returned.Item.Quantity",
                  "Net.Quantity", "Ordered.Item.Quantity")
dataset[numeric_cols] <- abs(dataset[numeric_cols])

# 2.2 Check for duplicates and missing values
cat("\nDuplicated rows:", sum(duplicated(dataset)), "\n")
cat("Missing values per column:\n")
print(colSums(is.na(dataset)))

# 2.3 Filter only consistent records: Gross.Sales - Discounts == Net.Sales
df <- dataset[dataset$Gross.Sales - dataset$Discounts == dataset$Net.Sales, ]
cat("\nRecords after consistency filter:", nrow(df),
    "(removed:", nrow(dataset) - nrow(df), ")\n")

# 2.4 Recalculate total sales correctly
df$Total.Sales.Correct <- df$Net.Sales + df$Taxes

# 2.5 Remove zero-value rows (Net.Sales == 0 AND no returns)
df <- df %>%
  filter(!(Net.Sales == 0 & Returned.Item.Quantity == 0))

# 2.6 Drop redundant columns
df <- df %>% select(-Total.Sales, -Returns)

cat("Final dataset:", nrow(df), "observations\n")

# ==============================================================================
# 3. EXPLORATORY DATA ANALYSIS
# ==============================================================================

# 3.1 Correlation matrix
numeric_data <- df %>% select(where(is.numeric))
cor_matrix <- cor(numeric_data, use = "complete.obs")

ggcorrplot(cor_matrix,
           method = "square", type = "lower",
           lab = TRUE, lab_size = 3,
           colors = c("#2166AC", "white", "#B2182B")) +
  ggtitle("Correlation Matrix") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# 3.2 Boxplot of key monetary variables
df_long <- df %>%
  select(Gross.Sales, Net.Sales, Discounts) %>%
  tidyr::pivot_longer(everything(), names_to = "Variable", values_to = "Value")

ggplot(df_long, aes(x = Variable, y = Value, fill = Variable)) +
  geom_boxplot(alpha = 0.7, show.legend = FALSE) +
  scale_fill_manual(values = c("#6BAED6", "#2171B5", "#CB181D")) +
  labs(title = "Distribution of Monetary Variables",
       y = "Value", x = NULL) +
  theme_minimal()

# ==============================================================================
# 4. CLUSTERING — PAM (Partitioning Around Medoids)
# ==============================================================================

# 4.1 Prepare and standardize clustering variables
data_clust <- df[, CLUSTERING_VARS]
data_clust_scaled <- as.data.frame(scale(data_clust))

# 4.2 Optimal k — Elbow Method (Manhattan distance)
dist_manhattan <- dist(data_clust_scaled, method = "manhattan")

fviz_nbclust(data_clust_scaled, FUN = hcut,
             method = "wss", diss = dist_manhattan) +
  ggtitle("Elbow Method (Manhattan Distance)") +
  theme_minimal()

# 4.3 Optimal k — Silhouette Method
fviz_nbclust(data_clust_scaled, FUN = hcut,
             method = "silhouette", diss = dist_manhattan) +
  ggtitle("Silhouette Method (Manhattan Distance)") +
  theme_minimal()

# 4.4 Fit PAM model
pam_model <- pam(dist_manhattan, k = K_OPTIMAL, diss = TRUE)

# 4.5 Silhouette analysis
sil <- silhouette(pam_model$clustering, dist_manhattan)
cat("\nAverage Silhouette Width:", round(mean(sil[, "sil_width"]), 3), "\n")
fviz_silhouette(sil) +
  ggtitle(paste0("Silhouette Plot (k = ", K_OPTIMAL, ")")) +
  theme_minimal()

# 4.6 Assign clusters to original data
df$Cluster <- as.factor(pam_model$clustering)
cat("\nCluster sizes:\n")
print(table(df$Cluster))

# ==============================================================================
# 5. CLUSTER PROFILING
# ==============================================================================

# 5.1 Medoids (representative observations)
cat("\nMedoids (standardized values):\n")
print(data_clust_scaled[pam_model$medoids, ])

# 5.2 Centroids (cluster means on original scale)
centroids <- df %>%
  group_by(Cluster) %>%
  summarise(across(all_of(CLUSTERING_VARS), mean), .groups = "drop")
cat("\nCentroids (original scale):\n")
print(as.data.frame(centroids))

# 5.3 Descriptive statistics per cluster
cluster_stats <- df %>%
  group_by(Cluster) %>%
  summarise(
    n           = n(),
    across(all_of(CLUSTERING_VARS),
           list(mean = mean, median = median, sd = sd, min = min, max = max),
           .names = "{.col}_{.fn}"),
    .groups = "drop"
  )
print(as.data.frame(cluster_stats))

# ==============================================================================
# 6. CLUSTER VISUALIZATION
# ==============================================================================

# 6.1 Cluster plot (PCA-reduced 2D)
fviz_cluster(pam_model, data = data_clust_scaled,
             palette = c("#E64B35", "#4DBBD5", "#00A087"),
             geom = "point", pointsize = 2, alpha = 0.6,
             ellipse.type = "convex",
             main = "PAM Clustering (k = 3) — PCA Projection") +
  theme_minimal()

# 6.2 Boxplot of Net Sales by Cluster
ggplot(df, aes(x = Cluster, y = Net.Sales, fill = Cluster)) +
  geom_boxplot(alpha = 0.7, show.legend = FALSE) +
  scale_fill_manual(values = c("#E64B35", "#4DBBD5", "#00A087")) +
  labs(title = "Net Sales Distribution by Cluster",
       y = "Net Sales", x = "Cluster") +
  theme_minimal()

# 6.3 Boxplot of Discounts by Cluster
ggplot(df, aes(x = Cluster, y = Discounts, fill = Cluster)) +
  geom_boxplot(alpha = 0.7, show.legend = FALSE) +
  scale_fill_manual(values = c("#E64B35", "#4DBBD5", "#00A087")) +
  labs(title = "Discounts Distribution by Cluster",
       y = "Discounts", x = "Cluster") +
  theme_minimal()

# ==============================================================================
# 7. PRODUCT ANALYSIS WITHIN CLUSTERS
# ==============================================================================

# 7.1 Product Type frequency per cluster
freq_type <- df %>%
  count(Cluster, Product.Type, name = "Frequency") %>%
  arrange(Cluster, desc(Frequency))

ggplot(freq_type, aes(x = reorder(Product.Type, -Frequency),
                       y = Frequency, fill = Cluster)) +
  geom_bar(stat = "identity", position = "dodge") +
  scale_fill_manual(values = c("#E64B35", "#4DBBD5", "#00A087")) +
  labs(title = "Product Type Distribution by Cluster",
       x = "Product Type", y = "Frequency") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# 7.2 Product Title frequency per cluster
freq_title <- df %>%
  count(Cluster, Product.Title, name = "Frequency") %>%
  arrange(Cluster, desc(Frequency))

ggplot(freq_title, aes(x = reorder(Product.Title, -Frequency),
                        y = Frequency, fill = Cluster)) +
  geom_bar(stat = "identity", position = "dodge") +
  scale_fill_manual(values = c("#E64B35", "#4DBBD5", "#00A087")) +
  labs(title = "Product Title Distribution by Cluster",
       x = "Product Title", y = "Frequency") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# 7.3 Net Sales by Product Type, colored by Cluster
ggplot(df, aes(x = Product.Type, y = Net.Sales, color = Cluster)) +
  geom_jitter(width = 0.2, alpha = 0.6, size = 2) +
  scale_color_manual(values = c("#E64B35", "#4DBBD5", "#00A087")) +
  labs(title = "Net Sales by Product Type",
       x = "Product Type", y = "Net Sales") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

cat("\n--- Analysis complete ---\n")
