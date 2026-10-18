from typing import Dict, Optional
from openai import OpenAI
import logging
from datetime import datetime
import json
from src.radar.reddit import RedditCollector

class RedditAnalyzer:
    """Analyzer for Reddit posts using GPT to evaluate post value"""
    
    def __init__(self, api_key: str):
        """
        Initialize the analyzer with OpenAI API key
        
        Args:
            api_key: OpenAI API key
        """
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)
        self.collector = RedditCollector()

    def analyze_post(self, post: Dict) -> Dict:
        """
        Analyze a Reddit post using GPT to determine its value and extract insights
        
        Args:
            post: Dictionary containing post data from RedditCollector
            
        Returns:
            Dictionary containing analysis results including:
            - value_score: float (0-1) indicating post value
            - sentiment: str (positive/negative/neutral)
            - key_points: list of main points
            - market_impact: str (high/medium/low)
            - analysis_summary: str
        """
        try:
            # Prepare the prompt for GPT with explicit JSON format
            prompt = f"""Analyze this Reddit post about cryptocurrency and provide a detailed analysis in JSON format.
The response must be a valid JSON object with exactly these fields:
- value_score (float between 0 and 1)
- sentiment (string: "positive", "negative", or "neutral")
- key_points (array of strings)
- market_impact (string: "high", "medium", or "low")
- analysis_summary (string)

Post details:
Title: {post['title']}
Subreddit: {post['subreddit']}
Author: {post['author']}
Score: {post['score']}
Comments: {post['num_comments']}
Upvote Ratio: {post['upvote_ratio']}
Content: {post['content']}

Scoring criteria:
1. Content Quality (0-0.3):
   - 0.3: Original, in-depth technical analysis
   - 0.2: Deep discussion or analysis
   - 0.1: General discussion or news sharing
   - 0.0: Low quality or spam

2. Timeliness (0-0.2):
   - 0.2: Latest market dynamics (within 24h)
   - 0.15: Recent important updates (1-2 days)
   - 0.1: General timely content (2-3 days)
   - 0.0: Outdated information

3. Community Engagement (0-0.2):
   - 0.2: High engagement (comments>100, high upvote ratio)
   - 0.15: Medium engagement (50-100 comments)
   - 0.1: Low engagement (<50 comments)
   - 0.0: No engagement

4. Market Impact (0-0.2):
   - 0.2: Potential major market impact
   - 0.15: Important impact on specific coin
   - 0.1: General market information
   - 0.0: No market impact

5. Credibility (0-0.1):
   - 0.1: High credibility (official info, known analysts)
   - 0.05: General credibility
   - 0.0: Low credibility or unverified

Respond with ONLY the JSON object, no other text."""

            # Call GPT API using new interface
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a cryptocurrency market analyst. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={ "type": "json_object" }  # Force JSON response
            )

            # Parse GPT response
            analysis_text = response.choices[0].message.content.strip()
            self.logger.debug(f"Raw GPT response: {analysis_text}")  # Debug log
            
            try:
                analysis = json.loads(analysis_text)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parsing error: {str(e)}, Raw response: {analysis_text}")
                raise

            # Validate required fields
            required_fields = ['value_score', 'sentiment', 'key_points', 'market_impact', 'analysis_summary']
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")

            # Add metadata
            analysis.update({
                "post_id": post['id'],
                "analyzed_at": datetime.utcnow().isoformat(),
                "original_post": {
                    "title": post['title'],
                    "subreddit": post['subreddit'],
                    "timestamp": post['timestamp']
                }
            })

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing post {post.get('id', 'unknown')}: {str(e)}")
            return {
                "error": str(e),
                "post_id": post.get('id', 'unknown'),
                "analyzed_at": datetime.utcnow().isoformat(),
                "value_score": 0.0,
                "sentiment": "neutral",
                "key_points": [],
                "market_impact": "low",
                "analysis_summary": "Analysis failed due to an error"
            }

    def analyze_post_content(self, post_url: str) -> Dict:
        """
        Deeply analyze a single Reddit post's content, including comments and community response
        
        Args:
            post_url: URL of the Reddit post to analyze
            
        Returns:
            Dictionary containing detailed analysis including:
            - post_summary: Overall summary of the post
            - key_points: Main points from the post
            - sentiment_analysis: Overall sentiment and community reaction
            - technical_analysis: Technical aspects discussed
            - market_impact: Potential market implications
            - community_insights: Key insights from comments
            - credibility_score: Post credibility assessment
            - trending_topics: Related topics or trends mentioned
            - risk_factors: Any risks or concerns mentioned
            - action_items: Suggested actions or takeaways
        """
        try:
            # Get post details
            post_data = self.collector.analyze_post_detail(post_url)
            if "error" in post_data:
                raise ValueError(f"Failed to fetch post data: {post_data['error']}")

            # Prepare the analysis prompt
            prompt = f"""Analyze this Reddit post about cryptocurrency in detail. Consider both the post content and community response.

Post Title: {post_data['title']}
Subreddit: {post_data['subreddit']}
Author: {post_data['author']}
Score: {post_data['score']}
Comments: {post_data['num_comments']}
Upvote Ratio: {post_data['upvote_ratio']}

Content:
{post_data['content']}

Top Comments Summary:
{self._summarize_comments(post_data['comments'][:5])}

Please provide a comprehensive analysis in JSON format with these exact fields:
{{
    "post_summary": "Brief summary of the post's main message",
    "key_points": ["List of main points from the post"],
    "sentiment_analysis": {{
        "overall_sentiment": "positive/negative/neutral",
        "community_reaction": "Description of how the community is reacting",
        "confidence_score": float between 0 and 1
    }},
    "technical_analysis": {{
        "technical_depth": "high/medium/low",
        "technical_points": ["List of technical aspects discussed"],
        "accuracy_assessment": "Assessment of technical accuracy"
    }},
    "market_impact": {{
        "potential_impact": "high/medium/low",
        "affected_areas": ["List of market areas that might be affected"],
        "timeframe": "short-term/mid-term/long-term"
    }},
    "community_insights": {{
        "main_concerns": ["List of main concerns from comments"],
        "community_sentiment": "Description of community sentiment",
        "notable_opinions": ["List of notable opinions from comments"]
    }},
    "credibility_score": {{
        "score": float between 0 and 1,
        "factors": ["List of factors affecting credibility"],
        "verification_status": "verified/unverified/partially_verified"
    }},
    "trending_topics": ["List of related topics or trends mentioned"],
    "risk_factors": ["List of potential risks or concerns"],
    "action_items": ["List of suggested actions or takeaways"]
}}

Respond with ONLY the JSON object, no other text."""

            # Call GPT API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a cryptocurrency market analyst specializing in social media analysis. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                response_format={ "type": "json_object" }
            )

            # Parse and validate response
            analysis_text = response.choices[0].message.content.strip()
            analysis = json.loads(analysis_text)

            # Add metadata
            analysis.update({
                "post_id": post_data['id'],
                "analyzed_at": datetime.utcnow().isoformat(),
                "post_metadata": {
                    "title": post_data['title'],
                    "subreddit": post_data['subreddit'],
                    "author": post_data['author'],
                    "timestamp": post_data['timestamp'],
                    "url": post_data['permalink']
                }
            })

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing post content {post_url}: {str(e)}")
            return {
                "error": str(e),
                "post_url": post_url,
                "analyzed_at": datetime.utcnow().isoformat()
            }

    def _summarize_comments(self, comments: list, max_length: int = 200) -> str:
        """
        Create a summary of top comments
        
        Args:
            comments: List of comment dictionaries
            max_length: Maximum length for each comment summary
            
        Returns:
            String containing summarized comments
        """
        summary = []
        for comment in comments:
            content = comment['content']
            if len(content) > max_length:
                content = content[:max_length] + "..."
            summary.append(f"User {comment['author']} ({comment['score']} points): {content}")
        return "\n".join(summary)

    def analyze_posts_batch(self, max_posts: int = 10) -> Dict:
        """
        Analyze a batch of Reddit posts, filtering out low impact posts and performing deep analysis
        on the remaining ones.
        
        Args:
            max_posts: Maximum number of posts to collect and analyze
            
        Returns:
            Dictionary containing:
            - total_posts: Total number of posts collected
            - filtered_posts: Number of posts after filtering
            - analyzed_posts: List of detailed analysis for each high-impact post
            - analysis_timestamp: When the analysis was performed
        """
        try:
            # Collect posts and convert generator to list
            posts_generator = self.collector.collect_posts(max_posts=max_posts)
            posts = list(posts_generator)  # Convert generator to list
            
            if not posts:
                self.logger.warning("No posts collected")
                return {
                    "total_posts": 0,
                    "filtered_posts": 0,
                    "analyzed_posts": [],
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }

            # Initial analysis and filtering
            filtered_posts = []
            for post in posts:
                try:
                    analysis = self.analyze_post(post)
                    if analysis.get("market_impact", "low") != "low":
                        filtered_posts.append({
                            "post": post,
                            "initial_analysis": analysis
                        })
                except Exception as e:
                    self.logger.error(f"Error in initial analysis of post {post.get('id', 'unknown')}: {str(e)}")
                    continue

            # Deep analysis of filtered posts
            analyzed_posts = []
            
            print(f"### Filtered posts length: {len(filtered_posts)}")

            for filtered_post in filtered_posts:
                try:
                    post_url = filtered_post["post"].get("link")
                    if not post_url:
                        continue
                        
                    deep_analysis = self.analyze_post_content(post_url)
                    analyzed_posts.append({
                        "post_id": filtered_post["post"]["id"],
                        "initial_analysis": filtered_post["initial_analysis"],
                        "deep_analysis": deep_analysis
                    })
                except Exception as e:
                    self.logger.error(f"Error in deep analysis of post {filtered_post['post'].get('id', 'unknown')}: {str(e)}")
                    continue

            return {
                "total_posts": len(posts),
                "filtered_posts": len(filtered_posts),
                "analyzed_posts": analyzed_posts,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error in batch analysis: {str(e)}")
            return {
                "error": str(e),
                "total_posts": 0,
                "filtered_posts": 0,
                "analyzed_posts": [],
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
