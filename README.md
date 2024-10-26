# Reddit Personality Analyser

A Python-based tool that analyses Reddit users' activity patterns and provides AI-powered insights using either Anthropic's Claude or Groq's LLaMA models.

## Overview

This tool fetches a Reddit user's submission and comment history, analyses their activity patterns, and uses AI to provide insights about their interests, behaviour, and communication style. It supports interactive analysis sessions where you can ask questions about the user and receive AI-generated insights based on their Reddit activity.

## Features

- Fetches and caches Reddit user activity data
- Supports both Claude and Groq AI models for analysis
- Interactive command-line interface with rich text formatting
- Maintains chat history for context-aware analysis
- Data caching to reduce API calls
- Comprehensive activity statistics
- Configurable data refresh options

## Prerequisites

- Python 3.7+
- Reddit API credentials
- Either an Anthropic API key (for Claude) or a Groq API key (for LLaMA)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/reddit-personality-analyser.git
cd reddit-personality-analyser
```

2. Install required packages:

```bash
pip install praw anthropic groq rich
```

3. Set up your credentials:
   - Create a `keys` directory in the project root
   - Add your API keys:
     - `keys/key.txt` for Anthropic API key
     - `keys/key-groq.txt` for Groq API key
   - Add Reddit credentials in `keys/reddit-credentials.json`:

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "user_agent": "your_user_agent"
}
```

## Usage

### Basic Usage

Run the analyser with either Claude or Groq:

```bash
# Using Claude
python persona-claude.py username

# Using Groq
python persona-groq.py username
```

### Command-line Options

- `--refresh`: Force refresh user data instead of using cache
- `--limit`: Limit the number of posts/comments to fetch (optional)

### Interactive Commands

During an analysis session:

- Type `exit` to end the session
- Type `history` to view chat history
- Type `refresh` to force refresh user data

## Features in Detail

### Data Collection

- Fetches user submissions and comments
- Calculates activity statistics
- Identifies top active subreddits
- Caches data for 24 hours by default

### AI Analysis

- Context-aware responses using chat history
- In-depth analysis of posting patterns
- Insights into user interests and behaviour
- Communication style assessment

### Data Caching

- Automatic caching of fetched data
- 24-hour cache validity
- Force refresh option available
- Separate cache for chat history

## Project Structure

```
reddit-personality-analyser/
├── persona-claude.py    # Claude-based analyser
├── persona-groq.py      # Groq-based analyser
├── keys/                # API credentials (not included)
├── reddit_cache/        # Cached user data
└── chat_history/        # Stored chat histories
```

## Error Handling

The tool includes comprehensive error handling for:

- Missing or invalid credentials
- API rate limits
- Network issues
- Invalid usernames
- Data parsing errors

## Privacy Considerations

This tool only analyses publicly available Reddit data. It:

- Respects Reddit's API terms of service
- Only accesses public posts and comments
- Stores data locally in cache
- Does not collect or transmit personal information

## Disclaimer

This tool is for educational and research purposes only. Please use responsibly and in accordance with Reddit's terms of service.
