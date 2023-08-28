#!/usr/bin/env python3
import requests
import sqlite3
from tqdm import tqdm
import sys
import os
import logging
import datetime
import time

logging.basicConfig(level=logging.INFO)

GITHUB_API_PREFIX = "https://api.github.com/"
SLEEP_TIME = 0.3
PER_PAGE = 100


def get_session():
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    session = requests.Session()
    if GITHUB_TOKEN:
        session.headers.update({"Authorization": "Bearer %s" % GITHUB_TOKEN})
    else:
        logging.warning(
            "No GITHUB_TOKEN environment variable found. This will result in a lower rate limit."
        )
    session.headers.update({"Accept": "application/vnd.github+json"})
    session.headers.update({"X-GitHub-Api-Version": "2022-11-28"})
    return session


def check_and_wait_for_rate_limit(response):
    remaining_rate_limit = int(response.headers["X-RateLimit-Remaining"])
    rate_limit_reset = int(response.headers["X-RateLimit-Reset"])
    current_time = datetime.datetime.now().timestamp()
    rate_limit_reset_interval = rate_limit_reset - current_time
    logging.debug(
        "Remaining rate limit: %d, reset in: %d seconds",
        remaining_rate_limit,
        rate_limit_reset_interval,
    )
    if remaining_rate_limit < 5:
        logging.info(
            "Rate limit almost reached. Waiting for reset in %d seconds...",
            rate_limit_reset_interval,
        )
        time.sleep(rate_limit_reset_interval + 10)
        logging.info("Resuming")


def get_repository(repository):
    url = GITHUB_API_PREFIX + "repos/%s" % repository
    response = session.get(url)
    time.sleep(SLEEP_TIME)
    check_and_wait_for_rate_limit(response)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error("Error getting repository %s: %s", repository, response.json())
        return None


def parse_args():
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print("Usage: python3 crawl.py <repository> [database path]")
        sys.exit(1)
    repository = sys.argv[1]
    if len(sys.argv) == 3:
        database = sys.argv[2]
    else:
        database = "results.sqlite"
    return repository, database


def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    return conn


def get_stargazers(repository):
    page_idx = 0
    all_stargazers = []
    progress_bar = tqdm(
        desc="Fetching stargazers",
        unit=" pages",
        total=repository["stargazers_count"] // PER_PAGE + 1,
    )
    while True:
        page_idx += 1
        url = GITHUB_API_PREFIX + "repos/%s/stargazers?page=%d&per_page=%d" % (
            repository["full_name"],
            page_idx,
            PER_PAGE,
        )
        response = session.get(url)
        time.sleep(SLEEP_TIME)
        check_and_wait_for_rate_limit(response)
        if response.status_code == 200:
            stargazers = response.json()
            if len(stargazers) == 0:
                break
            all_stargazers.extend(stargazers)
            progress_bar.update(1)
        else:
            logging.error(
                "Error getting stargazers for repository %s: %s",
                repository["full_name"],
                response.json(),
            )
            break
    return all_stargazers


def get_user(user_id):
    url = GITHUB_API_PREFIX + "users/%s" % user_id
    response = session.get(url)
    time.sleep(SLEEP_TIME)
    check_and_wait_for_rate_limit(response)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error("Error getting user %s: %s", user_id, response.json())
        return None


def persist_repository(repository, conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO repositories VALUES (?, ?, ?, ?)",
        (
            repository["full_name"],
            repository["stargazers_count"],
            repository["forks_count"],
            repository["watchers_count"],
        ),
    )
    conn.commit()
    cursor.close()


def persist_stargazers(stargazers, repository, conn):
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO stars VALUES (?, ?)",
        [(repository["full_name"], stargazer["login"]) for stargazer in stargazers],
    )
    conn.commit()
    cursor.close()


def fetch_and_persist_stargazers(repository, conn):
    repository = get_repository(repository)
    if repository is None:
        logging.error(
            "The repository %s does not exist or there is an error getting it",
            repository,
        )
        sys.exit(1)
    else:
        logging.info(
            "Repository %s found, #Stars: %d, #Forks: %d, #Watches: %d",
            repository["full_name"],
            repository["stargazers_count"],
            repository["forks_count"],
            repository["watchers_count"],
        )
    stargazers = get_stargazers(repository)
    if len(stargazers) == 0:
        logging.info(
            "No stargazers found for repository %s or there was an error getting them, exiting...",
            repository["full_name"],
        )
        sys.exit(1)
    else:
        logging.info(
            "%d stargazers fetched for repository %s",
            len(stargazers),
            repository["full_name"],
        )
    logging.info("Persisting repository data to database...")
    persist_repository(repository, conn)
    logging.info("Persisting stargazers data to database...")
    persist_stargazers(stargazers, repository, conn)


def get_stargazers_from_db(repository, conn):
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM stars WHERE repo_id=?", (repository,))
    stargazers = cursor.fetchall()
    cursor.close()
    return [stargazer[0] for stargazer in stargazers]


def fetch_and_persist_users(stargazers, conn):
    cursor = conn.cursor()
    for user_id in tqdm(stargazers, desc="Fetching user profiles", unit=" users"):
        cursor.execute("SELECT COUNT(*) FROM users WHERE id=?", (user_id,))
        if cursor.fetchone()[0] > 0:
            logging.debug("User %s already exists in database, skipping...", user_id)
            continue
        user = get_user(user_id)
        if user is None:
            logging.error("Error getting user %s, skipping...", user_id)
            continue
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user["login"],
                user["name"],
                user["company"],
                user["blog"],
                user["location"],
                user["email"],
                user["bio"],
                user["twitter_username"],
                user["public_repos"],
                user["public_gists"],
                user["followers"],
                user["following"],
                user["created_at"],
            ),
        )
        conn.commit()


def main():
    global session
    session = get_session()
    repository, db_path = parse_args()
    conn = get_db_connection(db_path)
    stargazers = get_stargazers_from_db(repository, conn)
    if len(stargazers) < 1:
        logging.info(
            "No stargazers found for repository %s in database, fetching them...",
            repository,
        )
        fetch_and_persist_stargazers(repository, conn)
        stargazers = get_stargazers_from_db(repository, conn)
    logging.info(
        "Crawling user profile for %d stargazers for repository %s...",
        len(stargazers),
        repository,
    )
    fetch_and_persist_users(stargazers, conn)
    conn.close()


if __name__ == "__main__":
    main()
