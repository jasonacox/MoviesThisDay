"""
MoviesThisDay MCP Tool Server

This script implements an MCP (Model Context Protocol) tool server that provides
a summary of popular movies released on a given day in history (or today) using 
the MoviesThisDay.com public API. It is designed for integration with AI 
assistants and chatbots (e.g., Claude Desktop) that support MCP tools.

Features:
- Exposes a single MCP tool: get_movies_by_date(date: str = None)
- Returns a concise text summary of movies released on the specified date 
    (YYYY-MM-DD or MM-DD), or today if not specified.
- Uses the MoviesThisDay.com API for up-to-date movie data.

Requirements:
- pip install httpx fastmcp mcp

Example usage:
        python3 main.py

"""
import httpx
from mcp.server.fastmcp import FastMCP

# initialize server
mcp = FastMCP("movies_this_day")

API_BASE = "https://moviesthisday.com"

def _format_mm_dd(date: str) -> str:
    """Helper to convert date string to MM_DD format for API."""
    if len(date) == 10:
        return date[5:].replace('-', '_')
    return date.replace('-', '_')

async def fetch_movies(date: str = None):
    """
    Fetch movies released on the given date (YYYY-MM-DD or MM-DD) or today if not specified.
    Args:
        date (str, optional): Date in YYYY-MM-DD or MM-DD format. Defaults to None (today).
    Returns:
        list: List of movie dicts from the API.
    """
    if date:
        url = f"{API_BASE}/movies/by-day/{_format_mm_dd(date)}"
    else:
        url = f"{API_BASE}/movies/today"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=20.0)
            data = response.json()
            movies = data.get("results") or data.get("movies") or []
            return movies
        except httpx.TimeoutException:
            return []
        except Exception:
            return []

@mcp.tool()
async def get_movies_by_date(date: str = None):
    """
    Fetch a summary of popular movies released on the specified date (YYYY-MM-DD or MM-DD), or today if not specified.
    Args:
        date (str, optional): Date in YYYY-MM-DD or MM-DD format. Defaults to None (today).
    Returns:
        str: Text summary of movies released on that day.
    """
    movies = await fetch_movies(date)
    if movies:
        # Sort by popularity descending if available
        movies.sort(key=lambda m: float(m.get('popularity', 0)), reverse=True)
        titles = [f"{m.get('title')} ({m.get('release_year') or m.get('release_date', '')[:4]})" for m in movies if m.get('title')]
        text = "Some popular movies released on this day in history:\n\n " + "\n * ".join(titles[:10]) + "."
    else:
        text = "No movies found for this day."
    return text

if __name__ == "__main__":
    mcp.run(transport="stdio")