<?php
$db = new SQLite3('main.db');
$db->exec('create table stations(
    id          INTEGER PRIMARY KEY, 
    callsign    TEXT,
    description TEXT,
    base_url    TEXT,
    last_seen   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_seen  TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    pings       INTEGER,
    drops       INTEGER,
    latency     INTEGER,
    log         TEXT,
    notes       TEXT
)');

