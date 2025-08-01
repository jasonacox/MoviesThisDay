[![CI](https://github.com/jasonacox/MoviesThisDay/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/jasonacox/MoviesThisDay/actions/workflows/python-app.yml)

# MoviesThisDay

A modern FastAPI web application and API for exploring movies released on this day in history.

Website: [moviesthisday.com](https://moviesthisday.com)

<img width="256" alt="image" src="https://github.com/user-attachments/assets/a656236c-f975-4b4b-a351-030e367b29de" />

## Features
- FastAPI backend serving both HTML (Bootstrap-styled) and JSON endpoints
- Browse movies by date, search by title, IMDb ID, release date, year, genre, studio, and runtime
- Modern, responsive UI with advanced search and navigation
- Robust input validation and helpful error messages for all endpoints
- API endpoints for integration and data exploration
- Pagination for large search result sets
- Clear and Search buttons in the search form
- Consistent, modern navigation and theming across all pages
- About page with project and API info, and a link to the GitHub repo

## Web UI
- `/` — Main page: Browse movies released on today's date or any selected date
- `/search` — Advanced search page with sidebar form, paginated results, and modern UI
- `/about` — About page with project info, usage, API examples, and GitHub link
- `/details/{imdb_id}` — Movie details page: View all available information for a specific movie by IMDb ID, including poster, ratings, and a correction form

<img width="1199" alt="image" src="https://github.com/user-attachments/assets/5d2a8d0a-95e0-4939-8b3d-c80195dad3a0" />

## API Endpoints
- `/ping` — Simple health check (returns `{ "status": "ok" }`)
- `/health` — Detailed health and status info (memory, uptime, version, database metadata, etc.)
- `/movies/today` — Movies released today (JSON)
- `/movies/lookup` — Flexible search by any combination of: `imdb_id`, `title` (regex), `release_date`, `id`, `release_year`, `runtime`, `genre` (regex), `studio` (regex), `rated`
- `/movies/by-imdb/{imdb_id}` — Lookup by IMDb ID
- `/movies/by-title?title=...` — Search by title (regex)
- `/movies/by-release-date/{release_date}` — Search by release date (YYYY-MM-DD)
- `/movies/by-year/{release_year}` — Search by year
- `/movies/by-genre?genre=...` — Search by genre (regex)
- `/movies/by-studio?studio=...` — Search by studio (regex)
- `/movies/by-day/{mm_dd}` — Movies released on a specific MM-DD (all years)
- `/movie/{imdb_id}` — Get all available details for a movie by IMDb ID (JSON, 404 if not found)
- `/stats/movies_by_day` — Movie counts by MM-DD (JSON, for stats/graphs)
- `/stats/total_movies` — Total and popular movie counts (JSON)
- `/stats/movies_by_rating` — Movie counts by normalized rating (JSON)
- `/stats/movies_by_year` — Movie counts by release year (JSON)

### Example API Usage

```sh
# Movies released today (JSON)
curl -X GET 'http://localhost:8000/movies/today'

# Movies by day (MM-DD)
curl -X GET 'http://localhost:8000/movies/by-day/06-15'

# Search by title (regex)
curl -G --data-urlencode 'title=^tron' 'http://localhost:8000/movies/by-title'

# Search by studio (regex)
curl -G --data-urlencode 'studio=Warner' 'http://localhost:8000/movies/by-studio'

# Advanced lookup (multiple fields)
curl -G --data-urlencode 'title=star' --data-urlencode 'release_year=1977' 'http://localhost:8000/movies/lookup'

# Search by genre (regex)
curl -G --data-urlencode 'genre=Action' 'http://localhost:8000/movies/by-genre'
```

### Interactive API Documentation

- Explore and test all API endpoints with **Swagger UI** at: [http://localhost:8000/docs](http://localhost:8000/docs) (or [https://moviesthisday.com/docs](https://moviesthisday.com/docs) in production)

## Data File Auto-Download

On first run, if the required `movie_db/movies_by_day.pkl` data file is missing, the app will automatically download and unzip it from a public source. No manual download is required for a fresh install.

You can also manually download the latest zipped data file here:

- [movies_by_day.pkl.zip (latest)](https://moviesthisday.s3.us-east-1.amazonaws.com/movies_by_day.pkl.zip)

Place the downloaded zip file in the `movie_db/` directory and the app will extract it on startup if needed.

## Project Structure
- `app.py` — Main FastAPI app and all endpoints
- `templates/` — HTML templates (Bootstrap, modern UI)
- `movie_db/` — Data and scripts for building the movie index

## Running with Docker

You can run MoviesThisDay using the official Docker container for easy deployment:

```sh
# Start the container (see run.sh for details)
./run.sh
```

This will:
- Pull and run the latest MoviesThisDay image
- Expose the app on port 8000 (or your chosen port)
- Set the timezone via the `TZ` environment variable (default: America/Los_Angeles)
- Automatically restart the container unless stopped
- Provide a healthcheck for the container

You can also run the container manually:

```sh
docker run -d \
  --name moviesthisday \
  -p 8000:8000 \
  --restart unless-stopped \
  -e TZ=America/Los_Angeles \
  jasonacox/moviesthisday:latest
```

See `run.sh` for a robust startup script with healthcheck, log tailing, and persistent data volume.

## MCP Integration: Use MoviesThisDay with Claude Desktop and AI Assistants

MoviesThisDay includes an optional [MCP (Model Context Protocol) server](./mcp/) for integration with AI chatbots and tools such as Claude Desktop.

- The MCP server allows AI assistants to fetch a summary of popular movies released on a given day in history, using the public MoviesThisDay API.
- Works with Claude Desktop, fastmcp, and any MCP-compatible client.
- See [`mcp/README.md`](./mcp/README.md) for setup and usage details.

**Example Claude Desktop Use Case:**

<img width="640" alt="image" src="https://github.com/user-attachments/assets/8b94a28a-33ec-4700-b4a1-546aab6489fa" />

With the MCP server running, you can ask Claude questions like:
- "What movies were released today in history?"
- "List movies released on July 4th."
- "What movies came out on 1999-03-31?"

Claude will call the MoviesThisDay tool and display a summary of movies released on the requested date.

---

## Author & License
- Author: Jason A. Cox
- Project: [MoviesThisDay on GitHub](https://github.com/jasonacox/MoviesThisDay)
- License: MIT
- Vibe Coded (Read the [Story](https://www.jasonacox.com/wordpress/archives/2330))
