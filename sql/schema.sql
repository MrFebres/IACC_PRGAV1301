CREATE TABLE IF NOT EXISTS shipments (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP NULL DEFAULT NULL,
    destination_city VARCHAR(120) NOT NULL,
    estimated_delivery_date DATE NULL DEFAULT NULL,
    origin_city VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    tracking_number VARCHAR(32) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_shipments_created_at (created_at),
    INDEX idx_shipments_status (status),
    UNIQUE INDEX idx_shipments_tracking_number (tracking_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;