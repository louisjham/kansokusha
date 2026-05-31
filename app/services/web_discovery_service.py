import os
import requests
import logging
import urllib.parse
import hashlib
from datetime import datetime
from flask import current_app
from app.models import get_setting

logger = logging.getLogger(__name__)

# List of low-value people-search and spam domains to filter or penalize
BLOCKLIST_DOMAINS = [
    "spokeo.com",
    "mylife.com",
    "whitepages.com",
    "radaris.com",
    "beenverified.com",
    "instantcheckmate.com",
    "truthfinder.com",
    "peoplesmart.com",
    "intelius.com",
    "peekyou.com",
    "peoplefinders.com",
    "ussearch.com",
    "zabasearch.com",
    "publicrecords360.com",
    "checkpeople.com",
]

# Safeguards to prevent exploitation or private identifier leaks
SAFEGUARD_KEYWORDS = [
    "password", "passwd", "secret", "ssn", "social security", "pin", "token",
    "credit card", "bank", "account number", "private key", "exploit", "hack",
    "vuln", "vulnerability", "cve", "payload", "sql injection", "xss", "payload"
]

class WebDiscoveryService:
    """
    Service for executing OSINT-style web discovery via Google Custom Search Engine
    and structuring the results for further downstream behavioral analysis.
    """

    def __init__(self):
        """Initialize Google Custom Search API configuration."""
        self.api_key = get_setting('GOOGLE_CSE_API_KEY', None)
        self.cx = get_setting('GOOGLE_CSE_CX', None)

        if not self.api_key or not self.cx:
            try:
                self.api_key = self.api_key or current_app.config.get('GOOGLE_CSE_API_KEY')
                self.cx = self.cx or current_app.config.get('GOOGLE_CSE_CX')
            except Exception:
                self.api_key = self.api_key or os.environ.get('GOOGLE_CSE_API_KEY')
                self.cx = self.cx or os.environ.get('GOOGLE_CSE_CX')

        try:
            self.max_queries = int(get_setting('WEB_DISCOVERY_MAX_QUERIES', 10))
        except Exception:
            try:
                self.max_queries = int(current_app.config.get('WEB_DISCOVERY_MAX_QUERIES', 10))
            except Exception:
                self.max_queries = int(os.environ.get('WEB_DISCOVERY_MAX_QUERIES', 10))

        try:
            self.max_results_per_query = int(get_setting('WEB_DISCOVERY_MAX_RESULTS_PER_QUERY', 10))
        except Exception:
            try:
                self.max_results_per_query = int(current_app.config.get('WEB_DISCOVERY_MAX_RESULTS_PER_QUERY', 10))
            except Exception:
                self.max_results_per_query = int(os.environ.get('WEB_DISCOVERY_MAX_RESULTS_PER_QUERY', 10))

    def build_queries(self, profile: dict) -> list[str]:
        """
        Build target search queries from profile inputs using standard dorks.
        
        Args:
            profile (dict): Info about the subject:
                - full_name (str)
                - username (str)
                - aliases (list[str])
                - employer (str)
                - city (str)
                - region (str)
                - known_domains (list[str])
                - email (str)
                
        Returns:
            list[str]: Filtered list of queries
        """
        # Validate profile fields and filter against safeguards
        all_text = " ".join([
            str(profile.get(k, '')) for k in ['full_name', 'username', 'employer', 'city', 'region', 'email']
        ])
        
        # Check safeguards
        for kw in SAFEGUARD_KEYWORDS:
            if kw.lower() in all_text.lower():
                logger.warning(f"Safeguard violation: Query text contains blocked keyword '{kw}'. Aborting query generation.")
                return []

        full_name = profile.get('full_name')
        username = profile.get('username')
        aliases = profile.get('aliases') or []
        employer = profile.get('employer')
        city = profile.get('city')
        region = profile.get('region')
        known_domains = profile.get('known_domains') or []
        email = profile.get('email')

        queries = []

        # Helper to extract email domain
        email_domain = None
        if email and '@' in email:
            email_parts = email.split('@')
            if len(email_parts) == 2:
                potential_domain = email_parts[1].lower()
                # Skip common consumer domains like gmail, yahoo, hotmail, outlook
                common_providers = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "live.com"]
                if potential_domain not in common_providers:
                    email_domain = potential_domain

        # Generate Name / Username variants
        names = []
        if full_name:
            names.append(f'"{full_name}"')
        for alias in aliases:
            names.append(f'"{alias}"')

        # 1. Professional presence
        for name in names:
            queries.append(f'{name} site:linkedin.com/in')
        
        # 2. Developer presence
        if username:
            queries.append(f'"{username}" site:github.com')
            queries.append(f'"{username}" site:gitlab.com')
            
        # 3. Forum / Community presence
        if username:
            queries.append(f'"{username}" site:reddit.com')
            queries.append(f'"{username}" site:stackoverflow.com/users')
        for name in names:
            queries.append(f'{name} site:news.ycombinator.com')

        # 4. Document / File exposure (OSINT)
        for name in names:
            queries.append(f'{name} filetype:pdf')
            queries.append(f'{name} (filetype:doc OR filetype:docx OR filetype:xls OR filetype:xlsx)')

        # 5. News / Media mentions
        for name in names:
            queries.append(f'{name} (site:medium.com OR site:substack.com)')
            if employer:
                queries.append(f'{name} "{employer}"')
            if city or region:
                loc = city or region
                queries.append(f'{name} "{loc}"')

        # 6. Public profile pages
        for name in names:
            queries.append(f'{name} (site:youtube.com OR site:tiktok.com)')

        # 7. Reputation / Risk signals (using negative constraints to find other domains)
        if username:
            queries.append(f'"{username}" -site:facebook.com -site:twitter.com')
        for name in names:
            if email_domain:
                queries.append(f'{name} site:{email_domain}')
            for domain in known_domains:
                queries.append(f'{name} site:{domain}')

        # Deduplicate and limit queries based on configuration
        unique_queries = list(dict.fromkeys(queries))
        return unique_queries[:self.max_queries]

    def search_queries(self, queries: list[str]) -> list[dict]:
        """
        Execute searches on the queries using the Google Custom Search JSON API.
        
        Args:
            queries (list[str]): The list of search queries to execute
            
        Returns:
            list[dict]: Merged raw Google CSE search items
        """
        if not self.api_key or not self.cx:
            raise ValueError(
                "Google Custom Search API credentials (GOOGLE_CSE_API_KEY and GOOGLE_CSE_CX) are not configured. "
                "Please configure them in your environment settings."
            )

        all_items = []
        url = "https://www.googleapis.com/customsearch/v1"

        for query in queries:
            logger.info(f"Running Google CSE query: '{query}'")
            params = {
                'key': self.api_key,
                'cx': self.cx,
                'q': query,
                'num': min(self.max_results_per_query, 10)
            }
            try:
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get('items', [])
                    for item in items:
                        # Keep track of which query generated this item
                        item['_origin_query'] = query
                        all_items.append(item)
                else:
                    logger.warning(f"Google CSE search returned error {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Error querying Google CSE: {str(e)}")

        return all_items

    def _get_domain(self, url: str) -> str:
        """Helper to extract domain from a URL."""
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    def normalize_results(self, results: list[dict], profile: dict = None) -> list[dict]:
        """
        Normalize raw Google CSE result items into a consistent format and score them.
        
        Args:
            results (list[dict]): Raw items from search API
            profile (dict, optional): Profile dictionary used to score relevance
            
        Returns:
            list[dict]: Normalized and scored results sorted by score (descending)
        """
        normalized = []
        domain_counts = {}

        profile = profile or {}
        full_name = profile.get('full_name', '')
        username = profile.get('username', '')
        employer = profile.get('employer', '')
        city = profile.get('city', '')
        region = profile.get('region', '')

        for item in results:
            title = item.get('title', '')
            url = item.get('link') or item.get('url', '')
            snippet = item.get('snippet', '')
            query = item.get('_origin_query', '')

            if not url:
                continue

            domain = self._get_domain(url)

            # Filter low-value domains in the blocklist
            if any(block_domain in domain for block_domain in BLOCKLIST_DOMAINS):
                logger.debug(f"Filtering blacklisted domain result: {url}")
                continue

            # Determine category based on URL and query
            category = "likely_misc"
            url_lower = url.lower()
            snippet_lower = snippet.lower()
            title_lower = title.lower()

            if any(x in url_lower for x in ["linkedin.com/in", "github.com/", "gitlab.com/", "facebook.com/", "twitter.com/", "youtube.com/", "tiktok.com/"]):
                category = "likely_profiles"
            elif any(x in url_lower for x in ["reddit.com", "stackoverflow.com", "ycombinator.com"]):
                category = "likely_forums"
            elif url_lower.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx")) or "filetype:" in query:
                category = "likely_documents"
            elif any(x in url_lower for x in ["medium.com", "substack.com"]) or any(x in snippet_lower or x in title_lower for x in ["news", "article", "press release"]):
                category = "likely_media_mentions"

            # Compute Relevance Score
            score = 1.0 # Base score

            # Exact username match
            if username and (username.lower() in url_lower or username.lower() in title_lower):
                score += 5.0

            # Exact full name match
            if full_name and (full_name.lower() in title_lower or f'"{full_name.lower()}"' in title_lower):
                score += 3.0
            elif full_name and all(part.lower() in title_lower for part in full_name.split()):
                score += 1.5

            # Employer and location corroboration
            if employer and employer.lower() in snippet_lower:
                score += 2.0
            if city and city.lower() in snippet_lower:
                score += 2.0
            if region and region.lower() in snippet_lower:
                score += 1.0

            # Source Credibility
            cred_domains = ["github.com", "linkedin.com", "stackoverflow.com", "medium.com", "substack.com", "news.ycombinator.com"]
            if any(cd in domain for cd in cred_domains):
                score += 1.5

            # Duplicate-domain penalty (reduces search spamming from a single domain)
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            if domain_counts[domain] > 1:
                # Apply penalty for each duplicate result from the same domain
                penalty = min(2.5, 0.5 * (domain_counts[domain] - 1))
                score -= penalty

            normalized.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source_domain": domain,
                "query": query,
                "category": category,
                "score": round(max(0.1, score), 2)
            })

        # Sort results by score in descending order
        normalized.sort(key=lambda x: x['score'], reverse=True)
        return normalized

    def cluster_results(self, results: list[dict]) -> dict:
        """
        Group normalized results into separate categories.
        
        Args:
            results (list[dict]): List of normalized results
            
        Returns:
            dict: Clustered lists matching the OSINT categories
        """
        clusters = {
            "likely_profiles": [],
            "likely_forums": [],
            "likely_documents": [],
            "likely_media_mentions": [],
            "likely_misc": []
        }

        for r in results:
            cat = r.get("category", "likely_misc")
            if cat in clusters:
                clusters[cat].append(r)
            else:
                clusters["likely_misc"].append(r)

        return clusters

    def convert_to_posts(self, results: list[dict]) -> list[dict]:
        """
        Convert normalized and scored discovery results into post-like items.
        
        Args:
            results (list[dict]): Normalized results
            
        Returns:
            list[dict]: Standardized posts
        """
        posts = []
        for r in results:
            url = r.get("url", "")
            title = r.get("title", "")
            category = r.get("category", "")
            score = r.get("score", 0.0)
            snippet = r.get("snippet", "")
            
            # Create a unique post ID based on the URL hash
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
            post_id = f"web-{url_hash}"

            content_text = (
                f"Web Discovery Match [Category: {category}, Relevance Score: {score}]\n"
                f"Title: {title}\n"
                f"Snippet: {snippet}"
            )

            posts.append({
                "platform": "web_discovery",
                "post_id": post_id,
                "content": content_text,
                "text": content_text,
                "title": title,
                "author": "Web Discovery",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "source_context": "web_discovery",
                "engagement_score": int(score * 10), # scale score to mock engagement
                "url": url,
                "raw_data": r
            })
            
        return posts

    def scrape_web_discovery(self, profile: dict) -> list[dict]:
        """
        Orchestrates full web discovery workflow.
        
        Args:
            profile (dict): Subject profile
            
        Returns:
            list[dict]: Standard posts ready for downstream consumption
        """
        queries = self.build_queries(profile)
        if not queries:
            logger.info("No queries built or safeguard violation. Returning empty result list.")
            return []

        raw_results = self.search_queries(queries)
        normalized = self.normalize_results(raw_results, profile)
        posts = self.convert_to_posts(normalized)
        return posts
