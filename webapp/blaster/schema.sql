DROP TABLE IF EXISTS iso;
DROP TABLE IF EXISTS conductor;
DROP TABLE IF EXISTS quickstart;
DROP TABLE IF EXISTS node;
DROP TABLE IF EXISTS passwords;

CREATE TABLE iso (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  pre_bootstrap_script TEXT,
  post_bootstrap_script TEXT,
  status TEXT NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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
  default_quickstart INT DEFAULT 0 NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE node (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  identifier TEXT NOT NULL,
  quickstart_id INTEGER,
  iso_id TEXT,
  status TEXT NOT NULL,
  validation_report TEXT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (quickstart_id) REFERENCES quickstart (id)
);

CREATE TABLE passwords (
  username TEXT PRIMARY KEY,
  password_hash TEXT
);

CREATE TABLE script (
  name TEXT PRIMARY KEY,
  description TEXT
);
