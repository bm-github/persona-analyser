import requests
import json
import os
import sys
import argparse
from typing import Dict, List, Optional
from anthropic import Anthropic
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

class RedditPersonalityAnalyser:
    def __init__(self):
        # Initialize Rich console for better formatting
        self.console = Console()
        
        # Read API key from file
        try:
            with open('../../keys/key.txt', 'r') as f:
                api_key = f.read().strip()
        except FileNotFoundError:
            raise Exception("key.txt file not found. Please create it with your Claude API key.")
        
        self.headers = {
            'User-Agent': 'PersonalityAnalyser/1.0 (by /YourUsername)'
        }
        self.client = Anthropic(api_key=api_key)
        
        # Create necessary directories
        self.cache_dir = "reddit_cache"
        self.history_dir = "chat_history"
        for directory in [self.cache_dir, self.history_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def get_cache_path(self, username: str) -> str:
        """Get the path for the cached user data file."""
        return os.path.join(self.cache_dir, f"{username}.json")

    def get_history_path(self, username: str) -> str:
        """Get the path for the chat history file."""
        return os.path.join(self.history_dir, f"{username}_history.json")

    def load_chat_history(self, username: str) -> List[Dict]:
        """Load chat history from file if it exists."""
        history_path = self.get_history_path(username)
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                return json.load(f)
        return []

    def save_chat_history(self, username: str, history: List[Dict]):
        """Save chat history to file."""
        history_path = self.get_history_path(username)
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)

    def load_cached_data(self, username: str) -> Optional[Dict]:
        """Load user data from cache if it exists."""
        cache_path = self.get_cache_path(username)
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
        return None

    def save_to_cache(self, username: str, data: Dict):
        """Save user data to cache."""
        cache_path = self.get_cache_path(username)
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)

    def fetch_user_data(self, username: str, force_refresh: bool = False) -> Optional[Dict]:
        """Fetch user data from Reddit or cache."""
        if not force_refresh:
            cached_data = self.load_cached_data(username)
            if cached_data:
                self.console.print("[green]Using cached data[/green]")
                return cached_data

        self.console.print("[yellow]Fetching new data from Reddit...[/yellow]")
        url = f"https://www.reddit.com/user/{username}.json"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            self.save_to_cache(username, data)
            self.console.print("[green]Data fetched and cached successfully[/green]")
            return data
        except requests.RequestException as e:
            self.console.print(f"[red]Error fetching data: {e}[/red]")
            return None

    def extract_post_data(self, data: Dict) -> List[Dict]:
        """Extract relevant post data from Reddit JSON response."""
        posts = []
        if 'data' in data and 'children' in data['data']:
            for post in data['data']['children']:
                if 'data' in post:
                    posts.append({
                        'title': post['data'].get('title', ''),
                        'selftext': post['data'].get('selftext', ''),
                        'subreddit': post['data'].get('subreddit', ''),
                        'score': post['data'].get('score', 0),
                        'upvote_ratio': post['data'].get('upvote_ratio', 0),
                        'created_utc': post['data'].get('created_utc', 0),
                    })
        return posts

    def analyse_with_claude(self, username: str, question: str, chat_history: List[Dict]) -> str:
        """Interactive analysis of user data with Claude."""
        data = self.fetch_user_data(username)
        if not data:
            return "Unable to fetch user data."
        
        posts = self.extract_post_data(data)
        
        # Prepare the content for analysis
        content = "Here are the user's Reddit posts:\n\n"
        for post in posts:
            date = datetime.fromtimestamp(post['created_utc']).strftime('%Y-%m-%d')
            content += f"Date: {date}\n"
            content += f"Title: {post['title']}\n"
            content += f"Content: {post['selftext']}\n"
            content += f"Subreddit: {post['subreddit']}\n"
            content += f"Score: {post['score']}\n"
            content += "---\n\n"

        # Include chat history context
        history_context = "\n".join([
            f"Previous Q: {entry['question']}\nPrevious A: {entry['answer']}\n"
            for entry in chat_history[-3:]  # Include last 3 exchanges for context
        ])

        # Prompt for Claude with the specific question and chat history
        prompt = f"""Based on these Reddit posts and our previous conversation, please answer the following question about the user:

Previous conversation:
{history_context}

New Question: {question}

Posts to analyse:
{content}

Please provide a focused and insightful answer based on the available data and our conversation history."""

        # Get response from Claude
        message = self.client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1000,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        return message.content

def interactive_analysis(username: str):
    """Interactive analysis session for a Reddit user."""
    analyser = RedditPersonalityAnalyser()
    console = analyser.console
    
    # Load existing chat history
    chat_history = analyser.load_chat_history(username)
    
    console.print(Panel.fit(
        f"[bold blue]Interactive Analysis Session for u/{username}[/bold blue]\n"
        "Type 'exit' to end the session\n"
        "Type 'history' to view chat history",
        title="Reddit Personality Analyser",
        border_style="blue"
    ))
    
    while True:
        question = console.input("\n[bold cyan]What would you like to know about this user?[/bold cyan] ")
        
        if question.lower() == 'exit':
            break
        
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
            
            # Save to chat history
            chat_history.append({
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "answer": analysis
            })
            analyser.save_chat_history(username, chat_history)
            
            # Display the response
            console.print("\n[bold]Analysis:[/bold]")
            console.print(Panel(Markdown(analysis), border_style="green"))
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

def main():
    parser = argparse.ArgumentParser(description='Analyse Reddit user personality')
    parser.add_argument('username', help='Reddit username to analyse')
    args = parser.parse_args()
    
    try:
        interactive_analysis(args.username)
    except KeyboardInterrupt:
        Console().print("\n[yellow]Ending analysis session.[/yellow]")
    except Exception as e:
        Console().print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()