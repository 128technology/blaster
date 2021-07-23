ALTER TABLE iso ADD pre_bootstrap_script TEXT;
ALTER TABLE iso ADD post_bootstrap_script TEXT;

CREATE TABLE script (
  name TEXT PRIMARY KEY,
  description TEXT
);
INSERT INTO script (name, description)  VALUES ('shutdown-post', 'Sample script to poweroff system after bootstrapping');

PRAGMA user_version = 1;
