from src.radar.twitter import TwitterCollector
import logging
import json
from datetime import datetime
import os
from dotenv import load_dotenv

def print_tweet_analysis(analysis: dict) -> None:
    """Print tweet analysis results in a formatted way"""
    print("\n" + "="*100)
    print("🔍 DETAILED TWEET ANALYSIS")
    print("="*100)
    
    # Print tweet metadata
    print("\n📰 TWEET INFORMATION")
    print("-"*100)
    print(f"Author: {analysis.get('author', 'N/A')}")
    print(f"Posted: {analysis.get('timestamp', 'N/A')}")
    print(f"URL: {analysis.get('url', 'N/A')}")
    print(f"Verified: {'✅' if analysis.get('author_verified') else '❌'}")
    print(f"Followers: {analysis.get('author_followers', 'N/A'):,}")
    
    # Print content and engagement
    print("\n📝 CONTENT & ENGAGEMENT")
    print("-"*100)
    print(f"Content: {analysis.get('text', 'N/A')}")
    print(f"\nEngagement Metrics:")
    print(f"• Likes: {analysis.get('likes', 0):,}")
    print(f"• Retweets: {analysis.get('retweets', 0):,}")
    print(f"• Replies: {analysis.get('replies_count', 0):,}")
    
    # Print hashtags and mentions
    print("\n🏷️ HASHTAGS & MENTIONS")
    print("-"*100)
    hashtags = analysis.get('hashtags', [])
    if hashtags:
        print("Hashtags:")
        for tag in hashtags:
            print(f"• #{tag}")
    
    mentions = analysis.get('mentions', [])
    if mentions:
        print("\nMentions:")
        for mention in mentions:
            print(f"• @{mention}")
    
    # Print media
    print("\n🖼️ MEDIA")
    print("-"*100)
    media = analysis.get('media', [])
    if media:
        for url in media:
            print(f"• {url}")
    else:
        print("No media attached")
    
    # Print replies
    print("\n💬 REPLIES")
    print("-"*100)
    replies = analysis.get('replies', [])
    if replies:
        for reply in replies[:5]:  # Show top 5 replies
            print(f"\n@{reply['author']} ({reply['timestamp']}):")
            print(f"• {reply['content']}")
            print(f"• Likes: {reply['likes']:,} | Retweets: {reply['retweets']:,}")
    else:
        print("No replies found")
    
    print("\n" + "="*100)

def main():
    # Load environment variables
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Get Twitter API credentials
    api_key = os.getenv('TWITTER_API_KEY')
    api_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

    if not all([api_key, api_secret, access_token, access_token_secret]):
        logger.error("Twitter API credentials not found in environment variables")
        return

    try:
        # Create Twitter collector instance
        collector = TwitterCollector(
            api_key=api_key,
            api_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Collect tweets
        logger.info("Starting tweet collection...")
        tweets = list(collector.collect_tweets(max_tweets=5))
        
        if not tweets:
            logger.warning("No tweets collected")
            return
            
        # Print collection summary
        print("\n" + "="*100)
        print("📊 TWEET COLLECTION SUMMARY")
        print("="*100)
        print(f"Total tweets collected: {len(tweets)}")
        print(f"Collection timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Analyze each tweet in detail
        for tweet in tweets:
            try:
                logger.info(f"Analyzing tweet: {tweet['link']}")
                analysis = collector.analyze_tweet_detail(tweet['link'])
                
                if "error" in analysis:
                    logger.error(f"Analysis failed: {analysis['error']}")
                    continue
            
        # Print analysis results
                print_tweet_analysis(analysis)
                
            except Exception as e:
                logger.error(f"Error analyzing tweet {tweet.get('link', 'unknown')}: {str(e)}")
                continue
        
        # Save full analysis to JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"twitter_analysis_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "collection_timestamp": datetime.now().isoformat(),
                "total_tweets": len(tweets),
                "tweets": tweets
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"Full analysis saved to {filename}")
            
    except Exception as e:
        logger.error(f"Error during tweet collection and analysis: {str(e)}")

if __name__ == "__main__":
    main()
