-- src/api/db/schema.sql

CREATE TABLE IF NOT EXISTS region_thresholds (
    region_id       VARCHAR(20) PRIMARY KEY,
    theta           FLOAT       NOT NULL DEFAULT 2.0,
    tp_count        INTEGER     NOT NULL DEFAULT 0,
    fp_count        INTEGER     NOT NULL DEFAULT 0,
    last_updated    TIMESTAMP   DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id            SERIAL PRIMARY KEY,
    region_id           VARCHAR(20) NOT NULL,
    alert_date          DATE        NOT NULL,
    score               FLOAT       NOT NULL,
    theta_used          FLOAT       NOT NULL,
    chl_z               FLOAT,
    persistence_days    INTEGER     DEFAULT 1,
    created_at          TIMESTAMP   DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_feedback (
    feedback_id     SERIAL PRIMARY KEY,
    alert_id        INTEGER     REFERENCES alerts(alert_id),
    region_id       VARCHAR(20) NOT NULL,
    label           VARCHAR(10) NOT NULL CHECK (label IN ('TP', 'FP')),
    user_id         VARCHAR(50) DEFAULT 'demo',
    created_at      TIMESTAMP   DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS score_cache (
    date DATE NOT NULL,
    zone_id TEXT NOT NULL,
    z_score FLOAT NOT NULL,
    chl_raw FLOAT,
    mu FLOAT,
    PRIMARY KEY (date, zone_id)
);

CREATE INDEX IF NOT EXISTS idx_score_date ON score_cache(date);
CREATE INDEX IF NOT EXISTS idx_alerts_date     ON alerts(alert_date);
CREATE INDEX IF NOT EXISTS idx_alerts_region   ON alerts(region_id);
CREATE INDEX IF NOT EXISTS idx_feedback_alert  ON alert_feedback(alert_id);