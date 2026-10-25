-- Current schema generated from SQLAlchemy MySQL definitions


CREATE TABLE events (
	id VARCHAR(36) NOT NULL, 
	seal_id VARCHAR(36), 
	action VARCHAR(64) NOT NULL, 
	details JSON NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE knowledge (
	id VARCHAR(36) NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	category VARCHAR(32) NOT NULL, 
	content TEXT NOT NULL, 
	source_title VARCHAR(255) NOT NULL, 
	source_url VARCHAR(500) NOT NULL, 
	image VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE seals (
	id VARCHAR(36) NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	source_kind VARCHAR(32) NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE artifacts (
	id VARCHAR(36) NOT NULL, 
	seal_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	media_type VARCHAR(100) NOT NULL, 
	metadata JSON NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(seal_id) REFERENCES seals (id)
)

;
