import sqlite3
import sys
from os import environ
import os

db_path = "results.sqlite"

def main():
    repos = open("repos.txt").read().splitlines()
    repos = [repo for repo in repos if repo != "" and not repo.startswith("#")]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM stars"
    )
    conn.commit()
    cursor.close()
    conn.close()
    print("Database cleaned, ready to start crawling...")
    for repo in repos:
        print(f"Crawling {repo}...")
        crawl(repo)

def crawl(repository):
    python_executable = sys.executable
    github_token = environ.get("GITHUB_TOKEN")
    if github_token is None:
        print("GITHUB_TOKEN environment variable not set, exiting...")
        sys.exit(1)
    command = [python_executable, "crawl.py", repository, db_path]
    env = {"GITHUB_TOKEN": github_token}
    os.execvpe(python_executable, command, env)

if __name__ == "__main__":
    main()
