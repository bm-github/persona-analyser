import praw
import json
import os
import sys
import argparse
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
        
        try:
            with open('../../keys/key.txt', 'r') as f:
                anthropic_api_key = f.read().strip()
                if not anthropic_api_key:
                    raise ValueError("Anthropic API key file is empty")
                    
            with open('../../keys/reddit-credentials.json', 'r') as f:
                reddit_creds = json.load(f)
                if not all(k in reddit_creds for k in ['client_id', 'client_secret', 'user_agent']):
                    raise ValueError("Missing required Reddit API credentials")
                
        except FileNotFoundError as e:
            raise Exception(f"Credentials file not found: {str(e)}")
        except Exception as e:
            raise Exception(f"Error reading credentials: {str(e)}")
        
        try:
            self.client = Anthropic(api_key=anthropic_api_key)
        except Exception as e:
            raise Exception(f"Failed to initialize Anthropic client: {str(e)}")
            
        try:
            self.reddit = praw.Reddit(
                client_id=reddit_creds['client_id'],
                client_secret=reddit_creds['client_secret'],
                user_agent=reddit_creds['user_agent']
            )
        except Exception as e:
            raise Exception(f"Failed to initialize Reddit client: {str(e)}")
        
        self.cache_dir = "reddit_cache"
        self.history_dir = "chat_history"
        for directory in [self.cache_dir, self.history_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def fetch_all_submissions(self, redditor: praw.models.Redditor) -> Generator[Dict, None, None]:
        """Fetch all submissions for a user using pagination."""
        try:
            for submission in redditor.submissions.new(limit=None):
                yield {
                    'type': 'submission',
                    'data': {
                        'title': submission.title,
                        'selftext': submission.selftext,
                        'subreddit': submission.subreddit.display_name,
                        'score': submission.score,
                        'upvote_ratio': submission.upvote_ratio,
                        'created_utc': submission.created_utc,
                        'permalink': submission.permalink,
                        'num_comments': submission.num_comments,
                        'url': submission.url,
                        'is_self': submission.is_self,
                        'link_flair_text': submission.link_flair_text,
                        'over_18': submission.over_18
                    }
                }
        except Exception as e:
            self.console.print(f"[red]Error fetching submissions: {e}[/red]")
            return

    def fetch_all_comments(self, redditor: praw.models.Redditor) -> Generator[Dict, None, None]:
        """Fetch all comments for a user using pagination."""
        try:
            for comment in redditor.comments.new(limit=None):
                yield {
                    'type': 'comment',
                    'data': {
                        'body': comment.body,
                        'subreddit': comment.subreddit.display_name,
                        'score': comment.score,
                        'created_utc': comment.created_utc,
                        'permalink': comment.permalink,
                        'is_submitter': comment.is_submitter,
                        'distinguished': comment.distinguished,
                        'parent_id': comment.parent_id,
                        'link_id': comment.link_id
                    }
                }
        except Exception as e:
            self.console.print(f"[red]Error fetching comments: {e}[/red]")
            return

    def fetch_user_data(self, username: str, force_refresh: bool = False) -> Optional[Dict]:
        """Fetch complete user data using PRAW with progress indication."""
        if not force_refresh:
            cached_data = self.load_cached_data(username)
            if cached_data:
                cache_age = datetime.now() - datetime.fromisoformat(cached_data['fetch_time'])
                if cache_age.days < 1:  # Cache for 24 hours
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
            
            # Verify the user exists by accessing a property
            _ = redditor.created_utc
            
            submissions_data = []
            comments_data = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                # Fetch submissions with progress indication
                task_submissions = progress.add_task("Fetching submissions...", total=None)
                for submission in self.fetch_all_submissions(redditor):
                    submissions_data.append(submission)
                    progress.update(task_submissions, advance=1)
                
                # Fetch comments with progress indication
                task_comments = progress.add_task("Fetching comments...", total=None)
                for comment in self.fetch_all_comments(redditor):
                    comments_data.append(comment)
                    progress.update(task_comments, advance=1)
            
            # Calculate some basic statistics
            subreddit_activity = {}
            for item in submissions_data + comments_data:
                subreddit = item['data']['subreddit']
                subreddit_activity[subreddit] = subreddit_activity.get(subreddit, 0) + 1
            
            # Sort subreddits by activity
            top_subreddits = dict(sorted(
                subreddit_activity.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10])
            
            data = {
                'submissions': submissions_data,
                'comments': comments_data,
                'username': username,
                'fetch_time': datetime.now().isoformat(),
                'statistics': {
                    'total_submissions': len(submissions_data),
                    'total_comments': len(comments_data),
                    'top_subreddits': top_subreddits
                }
            }
            
            self.save_to_cache(username, data)
            self.console.print(f"[green]Successfully fetched and cached data:[/green]")
            self.console.print(f"- Total submissions: {len(submissions_data)}")
            self.console.print(f"- Total comments: {len(comments_data)}")
            self.console.print("- Top active subreddits:")
            for sub, count in top_subreddits.items():
                self.console.print(f"  • r/{sub}: {count} posts/comments")
            
            return data
            
        except Exception as e:
            self.console.print(f"[red]Error fetching data: {e}[/red]")
            return None

    def get_cache_path(self, username: str) -> str:
        return os.path.join(self.cache_dir, f"{username}.json")

    def get_history_path(self, username: str) -> str:
        return os.path.join(self.history_dir, f"{username}_history.json")

    def load_chat_history(self, username: str) -> List[Dict]:
        history_path = self.get_history_path(username)
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                return json.load(f)
        return []

    def save_chat_history(self, username: str, history: List[Dict]):
        history_path = self.get_history_path(username)
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)

    def load_cached_data(self, username: str) -> Optional[Dict]:
        cache_path = self.get_cache_path(username)
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
        return None

    def save_to_cache(self, username: str, data: Dict):
        cache_path = self.get_cache_path(username)
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)

    def extract_post_data(self, data: Dict) -> str:
        """Format user data for analysis with improved organization."""
        content = f"User Activity Analysis for u/{data['username']}\n\n"
        
        # Add statistics section
        stats = data['statistics']
        content += "OVERVIEW:\n"
        content += f"Total Submissions: {stats['total_submissions']}\n"
        content += f"Total Comments: {stats['total_comments']}\n"
        content += "\nTop Active Subreddits:\n"
        for sub, count in stats['top_subreddits'].items():
            content += f"- r/{sub}: {count} posts/comments\n"
        content += "\n---\n\n"
        
        # Add submissions
        content += "RECENT SUBMISSIONS:\n\n"
        for submission in data['submissions'][:50]:  # Limit to recent 50 for analysis
            sub_data = submission['data']
            date = datetime.fromtimestamp(sub_data['created_utc']).strftime('%Y-%m-%d')
            content += f"Date: {date}\n"
            content += f"Title: {sub_data['title']}\n"
            content += f"Content: {sub_data['selftext']}\n"
            content += f"Subreddit: r/{sub_data['subreddit']}\n"
            content += f"Score: {sub_data['score']} (Upvote ratio: {sub_data['upvote_ratio']})\n"
            content += f"Comments: {sub_data['num_comments']}\n"
            content += "---\n\n"
        
        # Add comments
        content += "RECENT COMMENTS:\n\n"
        for comment in data['comments'][:50]:  # Limit to recent 50 for analysis
            comment_data = comment['data']
            date = datetime.fromtimestamp(comment_data['created_utc']).strftime('%Y-%m-%d')
            content += f"Date: {date}\n"
            content += f"Subreddit: r/{comment_data['subreddit']}\n"
            content += f"Content: {comment_data['body']}\n"
            content += f"Score: {comment_data['score']}\n"
            content += "---\n\n"
            
        return content

    def analyse_with_claude(self, username: str, question: str, chat_history: List[Dict]) -> str:
        """Interactive analysis of user data with Claude."""
        data = self.fetch_user_data(username)
        if not data:
            return "Unable to fetch user data."
        
        formatted_data = self.extract_post_data(data)
        
        # Include chat history context
        history_context = "\n".join([
            f"Previous Q: {entry['question']}\nPrevious A: {entry['answer']}\n"
            for entry in chat_history[-3:]  # Include last 3 exchanges for context
        ])

        # Get response from Claude
        message = self.client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1000,
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI analyzing Reddit activity to provide insights about users. 
                    Focus on identifying patterns in posting behavior, interests, and communication style. 
                    Consider both the content and context of posts, including subreddit choices and engagement levels.
                    Be objective and base your analysis only on the available data."""
                },
                {
                    "role": "user",
                    "content": f"""Based on this Reddit activity and our previous conversation, please answer 
                    the following question about u/{username}:

Previous conversation:
{history_context}

New Question: {question}

User Activity:
{formatted_data}

Please provide a focused and insightful answer based on the available data and our conversation history."""
                }
            ]
        )
        
        return message.content

def interactive_analysis(username: str):
    """Interactive analysis session for a Reddit user."""
    analyser = RedditPersonalityAnalyser()
    console = analyser.console
    
    chat_history = analyser.load_chat_history(username)
    
    console.print(Panel.fit(
        f"[bold blue]Interactive Analysis Session for u/{username}[/bold blue]\n"
        "Type 'exit' to end the session\n"
        "Type 'history' to view chat history\n"
        "Type 'refresh' to force refresh user data",
        title="Reddit Personality Analyser",
        border_style="blue"
    ))
    
    while True:
        question = console.input("\n[bold cyan]What would you like to know about this user?[/bold cyan] ")
        
        if question.lower() == 'exit':
            break
            
        if question.lower() == 'refresh':
            try:
                console.print("[yellow]Force refreshing user data...[/yellow]")
                data = analyser.fetch_user_data(username, force_refresh=True)
                if data:
                    console.print("[green]Data refreshed successfully![/green]")
                continue
            except Exception as e:
                console.print(f"[red]Error refreshing data: {e}[/red]")
                continue
        
        if question.lower() == 'history':
            console.print("\n[bold]Chat History:[/bold]")
            for entry in chat_history:
                console.print(Panel(
                    f"[cyan]Q: {entry['question']}[/cyan]\n\n[green]A: {entry['answer']}[/green]",
                    border_style="blue"
                ))
            continue
            
        try:
            console.print("[yellow]Analysing...[/yellow]")
            analysis = analyser.analyse_with_claude(username, question, chat_history)
            
            chat_history.append({
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "answer": analysis
            })
            analyser.save_chat_history(username, chat_history)
            
            console.print("\n[bold]Analysis:[/bold]")
            console.print(Panel(Markdown(analysis), border_style="green"))
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

def main():
    parser = argparse.ArgumentParser(description='Analyse Reddit user personality')
    parser.add_argument('username', help='Reddit username to analyse')
    parser.add_argument('--refresh', action='store_true', help='Force refresh user data')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of posts/comments to fetch')
    args = parser.parse_args()
    
    try:
        interactive_analysis(args.username)
    except KeyboardInterrupt:
        Console().print("\n[yellow]Ending analysis session.[/yellow]")
    except Exception as e:
        Console().print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()