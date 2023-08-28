#!/usr/bin/env python3
import sqlite3
import sys
import logging

logging.basicConfig(level=logging.INFO)


def get_db_path():
    if len(sys.argv) > 2:
        print("Usage: python3 init_db.py <database path>")
        sys.exit(1)
    elif len(sys.argv) == 1:
        return "results.sqlite"
    return sys.argv[1]


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
              CREATE TABLE IF NOT EXISTS repositories (id TEXT PRIMARY KEY, 
              stars INTEGER, forks INTEGER, watchers INTEGER)
              """
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS stars(repo_id TEXT, user_id TEXT, 
              FOREIGN KEY(repo_id) REFERENCES repositories(id), 
              PRIMARY KEY(repo_id, user_id))"""
    )
    c.execute(
        """
              CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT, 
              company TEXT, blog TEXT, location TEXT, email TEXT, bio TEXT, 
              twitter_username TEXT, public_repos INTEGER, public_gists INTEGER, 
              followers INTEGER, following INTEGER, created_at TIMESTAMP)
              """
    )
    c.close()
    conn.close()


def main():
    db_path = get_db_path()
    logging.info("Initializing database at %s", db_path)
    try:
        init_db(db_path)
    except sqlite3.OperationalError as e:
        logging.error("Error initializing database: %s", e)
        sys.exit(1)
    logging.info("Database initialized successfully")


if __name__ == "__main__":
    main()
