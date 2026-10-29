-- PostgreSQL schema for a NEW empty database; do not apply to existing tables.

CREATE TABLE users (
	id SERIAL NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	role VARCHAR(16) NOT NULL, 
	email VARCHAR(254), 
	status VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (role IN ('student','teacher','admin')), 
	CHECK (status IN ('active','disabled')), 
	UNIQUE (username)
)

;

CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(120) NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE auth_sessions (
	token_hash VARCHAR(64) NOT NULL, 
	user_id INTEGER NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE courses (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	teacher_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(teacher_id) REFERENCES users (id)
)

;

CREATE TABLE class_sessions (
	id SERIAL NOT NULL, 
	course_id INTEGER NOT NULL, 
	class_name VARCHAR(80) NOT NULL, 
	room VARCHAR(80), 
	start_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	end_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (end_time > start_time), 
	FOREIGN KEY(course_id) REFERENCES courses (id)
)

;

CREATE TABLE emoji_records (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	session_id INTEGER NOT NULL, 
	emoji VARCHAR(20) NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	source VARCHAR(10) NOT NULL, 
	confidence FLOAT, 
	device_id VARCHAR(100), 
	event_id VARCHAR(100), 
	PRIMARY KEY (id), 
	CHECK (emoji IN ('happy','neutral','sad','angry','surprise','fear','disgust')), 
	CHECK (source IN ('MANUAL','AI')), 
	CHECK (source != 'AI' OR (confidence IS NOT NULL AND confidence >= 0 AND confidence <= 1)), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(session_id) REFERENCES class_sessions (id), 
	UNIQUE (event_id)
)

;
CREATE INDEX ix_emoji_records_timestamp ON emoji_records (timestamp);
CREATE INDEX ix_emoji_records_session_id ON emoji_records (session_id);

CREATE TABLE schedule_users (
	id SERIAL NOT NULL, 
	session_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	scheduled_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (session_id, user_id), 
	FOREIGN KEY(session_id) REFERENCES class_sessions (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
