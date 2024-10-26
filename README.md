# Reddit Personality Analyser

This repository contains two Python scripts, `persona.py` and `persona-groq.py`, which analyse a Reddit user's personality by extracting their post history and interacting with two different AI models, Claude and GROQ, respectively. These scripts help provide insights into a user's online behavior and personality traits based on their Reddit activity.

## Files

### 1. `persona.py`

This script uses the **Claude API** for analysis. It fetches a Reddit user's posts, processes them, and allows interactive querying of the user's personality traits. Key features include:

- **Fetching Reddit User Data**: Retrieves the post history of a specified Reddit user.
- **Caching**: Stores the fetched data and previous analyses in JSON format for future use.
- **Interactive Analysis**: Users can ask personality-related questions about the Reddit user, and responses are generated using the Claude API.
- **Rich Integration**: Utilizes the `rich` library for enhanced terminal output.

#### Usage:
```bash
python persona.py <reddit_username>
```

#### Install Dependencies:
- `requests`
- `json`
- `os`
- `argparse`
- `anthropic`
- `rich`

**Install dependencies**:
```bash
pip install requests json os argparse anthropic rich
```

Make sure to add your **Claude API key** in `../../keys/key.txt`.

### 2. `persona-groq.py`

This script is similar to `persona.py` but leverages the **GROQ API** for analysis instead of Claude. It provides the same functionalities such as fetching Reddit data, caching, and interactive analysis.

- **GROQ Integration**: Replaces Claude with GROQ to generate responses based on Reddit post history.
- **API Key Handling**: Requires an API key from GROQ, stored in `../../keys/key-groq.txt`.

#### Usage:
```bash
python persona-groq.py <reddit_username>
```

## Install Dependencies

To install the required dependencies, copy the following into your terminal:

Make sure to add your **GROQ API key** in `../../keys/key-groq.txt`.

## How to Run

1. **Install dependencies**:
   ```bash
   pip install requests rich anthropic groq
   ```

2. **Add API keys**:
   - For `persona.py`, place the Claude API key in `../../keys/key.txt`.
   - For `persona-groq.py`, place the GROQ API key in `../../keys/key-groq.txt`.

3. **Run the script**:
   ```bash
   python persona.py <reddit_username>
   ```

   or

   ```bash
   python persona-groq.py <reddit_username>
   ```

4. **Interactive Mode**: Follow the prompts in the terminal to ask questions and analyse Reddit data interactively.