# MoviesThisDay MCP Integration

This directory provides an MCP (Model Context Protocol) tool server ([main.py](./main.py)) for integrating MoviesThisDay.com with AI assistants and chatbots such as Claude Desktop. The tool allows clients to fetch a list of popular movies released on a given day in history (today or a specified date) using the public MoviesThisDay.com API.

## Features
- Returns a concise text summary of popular movies released on a specified date (or today if not specified).
- Designed for use with Claude Desktop, other MCP-compatible chatbots, or any client supporting the MCP tools protocol.
- Uses the public API at https://moviesthisday.com for up-to-date movie data.

## How It Works
- The MCP tool exposes a single function: `get_movies_by_date(date: str = None)`
- If no date is provided, it fetches movies for today. If a date is provided (YYYY-MM-DD or MM-DD), it fetches movies for that day in history.
- The response is a text summary, e.g.:  
  `Some popular movies released on this day in history: Toy Story (1995), Tron (1982).`

## Requirements
- Python 3.8+
- `httpx` library (install with `pip install httpx`)
- MCP tool server framework (e.g. [fastmcp](https://github.com/anthropics/fastmcp) or compatible)

## Setup

1. Install dependencies:
```sh
pip install httpx fastmcp mcp
```
2. For Claude Desktop, edit the file. Be sure to adjust the paths to python and the main.py file:
```json
{
    "mcpServers": {
        "movies-this-day-local": {
            "command": "/usr/bin/python3",
            "args": [
                "/your/path/MoviesThisDay/mcp/main.py"
            ]
        }
    }
}
```
3. Restart Claude Desktop

**Test - Ask Claude:**
   - "What movies were released today in history?"
   - "What movies came out on July 4th?"
   - "List movies released on 1999-03-31."

Claude will call the tool and display a summary of movies released on the requested date.

## API Reference
- [MoviesThisDay.com API](https://moviesthisday.com)
  - `/movies/today` — Movies released today
  - `/movies/by-day/{MM_DD}` — Movies released on a specific day (e.g. `/movies/by-day/06_19`)

## Customization
- You can modify `main.py` to change the output format, add more endpoints, or support additional features as needed.

## License
See the main project LICENSE file.
