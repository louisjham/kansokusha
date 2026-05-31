import requests
import logging
import os
from flask import current_app
from app.models import get_setting

logger = logging.getLogger(__name__)

class GithubService:
    """Service for interacting with the GitHub REST API."""

    def __init__(self):
        """Initialize GitHub service and headers."""
        # Retrieve token from settings, config, or environment variables
        self.token = get_setting('GITHUB_TOKEN', None)
        if not self.token:
            try:
                self.token = current_app.config.get('GITHUB_TOKEN')
            except Exception:
                self.token = os.environ.get('GITHUB_TOKEN')

        self.headers = {
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'Kansokusha-App'
        }
        if self.token:
            self.headers['Authorization'] = f"Bearer {self.token}"
            logger.info("GitHub service initialized with authentication token.")
        else:
            logger.warning("GitHub service initialized without authentication token. Unauthenticated rate limits will apply.")

    def scrape_github_profile(self, username: str):
        """
        Scrape a GitHub profile and return standardized posts/activity.
        
        Args:
            username (str): GitHub username
            
        Returns:
            list: List of processed post entries in standard format
        """
        posts = []
        base_url = "https://api.github.com"

        # 1. Fetch Profile Summary
        try:
            profile_url = f"{base_url}/users/{username}"
            logger.info(f"Fetching GitHub profile for {username}")
            resp = requests.get(profile_url, headers=self.headers, timeout=15)
            
            if resp.status_code == 200:
                profile = resp.json()
                profile_post = {
                    'platform': 'github',
                    'post_id': f"profile-{profile.get('id')}",
                    'content': f"GitHub Profile Summary:\nName: {profile.get('name') or username}\nBio: {profile.get('bio') or 'No bio'}\nCompany: {profile.get('company') or 'N/A'}\nPublic Repositories: {profile.get('public_repos', 0)}\nFollowers: {profile.get('followers', 0)}",
                    'text': f"GitHub Profile Summary:\nName: {profile.get('name') or username}\nBio: {profile.get('bio') or 'No bio'}\nCompany: {profile.get('company') or 'N/A'}\nPublic Repositories: {profile.get('public_repos', 0)}\nFollowers: {profile.get('followers', 0)}",
                    'author': username,
                    'timestamp': profile.get('created_at'),
                    'created_at': profile.get('created_at'),
                    'source_context': 'github',
                    'url': profile.get('html_url', ''),
                    'raw_data': profile
                }
                posts.append(profile_post)
            elif resp.status_code == 404:
                logger.error(f"GitHub user {username} not found")
                raise ValueError(f"GitHub user '{username}' not found.")
            else:
                logger.error(f"Failed to fetch profile: Status code {resp.status_code}, details: {resp.text}")
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"Error fetching GitHub profile for {username}: {str(e)}")
            raise

        # 2. Fetch Repositories
        try:
            repos_url = f"{base_url}/users/{username}/repos?sort=updated&per_page=30"
            logger.info(f"Fetching GitHub repos for {username}")
            resp = requests.get(repos_url, headers=self.headers, timeout=15)
            
            if resp.status_code == 200:
                repos = resp.json()
                for repo in repos:
                    repo_post = {
                        'platform': 'github',
                        'post_id': f"repo-{repo.get('id')}",
                        'content': f"Repository: {repo.get('name')}\nLanguage: {repo.get('language') or 'N/A'}\nDescription: {repo.get('description') or 'No description'}",
                        'text': f"Repository: {repo.get('name')}\nLanguage: {repo.get('language') or 'N/A'}\nDescription: {repo.get('description') or 'No description'}",
                        'author': username,
                        'timestamp': repo.get('updated_at'),
                        'created_at': repo.get('updated_at'),
                        'source_context': 'github',
                        'url': repo.get('html_url', ''),
                        'raw_data': repo
                    }
                    posts.append(repo_post)
            else:
                logger.warning(f"Failed to fetch repositories: Status code {resp.status_code}")
        except Exception as e:
            logger.warning(f"Error fetching repositories for {username}: {str(e)}")

        # 3. Fetch Recent Events
        try:
            events_url = f"{base_url}/users/{username}/events/public?per_page=50"
            logger.info(f"Fetching GitHub public events for {username}")
            resp = requests.get(events_url, headers=self.headers, timeout=15)
            
            if resp.status_code == 200:
                events = resp.json()
                for event in events:
                    event_type = event.get('type')
                    repo_name = event.get('repo', {}).get('name', 'unknown')
                    payload = event.get('payload', {})
                    
                    # Format content based on event type
                    if event_type == 'PushEvent':
                        commits = payload.get('commits', [])
                        commit_msgs = [f"- {c.get('message')}" for c in commits]
                        commit_text = "\n".join(commit_msgs)
                        content = f"Pushed to {repo_name}:\n{commit_text}" if commit_text else f"Pushed to {repo_name}"
                    elif event_type == 'IssuesEvent':
                        action = payload.get('action', 'updated')
                        issue_title = payload.get('issue', {}).get('title', 'N/A')
                        content = f"{action.capitalize()} issue in {repo_name}: '{issue_title}'"
                    elif event_type == 'IssueCommentEvent':
                        action = payload.get('action', 'updated')
                        comment_body = payload.get('comment', {}).get('body', '')
                        content = f"Commented on issue in {repo_name}:\n{comment_body}"
                    elif event_type == 'PullRequestEvent':
                        action = payload.get('action', 'updated')
                        pr_title = payload.get('pull_request', {}).get('title', 'N/A')
                        content = f"{action.capitalize()} Pull Request in {repo_name}: '{pr_title}'"
                    elif event_type == 'WatchEvent':
                        content = f"Starred repository {repo_name}"
                    elif event_type == 'ForkEvent':
                        content = f"Forked repository {repo_name}"
                    elif event_type == 'CreateEvent':
                        ref_type = payload.get('ref_type', 'repository')
                        ref = payload.get('ref', '')
                        ref_str = f"'{ref}' " if ref else ""
                        content = f"Created {ref_type} {ref_str}in {repo_name}"
                    else:
                        content = f"GitHub Event: {event_type} on {repo_name}"

                    event_post = {
                        'platform': 'github',
                        'post_id': f"event-{event.get('id')}",
                        'content': content,
                        'text': content,
                        'author': username,
                        'timestamp': event.get('created_at'),
                        'created_at': event.get('created_at'),
                        'source_context': 'github',
                        'url': f"https://github.com/{repo_name}",
                        'raw_data': event
                    }
                    posts.append(event_post)
            else:
                logger.warning(f"Failed to fetch public events: Status code {resp.status_code}")
        except Exception as e:
            logger.warning(f"Error fetching public events for {username}: {str(e)}")

        logger.info(f"Aggregated {len(posts)} posts for GitHub user {username}")
        return posts
