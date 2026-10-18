import feedparser
from html import unescape
import re
import urllib.request
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Generator, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

THREE_DAYS_IN_SECONDS = 86400 * 1

class RedditCollector:
    """Reddit content collector for fetching and formatting posts"""
    
    # Reddit subreddit configurations
    SUBREDDITS = {
        "CryptoCurrency": "https://www.reddit.com/r/CryptoCurrency/.rss",
        "CryptoMarkets": "https://www.reddit.com/r/CryptoMarkets/.rss",
        "Bitcoin": "https://www.reddit.com/r/Bitcoin/.rss",
        "Ethereum": "https://www.reddit.com/r/Ethereum/.rss",
        "CryptoTechnology": "https://www.reddit.com/r/CryptoTechnology/.rss",
        "CryptoMoonShots": "https://www.reddit.com/r/CryptoMoonShots/.rss",
        "CryptoCurrencyTrading": "https://www.reddit.com/r/CryptoCurrencyTrading/.rss"
    }

    def __init__(self):
        """Initialize the collector with default headers"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }

    def _extract_images(self, content: str) -> List[str]:
        """
        Extract image URLs from content
        
        Args:
            content: Post content text
            
        Returns:
            List of image URLs
        """
        # Match both markdown image syntax and HTML img tags
        markdown_images = re.findall(r'!\[.*?\]\((.*?)\)', content)
        html_images = re.findall(r'<img.*?src="(.*?)"', content)
        return list(set(markdown_images + html_images))

    def _format_comment(self, comment: Dict) -> Dict:
        """
        Format a comment into a standardized structure
        
        Args:
            comment: Raw comment data
            
        Returns:
            Formatted comment dictionary
        """
        return {
            "author": comment.get("author", "Anonymous"),
            "content": comment.get("body", ""),
            "score": comment.get("score", 0),
            "created_utc": comment.get("created_utc", 0),
            "timestamp": datetime.fromtimestamp(
                comment.get("created_utc", 0), 
                timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "replies": [
                self._format_comment(reply) 
                for reply in comment.get("replies", {}).get("data", {}).get("children", [])
                if reply.get("kind") == "t1"
            ] if comment.get("replies") else []
        }

    def analyze_post_detail(self, post_url: str) -> Dict:
        """
        Analyze a single Reddit post in detail, including comments and images
        
        Args:
            post_url: URL of the Reddit post
            
        Returns:
            Dictionary containing detailed post information including:
            - title: Post title
            - content: Post content
            - author: Post author
            - timestamp: Post creation time
            - score: Post score
            - num_comments: Number of comments
            - upvote_ratio: Upvote ratio
            - images: List of image URLs
            - comments: List of formatted comments
            - subreddit: Subreddit name
        """
        try:
            # Convert post URL to JSON API URL
            if not post_url.endswith('.json'):
                post_url = post_url.rstrip('/') + '.json'
            
            # Fetch post data
            req = urllib.request.Request(
                url=post_url,
                headers=self.headers
            )
            response = urllib.request.urlopen(req, timeout=10)
            data = json.loads(response.read())
            
            if not data or len(data) < 2:
                raise ValueError("Invalid post data received")
            
            # Extract post data
            post_data = data[0]['data']['children'][0]['data']
            comments_data = data[1]['data']['children']
            
            # Extract images from content
            content = post_data.get('selftext', '')
            images = self._extract_images(content)
            
            # Format comments
            comments = [
                self._format_comment(comment['data'])
                for comment in comments_data
                if comment.get('kind') == 't1'
            ]
            
            # Format and return post data
            return {
                "title": post_data.get('title', 'No title'),
                "content": content,
                "author": post_data.get('author', 'Anonymous'),
                "timestamp": datetime.fromtimestamp(
                    post_data.get('created_utc', 0), 
                    timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "score": post_data.get('score', 0),
                "num_comments": post_data.get('num_comments', 0),
                "upvote_ratio": post_data.get('upvote_ratio', 0),
                "images": images,
                "comments": comments,
                "subreddit": post_data.get('subreddit', ''),
                "url": post_data.get('url', ''),
                "permalink": f"https://reddit.com{post_data.get('permalink', '')}",
                "id": post_data.get('id', '')
            }
            
        except Exception as e:
            logger.error(f"Error analyzing post {post_url}: {str(e)}")
            return {
                "error": str(e),
                "url": post_url,
                "analyzed_at": datetime.utcnow().isoformat()
            }

    def collect_posts(self, max_posts: int = 5) -> Generator[Dict, None, None]:
        """
        Collect and format posts from configured subreddits
        
        Args:
            max_posts: Maximum number of posts to collect per subreddit
            
        Yields:
            Formatted post data as dictionary
        """
        # Calculate the cutoff time (3 days ago)
        
        for subreddit, url in self.SUBREDDITS.items():
            try:
                # Fetch feed with custom user agent
                req = urllib.request.Request(
                    url=url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                response = urllib.request.urlopen(req, timeout=10)
                feed = feedparser.parse(response)
                
                if not feed or not feed.entries:
                    logger.warning(f"Unable to fetch content from {subreddit}")
                    continue
                
                now_timestamp = datetime.now(timezone.utc).timestamp()

                # Process each entry
                for entry in feed.entries[:max_posts]:
                    # Parse and check timestamp
                    try:
                        timestamp = datetime.strptime(
                            entry.get("published", ""), 
                            "%a, %d %b %Y %H:%M:%S %z"
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        timestamp = entry.get("published", "Unknown time")
                    
                    dt = datetime.fromisoformat(timestamp)
                    post_timestamp = dt.timestamp()

                    # check if timestamp is older than 3 days
                    if now_timestamp - post_timestamp > THREE_DAYS_IN_SECONDS:
                        logger.debug(f"Skipping old post from {subreddit}: {entry.get('title', 'No title')}")
                        continue

                    # Clean HTML content
                    content = unescape(re.sub(r'<[^>]+>', '', entry.get("summary", ""))).strip()
                    
                    # Yield formatted post data
                    yield {
                        "timestamp": timestamp,
                        "title": entry.get("title", "No title"),
                        "link": entry.get("link", "No link"),
                        "author": entry.get("author", "Anonymous"),
                        "content": content,
                        "subreddit": subreddit,
                        "id": entry.get("id", ""),
                        "score": entry.get("score", 0),
                        "num_comments": entry.get("num_comments", 0),
                        "upvote_ratio": entry.get("upvote_ratio", 0),
                        "created_utc": entry.get("created_utc", 0)
                    }
                    
            except Exception as e:
                logger.error(f"Error collecting posts from {subreddit}: {str(e)}")
                continue
