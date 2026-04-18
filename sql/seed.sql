INSERT IGNORE INTO shipments (
	destination_city,
	estimated_delivery_date,
	origin_city,
	status,
	tracking_number
) VALUES (
	'Valparaiso',
	'2026-04-24',
	'Santiago',
	'en_transito',
	'123456789'
);

INSERT IGNORE INTO shipments (
	destination_city,
	estimated_delivery_date,
	origin_city,
	status,
	tracking_number
) VALUES (
	'Antofagasta',
	NULL,
	'La Serena',
	'pendiente',
	'987654321'
);

INSERT IGNORE INTO shipments (
	destination_city,
	estimated_delivery_date,
	origin_city,
	status,
	tracking_number
) VALUES (
	'Concepcion',
	'2026-04-12',
	'Temuco',
	'entregado',
	'567890123'
);