CREATE TABLE passwords (
  username TEXT PRIMARY KEY,
  password_hash TEXT
);

PRAGMA user_version = 1;
