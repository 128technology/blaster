DROP TABLE IF EXISTS iso_status_enum;
DROP TABLE IF EXISTS iso;
DROP TABLE IF EXISTS conductor;
DROP TABLE IF EXISTS quickstart;
DROP TABLE IF EXISTS node;

CREATE TABLE iso_status_enum (
  id INTEGER PRIMARY KEY,
  status TEXT NOT NULL
);

INSERT INTO iso_status_enum(id, status) VALUES (1, 'Processing');
INSERT INTO iso_status_enum(id, status) VALUES (2, 'Ready');
INSERT INTO iso_status_enum(id, status) VALUES (3, 'Failed');

CREATE TABLE iso (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  status_id INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (status_id) REFERENCES iso_status_enum (id)
);

CREATE TABLE conductor (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  auth_key TEXT NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quickstart (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conductor_name TEXT,
  router_name TEXT,
  node_name TEXT,
  asset_id TEXT,
  config TEXT,
  description TEXT,
  default_quickstart INT DEFAULT 0 NOT NULL
);

CREATE TABLE node (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  identifier TEXT NOT NULL,
  quickstart_id INTEGER,
  iso_id INTEGER,
  FOREIGN KEY (quickstart_id) REFERENCES quickstart (id),
  FOREIGN KEY (iso_id) REFERENCES iso (id)
);
