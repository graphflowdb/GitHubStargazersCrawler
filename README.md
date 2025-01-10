# GitHubStargazersCrawler
A simple crawler to get the user profile of all stargazers of the specified GitHub repository via GitHub API. The crawler persists the data in a SQLite database

## Usage
1. Install the requirements: `pip install -r requirements.txt`
1. Create a GitHub API token and store it as an environment variable: `export GITHUB_TOKEN=<your token>`
1. Initialize the database: `python init_db.py`
1. Run the crawler: `python crawl.py <repository>`, for example `python crawler.py kuzudb/kuzu`

## Notes
- If the crawler is stopped, the current state will be saved in the SQLite database. It is possible to run the crawler multiple times for the same repository. It will automatically skip already crawled users and continue from the last saved state. 
- The crawler will also automatically handle the GitHub API rate limit. If the rate limit is reached, the crawler will wait until the limit is reset and then continue the crawling process.
- It is possible to run the crawler for multiple repositories over the same database. 
- It is possible to run the crawler without a GitHub API token, but the rate limit is much lower. Also, some information, such as the email address, will not be available without a token.
- The crawler will try to crawl each user only once. If an error occurs during crawling, the request will not be repeated. However, when restarting the crawler, the skipped users will be crawled again.
