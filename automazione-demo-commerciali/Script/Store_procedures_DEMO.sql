-- ============================================================================
-- AUTOMAZIONE DEMO COMMERCIALI
-- ============================================================================
-- Stored procedures per la generazione e il mantenimento automatico di dati
-- demo realistici in ambienti di presentazione commerciale.
--
-- PROBLEMA: la preparazione manuale dei dati demo richiedeva 3-4 giorni per
-- ogni prospect, diventando un collo di bottiglia nel funnel di vendita.
--
-- SOLUZIONE: due stored procedure che alimentano automaticamente le dashboard
-- con dati contestualizzati, garantendo variazioni coerenti sia nel confronto
-- mese su mese (MoM) che anno su anno (YoY).
--
-- LOGICA DI VARIAZIONE:
--   MoM → copia i dati dal primo giorno di 2 mesi fa. Ogni mese attinge da
--          un periodo sorgente diverso, creando variazioni naturali tra mesi.
--   YoY → copia i dati dal primo giorno di 2 anni fa. Confrontando anno
--          corrente vs precedente, le basi diverse generano delta realistici.
-- ============================================================================

USE demo;


-- ----------------------------------------------------------------------------
-- 1. STRUTTURA TABELLA
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS Web_Matrici_Dati (
    Idx       BIGINT         PRIMARY KEY,
    IdMatrice INT            NOT NULL,
    IdCat     INT            NOT NULL,
    Dt        DATETIME       NOT NULL,
    Netto     DECIMAL(10,2),
    Iva       INT,
    FattIvato DECIMAL(10,2),
    Qta       INT,
    Lavorato  BIT,
    Dim       INT,
    IdUtente  VARCHAR(20),
    DtUpd     DATETIME
);


-- ----------------------------------------------------------------------------
-- 2. SP_GENERA_DATI_DEMO_GIORNALIERO
-- ----------------------------------------------------------------------------
-- Inserisce giornalmente una riga per ogni categoria (IdCat) della matrice
-- indicata, copiando i valori da un periodo storico di riferimento con una
-- variazione giornaliera casuale e controllata.
--
-- Parametri:
--   p_id_matrice       INT         – ID della matrice da alimentare
--   p_iva              INT         – aliquota IVA da applicare
--   p_tipologia        VARCHAR(3)  – 'MoM' (Mese vs Mese) | 'YoY' (Anno vs Anno)
--   p_variazione_pct   DECIMAL(5,2) – variazione massima in % rispetto al
--                                     valore seed (default consigliato: 5.00)
--
-- VARIAZIONE GIORNALIERA:
--   Ogni giorno i valori (Netto, FattIvato, Qta) vengono moltiplicati per un
--   fattore casuale compreso tra (1 - p_variazione_pct/100) e
--   (1 + p_variazione_pct/100). La distribuzione è uniforme e centrata sulla
--   media del seed, garantendo oscillazioni realistiche senza drift.
-- ----------------------------------------------------------------------------

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_genera_dati_demo_giornaliero$$

CREATE PROCEDURE sp_genera_dati_demo_giornaliero(
    IN p_id_matrice     INT,
    IN p_iva            INT,
    IN p_tipologia      VARCHAR(3),
    IN p_variazione_pct DECIMAL(5,2)
)
BEGIN
    DECLARE v_data_corrente    DATE DEFAULT CURDATE();
    DECLARE v_data_riferimento DATE;
    DECLARE v_var              DECIMAL(5,4);

    -- Variazione massima: default 5% se non specificata o 0
    IF p_variazione_pct IS NULL OR p_variazione_pct = 0 THEN
        SET p_variazione_pct = 5.00;
    END IF;

    -- Fattore di variazione: da -var a +var (es. da 0.95 a 1.05)
    SET v_var = p_variazione_pct / 100;

    -- Determina la data sorgente da cui copiare i dati storici
    IF p_tipologia = 'MoM' THEN
        SET v_data_riferimento = CAST(
            DATE_FORMAT(DATE_SUB(v_data_corrente, INTERVAL 2 MONTH), '%Y-%m-01') AS DATE
        );
    ELSE
        SET v_data_riferimento = CAST(
            DATE_FORMAT(DATE_SUB(v_data_corrente, INTERVAL 2 YEAR), '%Y-01-01') AS DATE
        );
    END IF;

    -- Inserimento con variazione casuale giornaliera per ogni categoria
    INSERT INTO Web_Matrici_Dati
        (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
    SELECT
        CAST(CONCAT(DATE_FORMAT(v_data_corrente, '%Y%m%d'), src.IdCat) AS UNSIGNED),
        p_id_matrice,
        src.IdCat,
        CAST(v_data_corrente AS DATETIME),
        ROUND(src.Netto     * (1 + (RAND() * 2 - 1) * v_var), 2),
        p_iva,
        ROUND(src.FattIvato * (1 + (RAND() * 2 - 1) * v_var), 2),
        GREATEST(1, ROUND(src.Qta * (1 + (RAND() * 2 - 1) * v_var))),
        1,
        src.Dim,
        'demo',
        NOW()
    FROM Web_Matrici_Dati src
    WHERE src.IdMatrice = p_id_matrice
      AND src.Dt        = v_data_riferimento;

END$$

DELIMITER ;


-- ----------------------------------------------------------------------------
-- 3. SP_POPOLA_STORICO_ANNUALE
-- ----------------------------------------------------------------------------
-- Popola tutti i giorni di un anno con dati basati sul primo giorno dell'anno
-- di riferimento, applicando una variazione casuale giornaliera controllata.
--
-- Parametri:
--   p_id_matrice       INT          – ID della matrice da popolare
--   p_anno_target      INT          – anno da generare (es. 2024)
--   p_variazione_pct   DECIMAL(5,2) – variazione massima in % (default: 5%)
--
-- Utilizza INSERT...SELECT con ON DUPLICATE KEY UPDATE (upsert) per garantire
-- idempotenza: la procedura può essere rieseguita senza generare duplicati.
-- La variazione casuale viene rigenerata ad ogni esecuzione.
-- ----------------------------------------------------------------------------

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_popola_storico_annuale$$

CREATE PROCEDURE sp_popola_storico_annuale(
    IN p_id_matrice      INT,
    IN p_anno_target     INT,
    IN p_variazione_pct  DECIMAL(5,2)
)
BEGIN
    DECLARE v_data_corrente DATE;
    DECLARE v_data_fine     DATE;
    DECLARE v_data_seed     DATE;
    DECLARE v_var           DECIMAL(5,4);

    -- Variazione massima: default 5% se non specificata o 0
    IF p_variazione_pct IS NULL OR p_variazione_pct = 0 THEN
        SET p_variazione_pct = 5.00;
    END IF;

    SET v_var           = p_variazione_pct / 100;
    SET v_data_corrente = CAST(CONCAT(p_anno_target, '-01-02') AS DATE);
    SET v_data_fine     = CAST(CONCAT(p_anno_target, '-12-31') AS DATE);
    SET v_data_seed     = CAST(CONCAT(p_anno_target, '-01-01') AS DATE);

    WHILE v_data_corrente <= v_data_fine DO

        INSERT INTO Web_Matrici_Dati
            (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
        SELECT
            CAST(CONCAT(DATE_FORMAT(v_data_corrente, '%Y%m%d'), src.IdCat) AS UNSIGNED),
            p_id_matrice,
            src.IdCat,
            CAST(v_data_corrente AS DATETIME),
            ROUND(src.Netto     * (1 + (RAND() * 2 - 1) * v_var), 2),
            src.Iva,
            ROUND(src.FattIvato * (1 + (RAND() * 2 - 1) * v_var), 2),
            GREATEST(1, ROUND(src.Qta * (1 + (RAND() * 2 - 1) * v_var))),
            1,
            src.Dim,
            'demo',
            NOW()
        FROM Web_Matrici_Dati src
        WHERE src.IdMatrice = p_id_matrice
          AND src.Dt        = v_data_seed
        ON DUPLICATE KEY UPDATE
            Netto     = VALUES(Netto),
            FattIvato = VALUES(FattIvato),
            Qta       = VALUES(Qta),
            Dim       = VALUES(Dim),
            DtUpd     = NOW();

        SET v_data_corrente = DATE_ADD(v_data_corrente, INTERVAL 1 DAY);

    END WHILE;

END$$

DELIMITER ;


-- ----------------------------------------------------------------------------
-- 4. DATI SEED
-- ----------------------------------------------------------------------------
-- Dati iniziali per le diverse matrici demo. Ogni matrice rappresenta un
-- prospect/scenario con categorie di prodotto distinte.
-- I dati includono coppie anno corrente / anno precedente per abilitare
-- confronti YoY nelle dashboard.
-- ----------------------------------------------------------------------------

-- Matrice 284 – Dati mensili per confronto MoM
INSERT INTO Web_Matrici_Dati
    (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
VALUES
    (202403012841, 284, 2841, '2024-03-01', 2008.20, 22, 2450.00, 104, 1,  5, 'demo', NOW()),
    (202403012842, 284, 2842, '2024-03-01', 4436.89, 22, 5413.00, 140, 1, 11, 'demo', NOW()),
    (202403012843, 284, 2843, '2024-03-01', 1434.43, 22, 1750.00, 316, 1,  4, 'demo', NOW()),
    (202403012844, 284, 2844, '2024-03-01', 1166.39, 22, 1423.00,  30, 1,  3, 'demo', NOW()),
    (202403012845, 284, 2845, '2024-03-01', 1111.48, 22, 1356.00,  40, 1, 15, 'demo', NOW()),
    (202403012846, 284, 2846, '2024-03-01',  838.52, 22, 1023.00,  42, 0,  6, 'demo', NOW());

-- Matrice 139 – Confronto YoY (2024 vs 2025)
INSERT INTO Web_Matrici_Dati
    (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
VALUES
    (202401011391, 139, 1391, '2024-01-01', 1539.34, 22, 1878.00, 75, 1,  9, 'demo', NOW()),
    (202401011392, 139, 1392, '2024-01-01', 1468.03, 22, 1791.00, 69, 1, 10, 'demo', NOW()),
    (202401011393, 139, 1393, '2024-01-01',  127.05, 22,  155.00, 36, 1,  4, 'demo', NOW()),
    (202401011394, 139, 1394, '2024-01-01',  761.48, 22,  929.00, 21, 1,  3, 'demo', NOW()),
    (202401011395, 139, 1395, '2024-01-01',  262.30, 22,  320.00, 17, 1,  2, 'demo', NOW()),
    (202401011396, 139, 1396, '2024-01-01',  217.21, 22,  265.00, 15, 1,  2, 'demo', NOW()),
    (202501011391, 139, 1391, '2025-01-01', 1541.80, 22, 1881.00, 57, 1,  7, 'demo', NOW()),
    (202501011392, 139, 1392, '2025-01-01', 1129.51, 22, 1378.00, 52, 1,  7, 'demo', NOW()),
    (202501011393, 139, 1393, '2025-01-01',   36.07, 22,   44.00, 11, 1,  2, 'demo', NOW()),
    (202501011394, 139, 1394, '2025-01-01',  732.79, 22,  894.00, 16, 1,  2, 'demo', NOW()),
    (202501011395, 139, 1395, '2025-01-01',  223.77, 22,  273.00, 15, 1,  2, 'demo', NOW()),
    (202501011396, 139, 1396, '2025-01-01',  142.62, 22,  174.00, 13, 1,  1, 'demo', NOW());

-- Matrice 252 – Confronto YoY (2024 vs 2025)
INSERT INTO Web_Matrici_Dati
    (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
VALUES
    (202501012521, 252, 2521, '2025-01-01', 372.95, 22, 455.00, 19, 1, 4, 'demo', NOW()),
    (202501012522, 252, 2522, '2025-01-01',  60.66, 22,  74.00, 10, 1, 3, 'demo', NOW()),
    (202501012523, 252, 2523, '2025-01-01', 147.59, 22, 213.00,  6, 1, 3, 'demo', NOW()),
    (202501012524, 252, 2524, '2025-01-01', 147.54, 22, 180.00,  6, 1, 3, 'demo', NOW()),
    (202501012525, 252, 2525, '2025-01-01', 242.62, 22, 296.00,  7, 1, 2, 'demo', NOW()),
    (202501012526, 252, 2526, '2025-01-01', 282.79, 22, 345.00, 11, 1, 3, 'demo', NOW()),
    (202501012527, 252, 2527, '2025-01-01',  90.16, 22, 110.00,  8, 1, 2, 'demo', NOW()),
    (202401012521, 252, 2521, '2024-01-01', 277.05, 22, 338.00, 14, 1, 4, 'demo', NOW()),
    (202401012522, 252, 2522, '2024-01-01',  64.75, 22,  79.00, 11, 1, 3, 'demo', NOW()),
    (202401012523, 252, 2523, '2024-01-01', 181.97, 22, 222.00,  6, 1, 2, 'demo', NOW()),
    (202401012524, 252, 2524, '2024-01-01', 100.82, 22, 123.00,  5, 1, 2, 'demo', NOW()),
    (202401012525, 252, 2525, '2024-01-01', 275.41, 22, 336.00,  6, 1, 3, 'demo', NOW()),
    (202401012526, 252, 2526, '2024-01-01', 238.52, 22, 291.00, 12, 1, 2, 'demo', NOW()),
    (202401012527, 252, 2527, '2024-01-01',  61.47, 22,  75.00,  5, 1, 2, 'demo', NOW());

-- Matrice 316 – Confronto YoY (2024 vs 2025)
INSERT INTO Web_Matrici_Dati
    (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
VALUES
    (202401013161, 316, 3161, '2024-01-01', 181.97, 22, 222.00,  8, 1, 4, 'demo', NOW()),
    (202401013162, 316, 3162, '2024-01-01', 189.34, 22, 231.00,  9, 1, 4, 'demo', NOW()),
    (202401013163, 316, 3163, '2024-01-01', 202.46, 22, 247.00,  9, 1, 4, 'demo', NOW()),
    (202401013164, 316, 3164, '2024-01-01', 252.46, 22, 308.00, 11, 1, 4, 'demo', NOW()),
    (202501013161, 316, 3161, '2025-01-01', 239.34, 22, 292.00, 10, 1, 4, 'demo', NOW()),
    (202501013162, 316, 3162, '2025-01-01', 123.77, 22, 151.00,  5, 1, 4, 'demo', NOW()),
    (202501013163, 316, 3163, '2025-01-01', 219.67, 22, 268.00,  7, 1, 4, 'demo', NOW()),
    (202501013164, 316, 3164, '2025-01-01', 210.66, 22, 257.00,  9, 1, 4, 'demo', NOW());

-- Matrice 313 – Confronto YoY (2024 vs 2025), 7 categorie
INSERT INTO Web_Matrici_Dati
    (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
VALUES
    (202401013131, 313, 3131, '2024-01-01',  962.62, 22, 1150.00,  92, 1, 4, 'demo', NOW()),
    (202401013132, 313, 3132, '2024-01-01', 1270.49, 22, 1550.00, 113, 1, 4, 'demo', NOW()),
    (202401013133, 313, 3133, '2024-01-01',  573.77, 22,  700.00,  72, 1, 4, 'demo', NOW()),
    (202401013134, 313, 3134, '2024-01-01',  540.98, 22,  660.00,  68, 1, 5, 'demo', NOW()),
    (202401013135, 313, 3135, '2024-01-01', 1639.34, 22, 2000.00, 121, 1, 5, 'demo', NOW()),
    (202401013136, 313, 3136, '2024-01-01',  983.61, 22, 1200.00,  95, 1, 4, 'demo', NOW()),
    (202401013137, 313, 3137, '2024-01-01', 1475.41, 22, 1800.00, 140, 1, 4, 'demo', NOW()),
    (202501013131, 313, 3131, '2025-01-01',  983.61, 22, 1200.00,  95, 1, 4, 'demo', NOW()),
    (202501013132, 313, 3132, '2025-01-01', 1229.51, 22, 1500.00, 110, 1, 4, 'demo', NOW()),
    (202501013133, 313, 3133, '2025-01-01',  778.69, 22,  950.00,  80, 1, 4, 'demo', NOW()),
    (202501013134, 313, 3134, '2025-01-01',  754.10, 22,  920.00,  77, 1, 5, 'demo', NOW()),
    (202501013135, 313, 3135, '2025-01-01', 1147.54, 22, 1400.00, 105, 1, 5, 'demo', NOW()),
    (202501013136, 313, 3136, '2025-01-01', 1024.59, 22, 1250.00, 100, 1, 4, 'demo', NOW()),
    (202501013137, 313, 3137, '2025-01-01', 1311.48, 22, 1600.00, 120, 1, 4, 'demo', NOW());

-- Matrice 312 – Confronto YoY (2024 vs 2025), 5 categorie
INSERT INTO Web_Matrici_Dati
    (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
VALUES
    (202401013121, 312, 3121, '2024-01-01',  462.30, 22,  564.00, 208, 1, 3, 'demo', NOW()),
    (202401013122, 312, 3122, '2024-01-01',  955.74, 22, 1166.00, 153, 1, 2, 'demo', NOW()),
    (202401013123, 312, 3123, '2024-01-01',  208.20, 22,  254.00,  56, 1, 3, 'demo', NOW()),
    (202401013124, 312, 3124, '2024-01-01', 1739.34, 22, 2122.00, 273, 1, 4, 'demo', NOW()),
    (202401013125, 312, 3125, '2024-01-01',  163.93, 22,  200.00,  30, 1, 3, 'demo', NOW()),
    (202501013121, 312, 3121, '2025-01-01',  325.41, 22,  397.00, 198, 1, 3, 'demo', NOW()),
    (202501013122, 312, 3122, '2025-01-01', 1218.85, 22, 1487.00, 163, 1, 2, 'demo', NOW()),
    (202501013123, 312, 3123, '2025-01-01',  208.20, 22,  254.00,  56, 1, 3, 'demo', NOW()),
    (202501013124, 312, 3124, '2025-01-01', 1666.39, 22, 2033.00, 277, 1, 4, 'demo', NOW()),
    (202501013125, 312, 3125, '2025-01-01',  259.84, 22,  317.00,  29, 1, 2, 'demo', NOW());

-- Matrice 314 – Confronto YoY (2024 vs 2025), 6 categorie
INSERT INTO Web_Matrici_Dati
    (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
VALUES
    (202401013141, 314, 3141, '2024-01-01', 223.77, 22, 273.00, 38, 1, 30, 'demo', NOW()),
    (202401013142, 314, 3142, '2024-01-01', 756.56, 22, 923.00, 45, 1, 30, 'demo', NOW()),
    (202401013143, 314, 3143, '2024-01-01', 111.48, 22, 136.00, 16, 1, 27, 'demo', NOW()),
    (202401013144, 314, 3144, '2024-01-01', 222.13, 22, 271.00, 52, 1, 26, 'demo', NOW()),
    (202401013145, 314, 3145, '2024-01-01', 180.33, 22, 220.00, 32, 1, 29, 'demo', NOW()),
    (202401013146, 314, 3146, '2024-01-01', 194.26, 22, 237.00, 15, 1, 22, 'demo', NOW()),
    (202501013141, 314, 3141, '2025-01-01', 294.26, 22, 359.00, 42, 1, 30, 'demo', NOW()),
    (202501013142, 314, 3142, '2025-01-01', 710.66, 22, 867.00, 65, 1, 31, 'demo', NOW()),
    (202501013143, 314, 3143, '2025-01-01', 104.10, 22, 127.00, 15, 1, 27, 'demo', NOW()),
    (202501013144, 314, 3144, '2025-01-01',  84.43, 22, 103.00, 40, 1, 22, 'demo', NOW()),
    (202501013145, 314, 3145, '2025-01-01', 221.31, 22, 270.00, 57, 1, 31, 'demo', NOW()),
    (202501013146, 314, 3146, '2025-01-01', 130.33, 22, 159.00, 22, 1, 26, 'demo', NOW());

-- Matrice 321 – Confronto YoY multi-anno (2023, 2024, 2025)
INSERT INTO Web_Matrici_Dati
    (Idx, IdMatrice, IdCat, Dt, Netto, Iva, FattIvato, Qta, Lavorato, Dim, IdUtente, DtUpd)
VALUES
    (202301013211, 321, 3211, '2023-01-01', 15245.90, 22, 18600.00, 620, 1, 2330, 'demo', NOW()),
    (202301013212, 321, 3212, '2023-01-01', 15163.93, 22, 18500.00, 370, 1, 1430, 'demo', NOW()),
    (202301013213, 321, 3213, '2023-01-01',  3934.43, 22,  4800.00, 280, 1, 1500, 'demo', NOW()),
    (202301013214, 321, 3214, '2023-01-01', 11885.25, 22, 14500.00, 123, 1, 1150, 'demo', NOW()),
    (202301013215, 321, 3215, '2023-01-01', 14344.26, 22, 17500.00, 350, 1, 1000, 'demo', NOW()),
    (202301013216, 321, 3216, '2023-01-01',  3401.64, 22,  4150.00, 100, 1,  320, 'demo', NOW()),
    (202401013211, 321, 3211, '2024-01-01', 20255.01, 22, 24711.11, 600, 1, 2333, 'demo', NOW()),
    (202401013212, 321, 3212, '2024-01-01', 15007.01, 22, 18308.55, 311, 1, 1433, 'demo', NOW()),
    (202401013213, 321, 3213, '2024-01-01',  3111.11, 22,  3795.55, 235, 1, 1630, 'demo', NOW()),
    (202401013214, 321, 3214, '2024-01-01', 12593.97, 22, 15364.64, 137, 1, 1166, 'demo', NOW()),
    (202401013215, 321, 3215, '2024-01-01', 10785.16, 22, 13157.90, 284, 1, 1000, 'demo', NOW()),
    (202401013216, 321, 3216, '2024-01-01',  3333.33, 22,  4066.66, 100, 1,  323, 'demo', NOW()),
    (202501013211, 321, 3211, '2025-01-01', 15245.90, 22, 18600.00, 620, 1, 2330, 'demo', NOW()),
    (202501013212, 321, 3212, '2025-01-01', 15163.93, 22, 18500.00, 370, 1, 1430, 'demo', NOW()),
    (202501013213, 321, 3213, '2025-01-01',  3934.43, 22,  4800.00, 280, 1, 1500, 'demo', NOW()),
    (202501013214, 321, 3214, '2025-01-01', 11885.25, 22, 14500.00, 123, 1, 1150, 'demo', NOW()),
    (202501013215, 321, 3215, '2025-01-01', 14344.26, 22, 17500.00, 350, 1, 1000, 'demo', NOW()),
    (202501013216, 321, 3216, '2025-01-01',  3401.64, 22,  4150.00, 100, 1,  320, 'demo', NOW());


-- ----------------------------------------------------------------------------
-- 5. ESEMPI DI UTILIZZO
-- ----------------------------------------------------------------------------

-- Alimentazione giornaliera MoM per matrice 284, variazione ±5%
-- CALL sp_genera_dati_demo_giornaliero(284, 22, 'MoM', 5.00);

-- Alimentazione giornaliera YoY per matrice 139, variazione ±3%
-- CALL sp_genera_dati_demo_giornaliero(139, 22, 'YoY', 3.00);

-- Backfill storico completo anno 2024 per matrice 341, variazione ±5%
-- CALL sp_popola_storico_annuale(341, 2024, 5.00);


-- ----------------------------------------------------------------------------
-- 6. SCHEDULAZIONE AUTOMATICA (Event Scheduler)
-- ----------------------------------------------------------------------------
-- Esempio di event per esecuzione giornaliera automatica.
-- Richiede: SET GLOBAL event_scheduler = ON;
--
-- CREATE EVENT evt_demo_giornaliero
-- ON SCHEDULE EVERY 1 DAY
-- STARTS CURRENT_DATE + INTERVAL 1 DAY
-- DO
-- BEGIN
--     CALL sp_genera_dati_demo_giornaliero(284, 22, 'MoM', 5.00);
--     CALL sp_genera_dati_demo_giornaliero(139, 22, 'YoY', 5.00);
-- END;
 