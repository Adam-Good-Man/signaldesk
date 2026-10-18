import tweepy
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Generator, List
import logging
import re
import json
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

THREE_DAYS_IN_SECONDS = 86400 * 1

class TwitterCollector:
    """Twitter content collector for fetching and formatting tweets"""
    
    # Twitter search configurations
    SEARCH_QUERIES = [
        "crypto OR cryptocurrency OR bitcoin OR ethereum",
        "defi OR web3 OR blockchain",
        "crypto trading OR crypto market",
        "crypto news OR crypto update",
        "crypto analysis OR crypto technical"
    ]

    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str):
        """
        Initialize the collector with Twitter API credentials
        
        Args:
            api_key: Twitter API Key
            api_secret: Twitter API Secret
            access_token: Twitter Access Token
            access_token_secret: Twitter Access Token Secret
        """
        try:
            # Initialize Twitter API client
            auth = tweepy.OAuthHandler(api_key, api_secret)
            auth.set_access_token(access_token, access_token_secret)
            self.api = tweepy.API(auth, wait_on_rate_limit=True)
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
        except Exception as e:
            logger.error(f"Error initializing Twitter API: {str(e)}")
            raise

    def _extract_media(self, tweet: Dict) -> List[str]:
        """
        Extract media URLs from tweet
        
        Args:
            tweet: Tweet data dictionary
            
        Returns:
            List of media URLs
        """
        media_urls = []
        if 'extended_entities' in tweet and 'media' in tweet['extended_entities']:
            for media in tweet['extended_entities']['media']:
                if media['type'] == 'photo':
                    media_urls.append(media['media_url_https'])
                elif media['type'] == 'video':
                    # Get the highest quality video URL
                    variants = media.get('video_info', {}).get('variants', [])
                    if variants:
                        # Sort by bitrate and get the highest quality
                        video_variant = sorted(
                            [v for v in variants if v.get('content_type') == 'video/mp4'],
                            key=lambda x: x.get('bitrate', 0),
                            reverse=True
                        )[0]
                        media_urls.append(video_variant['url'])
        return media_urls

    def _format_reply(self, reply: Dict) -> Dict:
        """
        Format a reply into a standardized structure
        
        Args:
            reply: Raw reply data
            
        Returns:
            Formatted reply dictionary
        """
        return {
            "author": reply.get("user", {}).get("screen_name", "Anonymous"),
            "content": reply.get("full_text", ""),
            "likes": reply.get("favorite_count", 0),
            "retweets": reply.get("retweet_count", 0),
            "created_at": reply.get("created_at", ""),
            "timestamp": datetime.strptime(
                reply.get("created_at", ""), 
                "%a %b %d %H:%M:%S %z %Y"
            ).strftime("%Y-%m-%d %H:%M:%S") if reply.get("created_at") else "",
            "replies": []  # Twitter API doesn't provide nested replies easily
        }

    def analyze_tweet_detail(self, tweet_url: str) -> Dict:
        """
        Analyze a single tweet in detail, including replies and media
        
        Args:
            tweet_url: URL of the tweet
            
        Returns:
            Dictionary containing detailed tweet information including:
            - text: Tweet content
            - author: Tweet author
            - timestamp: Tweet creation time
            - likes: Number of likes
            - retweets: Number of retweets
            - replies: Number of replies
            - media: List of media URLs
            - replies: List of formatted replies
            - hashtags: List of hashtags
            - mentions: List of user mentions
        """
        try:
            # Extract tweet ID from URL
            tweet_id = tweet_url.split('/')[-1]
            
            # Fetch tweet data
            tweet = self.api.get_status(
                tweet_id,
                tweet_mode='extended',
                include_entities=True
            )._json
            
            # Get replies (using search API as a workaround)
            replies = []
            query = f"to:{tweet['user']['screen_name']}"
            for reply in tweepy.Cursor(
                self.api.search_tweets,
                q=query,
                since_id=tweet_id,
                tweet_mode='extended'
            ).items(100):  # Limit to 100 replies
                if reply.in_reply_to_status_id_str == tweet_id:
                    replies.append(self._format_reply(reply._json))
            
            # Extract hashtags and mentions
            hashtags = [tag['text'] for tag in tweet.get('entities', {}).get('hashtags', [])]
            mentions = [mention['screen_name'] for mention in tweet.get('entities', {}).get('user_mentions', [])]
            
            # Extract media
            media = self._extract_media(tweet)
            
            # Format and return tweet data
            return {
                "text": tweet.get('full_text', ''),
                "author": tweet.get('user', {}).get('screen_name', 'Anonymous'),
                "timestamp": datetime.strptime(
                    tweet.get('created_at', ''), 
                    "%a %b %d %H:%M:%S %z %Y"
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "likes": tweet.get('favorite_count', 0),
                "retweets": tweet.get('retweet_count', 0),
                "replies_count": tweet.get('reply_count', 0),
                "media": media,
                "replies": replies,
                "hashtags": hashtags,
                "mentions": mentions,
                "url": tweet_url,
                "id": tweet_id,
                "author_followers": tweet.get('user', {}).get('followers_count', 0),
                "author_verified": tweet.get('user', {}).get('verified', False)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing tweet {tweet_url}: {str(e)}")
            return {
                "error": str(e),
                "url": tweet_url,
                "analyzed_at": datetime.utcnow().isoformat()
            }

    def collect_tweets(self, max_tweets: int = 5) -> Generator[Dict, None, None]:
        """
        Collect and format tweets from configured search queries
        
        Args:
            max_tweets: Maximum number of tweets to collect per query
            
        Yields:
            Formatted tweet data as dictionary
        """
        now_timestamp = datetime.now(timezone.utc).timestamp()
        
        for query in self.SEARCH_QUERIES:
            try:
                # Search tweets
                tweets = tweepy.Cursor(
                    self.api.search_tweets,
                    q=query,
                    tweet_mode='extended',
                    lang='en',
                    result_type='mixed'  # Include both popular and recent tweets
                ).items(max_tweets)
                
                for tweet in tweets:
                    tweet_data = tweet._json
                    
                    # Parse and check timestamp
                    created_at = datetime.strptime(
                        tweet_data.get('created_at', ''), 
                        "%a %b %d %H:%M:%S %z %Y"
                    )
                    tweet_timestamp = created_at.timestamp()
                    
                    # Check if tweet is older than 3 days
                    if now_timestamp - tweet_timestamp > THREE_DAYS_IN_SECONDS:
                        logger.debug(f"Skipping old tweet: {tweet_data.get('full_text', 'No text')[:50]}...")
                        continue
                    
                    # Extract media
                    media = self._extract_media(tweet_data)
                    
                    # Extract hashtags and mentions
                    hashtags = [tag['text'] for tag in tweet_data.get('entities', {}).get('hashtags', [])]
                    mentions = [mention['screen_name'] for mention in tweet_data.get('entities', {}).get('user_mentions', [])]
                    
                    # Yield formatted tweet data
                    yield {
                        "timestamp": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "text": tweet_data.get('full_text', ''),
                        "link": f"https://twitter.com/{tweet_data.get('user', {}).get('screen_name', '')}/status/{tweet_data.get('id_str', '')}",
                        "author": tweet_data.get('user', {}).get('screen_name', 'Anonymous'),
                        "content": tweet_data.get('full_text', ''),
                        "hashtags": hashtags,
                        "mentions": mentions,
                        "id": tweet_data.get('id_str', ''),
                        "likes": tweet_data.get('favorite_count', 0),
                        "retweets": tweet_data.get('retweet_count', 0),
                        "replies": tweet_data.get('reply_count', 0),
                        "media": media,
                        "author_followers": tweet_data.get('user', {}).get('followers_count', 0),
                        "author_verified": tweet_data.get('user', {}).get('verified', False)
                    }
                    
            except Exception as e:
                logger.error(f"Error collecting tweets for query '{query}': {str(e)}")
                continue
