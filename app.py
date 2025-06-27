#! /usr/bin/env python3
"""
MoviesThisDay FastAPI Web Service

A modern web application and API for listing movies released on this day in history.

Features:
- FastAPI backend serving both HTML (Bootstrap-styled) and JSON endpoints
- Browse movies by date, search by title, IMDb ID, release date, year, genre, studio, and runtime
- Modern, responsive UI with advanced search and navigation
- Robust input validation and helpful error messages for all endpoints
- API endpoints for integration and data exploration

Author: 
- Jason A. Cox, 2025 June 15
- Project: https://github.com/jasonacox/MoviesToday
"""

# Standard library imports
import os
import sys
import re
import time
import base64
import pickle
import atexit
import logging
import zipfile
import platform
import resource
import urllib.request
from datetime import datetime

# Third-party imports
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

VERSION = "0.1.10"

# At startup, record the start time
START_TIME = time.time()

# Constants for filtering movies
POPULARITY_THRESHOLD = 10  # Only show movies with popularity above this value
AGE_LIMIT = 100  # Only show movies released within this many years

# Initialize FastAPI app
app = FastAPI()

# Set up Jinja2 templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Movie database paths
MOVIE_DB_DIR = os.path.join(os.path.dirname(__file__), 'movie_db')
PKL_PATH = os.path.join(MOVIE_DB_DIR, 'movies_by_day.pkl')
PKL_ZIP_URL = 'https://moviesthisday.s3.us-east-1.amazonaws.com/movies_by_day.pkl.zip'
PKL_ZIP_PATH = os.path.join(MOVIE_DB_DIR, 'movies_by_day.pkl.zip')

# Ensure movie_db directory exists
os.makedirs(MOVIE_DB_DIR, exist_ok=True)

# Set up logging
logger = logging.getLogger("MoviesThisDay")

# Notify that the app is starting
logger.info(f"Starting MoviesThisDay v{VERSION}...")

def on_shutdown():
    logger.info("MoviesThisDay is shutting down.")

atexit.register(on_shutdown)

# Simple in-memory cache for stats endpoints
_stats_cache = {}

# Download and unzip movies_by_day.pkl if missing
if not os.path.exists(PKL_PATH):
    logger.info('movies_by_day.pkl not found.')
    try:
        if not os.path.exists(PKL_ZIP_PATH):
            logger.info('Downloading zip...')
            urllib.request.urlretrieve(PKL_ZIP_URL, PKL_ZIP_PATH)
        logger.info('Extracting from zip...')
        with zipfile.ZipFile(PKL_ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(MOVIE_DB_DIR)
        logger.info('movies_by_day.pkl extracted successfully.')
    except Exception as e:
        logger.fatal(f"Could not retrieve or extract movies_by_day.pkl: {e}")
        sys.exit(1)

# Load the binary index and metadata once at startup
try:
    with open(PKL_PATH, 'rb') as pklfile:
        db = pickle.load(pklfile)
        movies_by_day_metadata = db.get('metadata', {})
        movies_by_day_index = db.get('index', {})
except Exception as e:
    logger.fatal(f"Could not load movies_by_day.pkl: {e}")
    sys.exit(1)

# Log header with version information and movie count at startup
movie_count = sum(len(movies) for movies in movies_by_day_index.values())
logger.info(f"""\n
=====================================================
  MoviesThisDay v{VERSION}
  Author: Jason A. Cox
  Project: https://github.com/jasonacox/MoviesToday
  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  Loaded {movie_count:,} movies into the database.
=====================================================
""")

def filter_movies(movies, current_year, today_date):
    """
    Filter a list of movies by popularity and age.
    - Only includes movies with popularity above POPULARITY_THRESHOLD.
    - Only includes movies released within AGE_LIMIT years of the current year.
    Args:
        movies (list): List of movie dicts.
        current_year (int): The year to use for age filtering.
        today_date (date): (Unused, kept for compatibility)
    Returns:
        list: Filtered list of movies.
    """
    return [
        m for m in movies
        if float(m.get('popularity', 0)) > POPULARITY_THRESHOLD
        and (m.get('release_year') and (current_year - int(m['release_year'])) <= AGE_LIMIT)
    ]

def is_new_release(movie, today=None):
    if not today:
        today = datetime.now().date()
    release_date = movie.get('release_date')
    if not release_date:
        return False
    try:
        release_dt = datetime.strptime(release_date, '%Y-%m-%d').date()
        days_diff = (today - release_dt).days
        return days_diff <= 92
    except Exception:
        return False

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, date: str = Query(None, description="Date in MM-DD format"), sort: str = Query('popularity', description="Sort by field"), client_date: str = Query(None, description="Client's local date in YYYY-MM-DD format", alias="client_date")):
    """
    Render the main MoviesThisDay page with movies for a given day, sorted and filtered.
    Uses client_date for all 'today' logic and as the default if no date is provided.
    Args:
        request (Request): FastAPI request object.
        date (str, optional): Date in MM-DD format. Defaults to None.
        sort (str, optional): Field to sort by ('popularity', 'name', 'year'). Defaults to 'popularity'.
        client_date (str, optional): Client's local date in YYYY-MM-DD format. Defaults to None.
    Returns:
        HTMLResponse: Rendered index.html template.
    """
    # Determine the date to use
    if client_date:
        try:
            client_dt = datetime.strptime(client_date, "%Y-%m-%d")
        except Exception:
            client_dt = datetime.now()
    else:
        client_dt = datetime.now()
    if date:
        mm_dd = date.replace('-', '_')
        try:
            dt = datetime.strptime(date, "%m-%d")
            today_str = dt.strftime('%B %d')
        except Exception:
            today_str = date
        display_date = f"{client_dt.year}-{date}"
    else:
        mm_dd = client_dt.strftime('%m_%d')
        today_str = client_dt.strftime('%B %d')
        display_date = client_dt.strftime('%Y-%m-%d')
    current_year = client_dt.year
    today_date = client_dt.date()
    movies = filter_movies(movies_by_day_index.get(mm_dd, []), current_year, today_date)
    # Annotate movies with is_new_release
    for m in movies:
        m['is_new_release'] = is_new_release(m, today_date)
    # Sorting logic
    if sort == 'name':
        movies.sort(key=lambda m: m.get('title', '').lower())
    elif sort == 'year':
        movies.sort(key=lambda m: int(m.get('release_year', 0)), reverse=True)
    else:  # Default to popularity
        movies.sort(key=lambda m: float(m.get('popularity', 0)), reverse=True)
    current_date_str = client_dt.strftime('%B %d')
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "movies": movies,
        "today_str": today_str,
        "max_date": datetime.now().strftime('%Y-%m-%d'),
        "sort_by": sort,
        "popularity_max": movies_by_day_metadata.get("avg_popularity_over_10", 100) or 100,
        "current_date_str": current_date_str,
        "version": VERSION,
        "client_date": client_dt.strftime('%Y-%m-%d'),
        "display_date": display_date,
        "current_date": client_dt.strftime('%Y-%m-%d'),
    })

@app.get("/movies/today")
async def movies_today():
    """
    Return today's movies as JSON, filtered by popularity, age, and release date.

    Returns:
        JSONResponse: A JSON object containing today's movies (filtered) and metadata.
    """
    today = datetime.now().strftime('%m_%d')
    current_year = datetime.now().year
    today_date = datetime.now().date()
    movies = filter_movies(movies_by_day_index.get(today, []), current_year, today_date)
    return JSONResponse(content={"movies": movies, "metadata": movies_by_day_metadata})

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """
    Render the modern search page for MoviesThisDay with search fields and results table.

    Args:
        request (Request): The incoming HTTP request object.

    Returns:
        TemplateResponse: Rendered search.html template with context variables.
    """
    return templates.TemplateResponse(request, "search.html", {
        "request": request,
        "popularity_max": movies_by_day_metadata.get("avg_popularity_over_10", 100) or 100,
        "version": VERSION
    })

@app.get("/movies/lookup")
async def movies_lookup(
    imdb_id: str = Query(None),
    title: str = Query(None, description="Regex pattern for title"),
    release_date: str = Query(None),
    movie_id: str = Query(None, alias="id"),
    release_year: str = Query(None),
    runtime: str = Query(None, description="e.g. >120, <90, =100, 90-120"),
    genre: str = Query(None, description="Regex pattern for OMDb genre"),
    studio: str = Query(None, description="Regex pattern for production company name"),
    rated: str = Query(None, description="e.g. G, PG, <PG-13, >=R, NR, etc.")
):
    """
    Search for movies matching one or more query parameters.
    Supports regex for title, genre, and studio. Validates input and returns matching movies.
    Args:
        imdb_id (str, optional): IMDb ID.
        title (str, optional): Regex pattern for title.
        release_date (str, optional): Release date in YYYY-MM-DD.
        movie_id (str, optional): Internal movie ID.
        release_year (str, optional): 4-digit year.
        runtime (str, optional): Runtime filter (e.g. >120, <90, =100, 90-120).
        genre (str, optional): Regex pattern for OMDb genre.
        studio (str, optional): Regex pattern for production company name.
        rated (str, optional): MPAA rating (e.g. G, PG, R, NC-17).
    Returns:
        JSONResponse: Matching movies and count.
    """
    if not any([imdb_id, title, release_date, movie_id, release_year, runtime, genre, studio, rated]):
        raise HTTPException(status_code=400, detail="Provide at least one query parameter: imdb_id, title, release_date, id, release_year, runtime, genre, studio, or rated.")
    # Validate regex fields
    if title is not None:
        if not title.strip():
            raise HTTPException(status_code=400, detail="Empty 'title' parameter. Provide a non-empty title regex pattern.")
        try:
            re.compile(title, re.IGNORECASE)
        except re.error as exc:
            raise HTTPException(status_code=400, detail="Invalid regex pattern for 'title'. Provide a valid regex string.") from exc
    if genre is not None:
        if not genre.strip():
            raise HTTPException(status_code=400, detail="Empty 'genre' parameter. Provide a non-empty genre regex pattern.")
        try:
            re.compile(genre, re.IGNORECASE)
        except re.error as exc:
            raise HTTPException(status_code=400, detail="Invalid regex pattern for 'genre'. Provide a valid regex string.") from exc
    if studio is not None:
        if not studio.strip():
            raise HTTPException(status_code=400, detail="Empty 'studio' parameter. Provide a non-empty studio regex pattern.")
        try:
            re.compile(studio, re.IGNORECASE)
        except re.error as exc:
            raise HTTPException(status_code=400, detail="Invalid regex pattern for 'studio'. Provide a valid regex string.") from exc
    if release_date is not None:
        try:
            datetime.strptime(release_date, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid 'release_date' format. Provide YYYY-MM-DD, e.g. 1999-03-31.") from exc
    if release_year is not None:
        if not release_year.isdigit() or len(release_year) != 4:
            raise HTTPException(status_code=400, detail="Invalid 'release_year'. Provide a 4-digit year, e.g. 1999.")
    if rated is not None:
        if not rated.strip():
            raise HTTPException(status_code=400, detail="Empty 'rated' parameter. Provide a non-empty rating.")
        # Simple validation for common rating patterns
        valid_ratings = ['G', 'PG', 'PG-13', 'R', 'NC-17', 'NR']
        if rated not in valid_ratings and not re.match(r"^[<>]=?[A-Z-]+$", rated):
            raise HTTPException(status_code=400, detail="Invalid 'rated' value. Use exact ratings like 'PG' or ranges like '<PG-13'.")
    # Load the movies index (assume already loaded as movies_by_day_index)
    all_movies = []
    for movies in movies_by_day_index.values():
        all_movies.extend(movies)
    results = all_movies
    if imdb_id:
        results = [m for m in results if m.get('imdb_id') == imdb_id]
    if movie_id:
        results = [m for m in results if str(m.get('id')) == str(movie_id)]
    if title:
        pattern = re.compile(title, re.IGNORECASE)
        results = [m for m in results if m.get('title') and pattern.search(m['title'])]
    if release_date:
        results = [m for m in results if m.get('release_date') == release_date]
    if release_year:
        results = [m for m in results if str(m.get('release_year')) == str(release_year)]
    if runtime:
        def runtime_match(val, expr):
            try:
                r = int(val) if val is not None else None
                if r is None:
                    return False
                expr = expr.strip()
                if '-' in expr:
                    parts = expr.split('-')
                    if len(parts) == 2:
                        low, high = int(parts[0]), int(parts[1])
                        return low <= r <= high
                elif expr.startswith('>'):
                    return r > int(expr[1:])
                elif expr.startswith('<'):
                    return r < int(expr[1:])
                elif expr.startswith('='):
                    return r == int(expr[1:])
                else:
                    return r == int(expr)
            except Exception:
                return False
        results = [m for m in results if runtime_match(m.get('runtime'), runtime)]
    if genre:
        pattern = re.compile(genre, re.IGNORECASE)
        results = [m for m in results if m.get('omdb_genre') and pattern.search(m['omdb_genre'])]
    if studio:
        pattern = re.compile(studio, re.IGNORECASE)
        results = [m for m in results if m.get('production_companies') and pattern.search(m['production_companies'])]
    if rated:
        rated_map = {
            'g': 1,
            'tv-y7': 2,
            'pg': 3, 'approved': 3,
            'pg-13': 4, 'pg13': 4, 'tv-14': 4,
            'r': 5,
            'nc-17': 6, 'nc17': 6,
            'nr': 7, 'not rated': 7, 'unrated': 7, '': 7, None: 7, 'n/a': 7,
        }
        def get_rated_val(val):
            if val is None:
                return 7
            v = str(val).strip().lower()
            return rated_map.get(v, 0)
        expr = rated.strip().lower()
        op = None
        val = expr
        # Parse operator
        if expr.startswith('<='):
            op = '<='
            val = expr[2:].strip()
        elif expr.startswith('>='):
            op = '>='
            val = expr[2:].strip()
        elif expr.startswith('<'):
            op = '<'
            val = expr[1:].strip()
        elif expr.startswith('>'):
            op = '>'
            val = expr[1:].strip()
        elif expr.startswith('='):
            op = '=='
            val = expr[1:].strip()
        else:
            op = '=='
            val = expr
        val_num = rated_map.get(val, None)
        if val_num is not None:
            if op == '<=':
                results = [m for m in results if get_rated_val(m.get('omdb_rated')) <= val_num]
            elif op == '>=':
                results = [m for m in results if get_rated_val(m.get('omdb_rated')) >= val_num]
            elif op == '<':
                results = [m for m in results if get_rated_val(m.get('omdb_rated')) < val_num]
            elif op == '>':
                results = [m for m in results if get_rated_val(m.get('omdb_rated')) > val_num]
            elif op == '==':
                results = [m for m in results if get_rated_val(m.get('omdb_rated')) == val_num]
        else:
            # If not a known rating, do nothing (or could return 0 results)
            results = []
    return JSONResponse(content={"results": results, "count": len(results)})

@app.get("/movies/by-imdb/{imdb_id}")
async def movie_by_imdb(imdb_id: str):
    """
    Get a single movie by its IMDb ID.
    Args:
        imdb_id (str): IMDb ID of the movie.
    Returns:
        JSONResponse: Movie dict if found, else error message.
    """
    for movies in movies_by_day_index.values():
        for m in movies:
            if m.get('imdb_id') == imdb_id:
                return JSONResponse(content=m)
    return JSONResponse(content={"error": "Movie not found"}, status_code=404)

@app.get("/movies/by-title")
async def movie_by_title(title: str = Query(..., description="Regex pattern for title")):
    """
    Get movies matching a title regex pattern.
    Args:
        title (str): Regex pattern for title.
    Returns:
        JSONResponse: Matching movies and count.
    """
    if not title or not title.strip():
        raise HTTPException(status_code=400, detail="Missing or empty 'title' parameter. Provide a non-empty title regex pattern, e.g. ?title=matrix")
    try:
        pattern = re.compile(title, re.IGNORECASE)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regex pattern for 'title'. Provide a valid regex string.")
    results = []
    for movies in movies_by_day_index.values():
        for m in movies:
            if m.get('title') and pattern.search(m['title']):
                results.append(m)
    return JSONResponse(content={"results": results, "count": len(results)})

@app.get("/movies/by-release-date/{release_date}")
async def movie_by_release_date(release_date: str):
    """
    Get movies by exact release date (YYYY-MM-DD).
    Args:
        release_date (str): Release date in YYYY-MM-DD format.
    Returns:
        JSONResponse: Matching movies and count.
    """
    try:
        datetime.strptime(release_date, "%Y-%m-%d")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid 'release_date' format. Provide YYYY-MM-DD, e.g. 1999-03-31.")
    results = []
    for movies in movies_by_day_index.values():
        for m in movies:
            if m.get('release_date') == release_date:
                results.append(m)
    return JSONResponse(content={"results": results, "count": len(results)})

@app.get("/movies/by-year/{release_year}")
async def movie_by_year(release_year: str):
    """
    Get movies by release year.
    Args:
        release_year (str): 4-digit year.
    Returns:
        JSONResponse: Matching movies and count.
    """
    if not release_year.isdigit() or len(release_year) != 4:
        raise HTTPException(status_code=400, detail="Invalid 'release_year'. Provide a 4-digit year, e.g. 1999.")
    results = []
    for movies in movies_by_day_index.values():
        for m in movies:
            if str(m.get('release_year')) == str(release_year):
                results.append(m)
    return JSONResponse(content={"results": results, "count": len(results)})

@app.get("/movies/by-genre")
async def movie_by_genre(genre: str = Query(..., description="Regex pattern for OMDb genre")):
    """
    Get movies matching a genre regex pattern (OMDb genre field).
    Args:
        genre (str): Regex pattern for OMDb genre.
    Returns:
        JSONResponse: Matching movies and count.
    """
    if not genre or not genre.strip():
        raise HTTPException(status_code=400, detail="Missing or empty 'genre' parameter. Provide a non-empty genre regex pattern, e.g. ?genre=action")
    try:
        pattern = re.compile(genre, re.IGNORECASE)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regex pattern for 'genre'. Provide a valid regex string.")
    results = []
    for movies in movies_by_day_index.values():
        for m in movies:
            if m.get('omdb_genre') and pattern.search(m['omdb_genre']):
                results.append(m)
    return JSONResponse(content={"results": results, "count": len(results)})

@app.get("/movies/by-studio")
async def movie_by_studio(studio: str = Query(..., description="Regex pattern for production company name")):
    """
    Get movies matching a studio regex pattern (production company name).
    Args:
        studio (str): Regex pattern for production company name.
    Returns:
        JSONResponse: Matching movies and count.
    """
    if not studio or not studio.strip():
        raise HTTPException(status_code=400, detail="Missing or empty 'studio' parameter. Provide a non-empty regex pattern, e.g. ?studio=Warner.")
    try:
        pattern = re.compile(studio, re.IGNORECASE)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regex pattern for 'studio'. Provide a valid regex string.")
    results = []
    for movies in movies_by_day_index.values():
        for m in movies:
            companies = m.get('production_companies')
            if companies and pattern.search(companies):
                results.append(m)
    return JSONResponse(content={"results": results, "count": len(results)})

@app.get("/movies/by-day/{mm_dd}")
async def movies_by_day(mm_dd: str):
    """
    Get a JSON list of movies released on the specified MM-DD (e.g., 06-15).
    Returns movies for that day across all years, filtered and sorted by popularity (desc).
    Args:
        mm_dd (str): Date in MM-DD or MM_DD format.
    Returns:
        JSONResponse: Movies and count for the specified day.
    """
    # Accept MM-DD or MM_DD
    if not mm_dd or not re.match(r"^(0[1-9]|1[0-2])[-_](0[1-9]|[12][0-9]|3[01])$", mm_dd):
        raise HTTPException(status_code=400, detail="Invalid 'mm_dd' format. Provide MM-DD or MM_DD, e.g. 06-15 or 06_15.")
    mm_dd_key = mm_dd.replace('-', '_')
    current_year = datetime.now().year
    today_date = datetime.now().date()
    movies = filter_movies(movies_by_day_index.get(mm_dd_key, []), current_year, today_date)
    movies.sort(key=lambda m: float(m.get('popularity', 0)), reverse=True)
    return JSONResponse(content={"results": movies, "count": len(movies)})

@app.get("/movies/by-day")
async def movies_by_day_missing():
    """
    Return an error if /movies/by-day/ is accessed without a date.
    Returns:
        JSONResponse: Error message and usage instructions.
    """
    return JSONResponse(
        status_code=400,
        content={
            "error": "Missing date. Please specify a date in MM-DD or MM_DD format, e.g. /movies/by-day/06-15 or /movies/by-day/06_15."
        }
    )

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """
    Render the About page for MoviesThisDay.
    Only version and current year are dynamic; all other content is static.
    Args:
        request (Request): FastAPI request object.
    Returns:
        HTMLResponse: Rendered about.html template.
    """
    movie_count = sum(len(movies) for movies in movies_by_day_index.values())
    return templates.TemplateResponse(request, "about.html", {
        "request": request,
        "current_year": datetime.now().year,
        "version": VERSION,
        "movie_count": movie_count
    })

@app.get("/version")
async def version():
    """
    Return the current MoviesThisDay app version as JSON.
    Returns:
        dict: Version string.
    """
    return {"version": VERSION}

@app.get("/details/{imdb_id}", response_class=HTMLResponse)
async def details_movie(request: Request, imdb_id: str):
    """
    Render a web page displaying all details for the specified IMDb ID.
    Args:
        request (Request): FastAPI request object.
        imdb_id (str): IMDb ID of the movie.
    Returns:
        HTMLResponse: Rendered movie details page or 404 if not found.
    """
    movie = None
    for movies in movies_by_day_index.values():
        for m in movies:
            if m.get('imdb_id') == imdb_id:
                movie = m
                break
        if movie:
            break
    if not movie:
        return HTMLResponse(content="<h2>Movie not found</h2>", status_code=404)
    return templates.TemplateResponse(request, "details.html", {
        "request": request,
        "movie": movie,
        "version": VERSION
    })

@app.get("/movie/{imdb_id}")
async def movie_json(imdb_id: str):
    """
    Return all available details for a movie by IMDb ID as a JSON payload.
    Args:
        imdb_id (str): IMDb ID of the movie.
    Returns:
        JSONResponse: All movie details if found, else 404 error.
    """
    for movies in movies_by_day_index.values():
        for m in movies:
            if m.get('imdb_id') == imdb_id:
                return JSONResponse(content=m)
    return JSONResponse(content={"error": "Movie not found"}, status_code=404)

@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """
    Serve a robots.txt file that allows all crawling except for /docs.
    """
    return PlainTextResponse("User-agent: *\nDisallow: /docs\n")

favicon_base64 = "data:image/png;base64,/9j/4QDKRXhpZgAATU0AKgAAAAgABgESAAMAAAABAAEAAAEaAAUAAAABAAAAVgEbAAUAAAABAAAAXgEoAAMAAAABAAIAAAITAAMAAAABAAEAAIdpAAQAAAABAAAAZgAAAAAAAABIAAAAAQAAAEgAAAABAAeQAAAHAAAABDAyMjGRAQAHAAAABAECAwCgAAAHAAAABDAxMDCgAQADAAAAAQABAACgAgAEAAAAAQAAABCgAwAEAAAAAQAAABCkBgADAAAAAQAAAAAAAAAAAAD/2wCEAAEBAQEBAQIBAQIDAgICAwQDAwMDBAUEBAQEBAUGBQUFBQUFBgYGBgYGBgYHBwcHBwcICAgICAkJCQkJCQkJCQkBAQEBAgICBAICBAkGBQYJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCf/dAAQAAf/AABEIABAAEAMBIgACEQEDEQH/xAGiAAABBQEBAQEBAQAAAAAAAAAAAQIDBAUGBwgJCgsQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+gEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoLEQACAQIEBAMEBwUEBAABAncAAQIDEQQFITEGEkFRB2FxEyIygQgUQpGhscEJIzNS8BVictEKFiQ04SXxFxgZGiYnKCkqNTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqCg4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2dri4+Tl5ufo6ery8/T19vf4+fr/2gAMAwEAAhEDEQA/AP6nfiL+1j8PfhZ+0N4V/Z68ZRS2tz4vtmlstQZ0Fss3mGOO3cHDBpWGEb7u4he9W/g5+1J4C+OPxU8a/DHwPDLKPBLwRT35ZDb3MkrSRuIQPmxG8TIWOASOOK4X47/sk6L+0D8RbzxD4vvEj0m68Ky6EkcaH7Vb3hu0uoL2Fz8gMBT5Rjk8Hit/4E/sz6J8A/iBq+teD3hi0O70LR9GtLRVPnIdM88yTSueHaYzbieuc5r90xFDgn/V/npyl9e9lHTXk5/aRvL/ABezbjyfAuVyvdpH5LTqcV/20oSjH6n7R66c/J7N2W+3PZ83xa8vLZcx/9k="

@app.get("/favicon.ico")
async def favicon():
    """
    Serve the favicon.ico as a base64-encoded PNG image (blue gradient theme).
    """
    # Remove data URL prefix if present
    b64 = favicon_base64.split(",", 1)[-1]
    icon_bytes = base64.b64decode(b64)
    return Response(content=icon_bytes, media_type="image/x-icon")

@app.get("/stats/movies_by_day")
def stats_movies_by_day():
    """
    Return a dictionary of movie counts by MM-DD (month-day), filtered by popularity and age.
    - Only includes movies with popularity above POPULARITY_THRESHOLD and within AGE_LIMIT years.
    - Skips movies with missing or invalid release dates.
    - Results are cached in-memory for performance.
    Returns:
        JSONResponse: {"date_counts": {"MM-DD": count, ...}}
    """
    if "movies_by_day" in _stats_cache:
        return JSONResponse(content=_stats_cache["movies_by_day"])
    from collections import Counter
    current_year = datetime.now().year
    today_date = datetime.now().date()
    mmdd_counts = Counter()
    for movies in movies_by_day_index.values():
        for m in movies:
            try:
                # Filter by popularity and age
                if float(m.get('popularity', 0)) <= POPULARITY_THRESHOLD:
                    continue
                if not m.get('release_year') or (current_year - int(m['release_year'])) > AGE_LIMIT:
                    continue
            except Exception:
                continue
            date = m.get('release_date')
            if not date or not date.strip():
                continue
            try:
                mmdd = date[5:10]  # 'YYYY-MM-DD' -> 'MM-DD'
                mmdd_counts[mmdd] += 1
            except Exception:
                continue
    # Sort by month and day
    sorted_counts = dict(sorted(mmdd_counts.items(), key=lambda x: (int(x[0][:2]), int(x[0][3:]))))
    result = {"date_counts": sorted_counts}
    _stats_cache["movies_by_day"] = result
    return JSONResponse(content=result)

@app.get("/stats/total_movies")
def stats_total_movies():
    """
    Return the total number of movies and the number of 'popular' movies (filtered by popularity and age).
    - 'Popular' movies have popularity above POPULARITY_THRESHOLD and are within AGE_LIMIT years.
    - Results are cached in-memory for performance.
    Returns:
        dict: {"total_movies": int, "popular_movies": int}
    """
    if "total_movies" in _stats_cache:
        return JSONResponse(content=_stats_cache["total_movies"])
    current_year = datetime.now().year
    today_date = datetime.now().date()
    total = 0
    popular_movies = 0
    for movies in movies_by_day_index.values():
        for m in movies:
            total += 1
            try:
                # Filter by popularity and age
                if float(m.get('popularity', 0)) <= POPULARITY_THRESHOLD:
                    continue
                if not m.get('release_year') or (current_year - int(m['release_year'])) > AGE_LIMIT:
                    continue
            except Exception:
                continue
            popular_movies += 1
    result = {"total_movies": total, "popular_movies": popular_movies}
    _stats_cache["total_movies"] = result
    return JSONResponse(content=result)

@app.get("/stats/movies_by_rating")
def stats_movies_by_rating():
    """
    Return a dictionary of movie counts by normalized rating, filtered by popularity and age.
    - Normalizes ratings (e.g., 'A'/'APPROVED' to 'PG', 'PASSED' to 'PG-13', etc.).
    - Only includes movies with popularity above POPULARITY_THRESHOLD and within AGE_LIMIT years.
    - Results are sorted from lowest to highest age rating, with extras appended alphabetically.
    - Results are cached in-memory for performance.
    Returns:
        dict: {"rating_counts": {rating: count, ...}}
    """
    if "movies_by_rating" in _stats_cache:
        return JSONResponse(content=_stats_cache["movies_by_rating"])
    from collections import Counter
    current_year = datetime.now().year
    rating_map = {
        'G': 'G', 'TV-G': 'G',
        'PG': 'PG', 'TV-PG': 'PG', 'M/PG': 'PG', 'GP': 'PG', 'M': 'PG',
        'PG-13': 'PG-13', 'TV-14': 'PG-13', 'TV-13': 'PG-13', '13+': 'PG-13', '12': 'PG-13', '16+': 'NC-17',
        'R': 'R', 'TV-MA': 'R', 'MA-17': 'R',
        'NC-17': 'NC-17', 'X': 'NC-17', '18+': 'NC-17',
        'A': 'PG', 'APPROVED': 'PG',
        'PASSED': 'PG-13',
        'NOT RATED': 'NR', 'NR': 'NR', 'UNRATED': 'NR', 'N/A': 'NR', '': 'NR', None: 'NR',
        'TV-Y': 'TV-Y',
        'TV-Y7': 'TV-Y7', 'TV-Y7-FV': 'TV-Y7',
    }
    rating_counts = Counter()
    for movies in movies_by_day_index.values():
        for m in movies:
            try:
                # Filter by popularity and age
                if float(m.get('popularity', 0)) <= POPULARITY_THRESHOLD:
                    continue
                if not m.get('release_year') or (current_year - int(m['release_year'])) > AGE_LIMIT:
                    continue
            except Exception:
                continue
            rated = m.get('omdb_rated') or m.get('rated') or ''
            rated = rated.strip().upper() if rated else 'NR'
            canonical = rating_map.get(rated, rated)
            rating_counts[canonical] += 1
    # Order: G, TV-Y, TV-Y7, PG, PG-13, R, NC-17, NR, then extras alphabetically
    canonical_order = [
        'G', 'TV-Y', 'TV-Y7', 'PG', 'PG-13', 'R', 'NC-17', 'NR'
    ]
    extra_ratings = sorted([r for r in rating_counts if r not in canonical_order])
    ordered_keys = canonical_order + extra_ratings
    sorted_counts = {k: rating_counts[k] for k in ordered_keys if k in rating_counts}
    result = {"rating_counts": sorted_counts}
    _stats_cache["movies_by_rating"] = result
    return JSONResponse(content=result)

@app.get("/stats/movies_by_year")
def stats_movies_by_year():
    """
    Return a dictionary of movie counts by release year (year: count), filtered by popularity and age.
    - Only includes movies with popularity above POPULARITY_THRESHOLD and within AGE_LIMIT years.
    - Results are cached in-memory for performance.
    Returns:
        JSONResponse: {"year_counts": {year: count, ...}}
    """
    if "movies_by_year" in _stats_cache:
        return JSONResponse(content=_stats_cache["movies_by_year"])
    from collections import Counter
    current_year = datetime.now().year
    year_counts = Counter()
    for movies in movies_by_day_index.values():
        for m in movies:
            try:
                if float(m.get('popularity', 0)) <= POPULARITY_THRESHOLD:
                    continue
                if not m.get('release_year') or (current_year - int(m['release_year'])) > AGE_LIMIT:
                    continue
                year = str(m.get('release_year'))
                if year:
                    year_counts[year] += 1
            except Exception:
                continue
    # Sort by year ascending
    sorted_counts = dict(sorted(year_counts.items(), key=lambda x: int(x[0])))
    result = {"year_counts": sorted_counts}
    _stats_cache["movies_by_year"] = result
    return JSONResponse(content=result)

@app.get("/health")
def health():
    """
    Health check endpoint that returns memory usage, selected global variables, app version, uptime, environment, cache, and movie count.
    Returns:
        dict: Health and status information for the MoviesThisDay app.
    """
    # Memory usage (RSS in bytes)
    mem_bytes = None
    try:
        # Use the already imported modules
        mem_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux, ru_maxrss is in KB; on macOS, it's in bytes
        if platform.system() != "Darwin":  # Linux returns KB, macOS returns bytes
            mem_bytes = mem_bytes * 1024  # convert KB to bytes
    except Exception:
        mem_bytes = None
    # Only show these selected globals
    show_keys = [
        'VERSION', 'POPULARITY_THRESHOLD', 'AGE_LIMIT', 'MOVIE_DB_DIR', 'PKL_PATH', 'PKL_ZIP_URL', 'PKL_ZIP_PATH'
    ]
    global_summary = {}
    for k in show_keys:
        v = globals().get(k, None)
        # Show only filename for paths
        if "PATH" in k or "DIR" in k:
            v = os.path.basename(v) if v else None
        # Convert to string for JSON serialization
        global_summary[k] = v

    def pretty_mem(mem_bytes):
        if not mem_bytes or mem_bytes <= 0:
            return None
        units = ["bytes", "KB", "MB", "GB"]
        unit_index = 0
        while mem_bytes >= 1024 and unit_index < len(units) - 1:
            mem_bytes /= 1024
            unit_index += 1
        return f"{mem_bytes:.2f} {units[unit_index]}"

    uptime_seconds = int(time.time() - START_TIME)
    cache_keys = list(_stats_cache.keys())

    return {
        "status": "ok",
        "memory_used": mem_bytes,
        "memory_used_string": pretty_mem(mem_bytes),
        "globals": global_summary,
        "version": VERSION,
        "uptime_seconds": uptime_seconds,
        "cache_keys": cache_keys,
        "database": movies_by_day_metadata, 
    }

@app.get("/ping")
def ping():
    """
    Simple ping endpoint for uptime checks. Returns 'ok'.
    """
    return {"status": "ok"}

