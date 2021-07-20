ALTER TABLE iso ADD pre_bootstrap_script TEXT;
ALTER TABLE iso ADD post_bootstrap_script TEXT;

CREATE TABLE script (
  name TEXT PRIMARY KEY,
  description TEXT
);

PRAGMA user_version = 1;
