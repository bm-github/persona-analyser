import praw
import json
import os
import sys
from typing import Dict, List, Optional, Generator
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from anthropic import Anthropic

class RedditPersonalityAnalyser:
    def __init__(self):
        self.console = Console()
        self._init_credentials()
        self.cache_dir = "reddit_cache"
        self.history_dir = "chat_history"
        for directory in [self.cache_dir, self.history_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def _init_credentials(self):
        """Separate credentials initialization for better error handling"""
        try:
            with open('../../keys/key-anthropic.txt', 'r') as f:
                anthropic_api_key = f.read().strip()
                if not anthropic_api_key:
                    raise ValueError("Anthropic API key file is empty")
                    
            with open('../../keys/reddit-credentials.json', 'r') as f:
                self.reddit_creds = json.load(f)
                if not all(k in self.reddit_creds for k in ['client_id', 'client_secret', 'user_agent']):
                    raise ValueError("Missing required Reddit API credentials")
                
            self.client = Anthropic(api_key=anthropic_api_key)
            self.reddit = praw.Reddit(
                client_id=self.reddit_creds['client_id'],
                client_secret=self.reddit_creds['client_secret'],
                user_agent=self.reddit_creds['user_agent']
            )
        except Exception as e:
            raise Exception(f"Credentials initialization failed: {str(e)}")

    def get_cache_path(self, username: str) -> str:
        """Get the path for the user's cache file."""
        return os.path.join(self.cache_dir, f"{username}.json")

    def get_history_path(self, username: str) -> str:
        """Get the path for the user's chat history file."""
        return os.path.join(self.history_dir, f"{username}_history.json")

    def load_cached_data(self, username: str) -> Optional[Dict]:
        """Load cached Reddit data from file."""
        cache_path = self.get_cache_path(username)
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
        return None

    def save_to_cache(self, username: str, data: Dict):
        """Save Reddit data to cache file."""
        cache_path = self.get_cache_path(username)
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)

    def fetch_all_submissions(self, redditor: praw.models.Redditor) -> Generator[Dict, None, None]:
        """Fetch submissions for a user using pagination with reduced fields."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Fetching submissions...", total=None)
                for submission in redditor.submissions.new(limit=100):  # Limited to 100 most recent
                    progress.update(task, advance=1)
                    yield {
                        'title': submission.title,
                        'selftext': submission.selftext[:1000],  # Limit content length
                        'subreddit': submission.subreddit.display_name,
                        'created_utc': submission.created_utc,
                        'score': submission.score,
                        'num_comments': submission.num_comments
                    }
        except Exception as e:
            self.console.print(f"[red]Error fetching submissions: {e}[/red]")
            return

    def fetch_all_comments(self, redditor: praw.models.Redditor) -> Generator[Dict, None, None]:
        """Fetch comments for a user using pagination with reduced fields."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Fetching comments...", total=None)
                for comment in redditor.comments.new(limit=100):  # Limited to 100 most recent
                    progress.update(task, advance=1)
                    yield {
                        'body': comment.body[:1000],  # Limit content length
                        'subreddit': comment.subreddit.display_name,
                        'score': comment.score,
                        'created_utc': comment.created_utc
                    }
        except Exception as e:
            self.console.print(f"[red]Error fetching comments: {e}[/red]")
            return

    def extract_post_data(self, data: Dict, max_items: int = 25) -> str:
        """Format user data for analysis with improved efficiency."""
        content_parts = []
        
        # Add statistics section
        stats = data['statistics']
        content_parts.append(f"User Activity Analysis for u/{data['username']}\n")
        content_parts.append("OVERVIEW:")
        content_parts.append(f"Total Submissions: {stats['total_submissions']}")
        content_parts.append(f"Total Comments: {stats['total_comments']}")
        content_parts.append("\nTop Active Subreddits:")
        
        # Limit to top 5 subreddits for more focused analysis
        for sub, count in list(stats['top_subreddits'].items())[:5]:
            content_parts.append(f"- r/{sub}: {count} posts/comments")
        
        # Add most recent and highest-scoring submissions
        submissions = sorted(
            data['submissions'],
            key=lambda x: x.get('score', 0),
            reverse=True
        )[:max_items]
        
        content_parts.append("\nTOP SUBMISSIONS:")
        for submission in submissions:
            date = datetime.fromtimestamp(submission['created_utc']).strftime('%Y-%m-%d')
            content_parts.append(
                f"\nDate: {date}\n"
                f"Title: {submission['title']}\n"
                f"Subreddit: r/{submission['subreddit']}\n"
                f"Score: {submission.get('score', 0)}"
            )
            if submission.get('selftext'):
                content_parts.append(f"Content: {submission['selftext'][:500]}...")
        
        # Add highest-scoring comments
        comments = sorted(
            data['comments'],
            key=lambda x: x.get('score', 0),
            reverse=True
        )[:max_items]
        
        content_parts.append("\nTOP COMMENTS:")
        for comment in comments:
            date = datetime.fromtimestamp(comment['created_utc']).strftime('%Y-%m-%d')
            content_parts.append(
                f"\nDate: {date}\n"
                f"Subreddit: r/{comment['subreddit']}\n"
                f"Score: {comment.get('score', 0)}\n"
                f"Content: {comment['body'][:500]}..."
            )
        
        return "\n".join(content_parts)

    def analyse_with_claude(self, username: str, question: str) -> str:
        """Optimized analysis using Claude."""
        data = self.fetch_user_data(username)
        if not data:
            return "Unable to fetch user data."
        
        formatted_data = self.extract_post_data(data)
        
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                temperature=0.7,
                system="Analyze Reddit user activity focusing on key patterns in behavior, interests, and communication style. "
                       "Provide concise, data-driven insights.",
                messages=[{
                    "role": "user",
                    "content": f"Analyze u/{username}'s Reddit activity to answer: {question}\n\n{formatted_data}"
                }]
            )
            return message.content[0].text
        except Exception as e:
            self.console.print(f"[red]Error calling Anthropic API: {e}[/red]")
            return f"Error analysing data: {str(e)}"

    def fetch_user_data(self, username: str, force_refresh: bool = False) -> Optional[Dict]:
        """Optimized user data fetching with smart caching."""
        if not force_refresh:
            cached_data = self.load_cached_data(username)
            if cached_data:
                cache_age = datetime.now() - datetime.fromisoformat(cached_data['fetch_time'])
                if cache_age.days < 1:
                    self.console.print("[green]Using cached data (less than 24 hours old)[/green]")
                    return cached_data
                else:
                    self.console.print("[yellow]Cache is over 24 hours old. Refreshing...[/yellow]")
            else:
                self.console.print("[yellow]No cached data found. Fetching new data...[/yellow]")
        else:
            self.console.print("[yellow]Force refresh requested. Fetching new data...[/yellow]")

        try:
            redditor = self.reddit.redditor(username)
            _ = redditor.created_utc  # Verify user exists
            
            submissions_data = list(self.fetch_all_submissions(redditor))
            comments_data = list(self.fetch_all_comments(redditor))
            
            # Calculate subreddit activity
            subreddit_activity = {}
            for item in submissions_data + comments_data:
                subreddit = item['subreddit']
                subreddit_activity[subreddit] = subreddit_activity.get(subreddit, 0) + 1
            
            data = {
                'submissions': submissions_data,
                'comments': comments_data,
                'username': username,
                'fetch_time': datetime.now().isoformat(),
                'statistics': {
                    'total_submissions': len(submissions_data),
                    'total_comments': len(comments_data),
                    'top_subreddits': dict(sorted(
                        subreddit_activity.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:5])
                }
            }
            
            self.save_to_cache(username, data)
            self.console.print(f"[green]Successfully fetched and cached data:[/green]")
            self.console.print(f"- Total submissions: {len(submissions_data)}")
            self.console.print(f"- Total comments: {len(comments_data)}")
            self.console.print("- Top active subreddits:")
            for sub, count in data['statistics']['top_subreddits'].items():
                self.console.print(f"  • r/{sub}: {count} posts/comments")
            
            return data
            
        except Exception as e:
            self.console.print(f"[red]Error fetching data: {e}[/red]")
            return None

    def interactive_session(self, username: str):
        """Streamlined interactive analysis session."""
        console = self.console
        
        console.print(Panel.fit(
            f"[bold blue]Analysis Session for u/{username}[/bold blue]\n"
            "Commands: 'exit', 'refresh', 'help'",
            title="Reddit Analyzer",
            border_style="blue"
        ))
        
        while True:
            question = console.input("\n[bold cyan]Question about user:[/bold cyan] ")
            
            match question.lower():
                case 'exit':
                    break
                case 'refresh':
                    if self.fetch_user_data(username, force_refresh=True):
                        console.print("[green]Data refreshed![/green]")
                    continue
                case 'help':
                    console.print(Panel(
                        "Commands:\n"
                        "exit - End session\n"
                        "refresh - Update user data\n"
                        "help - Show this message",
                        title="Help",
                        border_style="blue"
                    ))
                    continue
                    
            try:
                console.print("[yellow]Analyzing...[/yellow]")
                analysis = self.analyse_with_claude(username, question)
                console.print(Panel(Markdown(analysis), border_style="green"))
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

def main():
    console = Console()
    
    console.print(Panel.fit(
        "[bold blue]Reddit Personality Analyser[/bold blue]\n"
        "This tool analyzes Reddit users' activity and provides insights.",
        border_style="blue"
    ))
    
    while True:
        username = console.input("\n[bold cyan]Enter Reddit username to analyse (or 'exit' to quit):[/bold cyan] ")
        
        if username.lower() == 'exit':
            break
            
        analyser = RedditPersonalityAnalyser()
        analyser.interactive_session(username)

if __name__ == "__main__":
    main()