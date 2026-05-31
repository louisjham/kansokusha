import requests
import logging
import os
from flask import current_app
from app.models import get_setting

logger = logging.getLogger(__name__)

class YoutubeService:
    """Service for interacting with the YouTube Data API v3."""

    def __init__(self):
        """Initialize YouTube API v3 service."""
        self.api_key = get_setting('YOUTUBE_API_KEY', None)
        if not self.api_key:
            try:
                self.api_key = current_app.config.get('YOUTUBE_API_KEY')
            except Exception:
                self.api_key = os.environ.get('YOUTUBE_API_KEY')

        if self.api_key:
            logger.info("YouTube service initialized with API Key.")
        else:
            logger.warning("YouTube service initialized without API Key. API calls will fail.")

    def _resolve_channel_id(self, query: str) -> str:
        """Resolve YouTube channel ID using search.list if query appears to be a URL or name."""
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY is not configured.")

        # Check if query is already a valid channel ID (starts with 'UC' and is 24 chars)
        if query.startswith('UC') and len(query) == 24 and '/' not in query:
            return query

        # Parse handles or names if it looks like a URL
        search_query = query
        if 'youtube.com' in query or 'youtu.be' in query:
            parts = query.rstrip('/').split('/')
            last_part = parts[-1]
            if last_part.startswith('@'):
                search_query = last_part
            elif 'channel' in parts:
                idx = parts.index('channel')
                if idx + 1 < len(parts):
                    potential_id = parts[idx+1]
                    if potential_id.startswith('UC'):
                        return potential_id
            elif 'c' in parts:
                idx = parts.index('c')
                if idx + 1 < len(parts):
                    search_query = parts[idx+1]
            elif 'user' in parts:
                idx = parts.index('user')
                if idx + 1 < len(parts):
                    search_query = parts[idx+1]
            else:
                search_query = last_part

        # Call search.list to find the channel
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': search_query,
            'type': 'channel',
            'maxResults': 1,
            'key': self.api_key
        }
        
        logger.info(f"Resolving YouTube channel ID via search.list for query: '{search_query}'")
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items', [])
        
        if not items:
            raise ValueError(f"Could not find YouTube channel matching: '{query}'")
        
        channel_id = items[0].get('id', {}).get('channelId')
        if not channel_id:
            raise ValueError(f"No channel ID found in search results for: '{query}'")
        
        return channel_id

    def scrape_youtube_activity(self, channel_url_or_id: str):
        """
        Scrape YouTube channel uploads and video comments.
        
        Args:
            channel_url_or_id (str): YouTube channel URL or raw channel ID
            
        Returns:
            list: Processed video/comment posts standard list
        """
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY is not configured.")

        # 1. Resolve channel ID
        channel_id = self._resolve_channel_id(channel_url_or_id)
        logger.info(f"Resolved channel ID to: {channel_id}")

        # 2. Get uploads playlist ID using channels.list
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            'part': 'contentDetails,snippet',
            'id': channel_id,
            'key': self.api_key
        }
        
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items', [])
        if not items:
            raise ValueError(f"YouTube channel ID '{channel_id}' not found.")

        channel_title = items[0].get('snippet', {}).get('title', 'Unknown Channel')
        uploads_playlist_id = items[0].get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
        if not uploads_playlist_id:
            raise ValueError(f"No uploads playlist found for channel ID '{channel_id}'.")

        logger.info(f"Found uploads playlist ID: {uploads_playlist_id} for channel: '{channel_title}'")

        posts = []

        # 3. Retrieve latest 50 video uploads using playlistItems.list
        playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
        playlist_params = {
            'part': 'snippet',
            'playlistId': uploads_playlist_id,
            'maxResults': 50,
            'key': self.api_key
        }
        
        resp = requests.get(playlist_url, params=playlist_params, timeout=15)
        resp.raise_for_status()
        videos = resp.json().get('items', [])
        logger.info(f"Retrieved {len(videos)} videos from uploads playlist.")

        for video in videos:
            snippet = video.get('snippet', {})
            video_id = snippet.get('resourceId', {}).get('videoId')
            title = snippet.get('title', '')
            description = snippet.get('description', '')
            published_at = snippet.get('publishedAt')

            if not video_id:
                continue

            # Create post entry for video description
            video_post = {
                'platform': 'youtube',
                'post_id': f"video-{video_id}",
                'content': f"Video Upload: {title}\nDescription: {description}",
                'text': f"Video Upload: {title}\nDescription: {description}",
                'author': channel_title,
                'timestamp': published_at,
                'created_at': published_at,
                'source_context': 'youtube',
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'raw_data': video
            }
            posts.append(video_post)

            # 4. Fetch top-level comments using commentThreads.list
            try:
                comments_url = "https://www.googleapis.com/youtube/v3/commentThreads"
                comments_params = {
                    'part': 'snippet',
                    'videoId': video_id,
                    'maxResults': 20,
                    'key': self.api_key
                }
                c_resp = requests.get(comments_url, params=comments_params, timeout=10)
                if c_resp.status_code == 200:
                    threads = c_resp.json().get('items', [])
                    for thread in threads:
                        tlc = thread.get('snippet', {}).get('topLevelComment', {})
                        c_id = tlc.get('id')
                        c_snippet = tlc.get('snippet', {})
                        author = c_snippet.get('authorDisplayName', 'Unknown')
                        text = c_snippet.get('textOriginal') or c_snippet.get('textDisplay', '')
                        likes = c_snippet.get('likeCount', 0)
                        published = c_snippet.get('publishedAt')

                        comment_post = {
                            'platform': 'youtube',
                            'post_id': f"comment-{c_id}",
                            'content': f"Comment by {author} on video '{title}':\n{text}",
                            'text': f"Comment by {author} on video '{title}':\n{text}",
                            'author': author,
                            'timestamp': published,
                            'created_at': published,
                            'source_context': 'youtube',
                            'engagement_score': likes,
                            'like_count': likes,
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'raw_data': thread
                        }
                        posts.append(comment_post)
                else:
                    logger.warning(f"Could not fetch comments for video {video_id}: Status {c_resp.status_code}")
            except Exception as comment_err:
                logger.warning(f"Error fetching comments for video {video_id}: {str(comment_err)}")

        logger.info(f"Aggregated {len(posts)} posts for YouTube channel {channel_id}")
        return posts
