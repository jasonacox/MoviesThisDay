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

import os
import pickle
import re
import urllib.request
import zipfile
from datetime import datetime
import time

from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
import json

VERSION = "0.1.4"

POPULARITY_THRESHOLD = 10  # Only show movies with popularity above this value
AGE_LIMIT = 100  # Only show movies released within this many years

app = FastAPI()

# Log header with version information at startup
print(f"""
=====================================================
  MoviesThisDay v{VERSION}
  Author: Jason A. Cox
  Project: https://github.com/jasonacox/MoviesToday
  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
=====================================================
""")

# Set up Jinja2 templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Movie database paths
MOVIE_DB_DIR = os.path.join(os.path.dirname(__file__), 'movie_db')
PKL_PATH = os.path.join(MOVIE_DB_DIR, 'movies_by_day.pkl')
PKL_ZIP_URL = 'https://github.com/user-attachments/files/20749297/movies_by_day.pkl.zip'
PKL_ZIP_PATH = os.path.join(MOVIE_DB_DIR, 'movies_by_day.pkl.zip')

# Ensure movie_db directory exists
os.makedirs(MOVIE_DB_DIR, exist_ok=True)

# Download and unzip movies_by_day.pkl if missing
if not os.path.exists(PKL_PATH):
    print('movies_by_day.pkl not found. Downloading...')
    urllib.request.urlretrieve(PKL_ZIP_URL, PKL_ZIP_PATH)
    with zipfile.ZipFile(PKL_ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(MOVIE_DB_DIR)
    os.remove(PKL_ZIP_PATH)
    print('movies_by_day.pkl downloaded and extracted.')

# Load the binary index and metadata once at startup
with open(PKL_PATH, 'rb') as pklfile:
    db = pickle.load(pklfile)
    movies_by_day_metadata = db.get('metadata', {})
    movies_by_day_index = db.get('index', {})

# Load environment variables
CORRECTIONS_FILE = os.environ.get('CORRECTIONS_FILE', os.path.join(os.path.dirname(__file__), 'corrections.jsonl'))

# Check if corrections file is writable at startup
try:
    with open(CORRECTIONS_FILE, 'a', encoding='utf-8') as f:
        pass
    CORRECTIONS_WRITABLE = True
except Exception as e:
    print(f"[ERROR] Corrections file '{CORRECTIONS_FILE}' is not writable: {e}")
    CORRECTIONS_WRITABLE = False

def filter_movies(movies, current_year, today_date):
    """
    Filter a list of movies by popularity, age, and release date.
    - Only includes movies with popularity above POPULARITY_THRESHOLD.
    - Only includes movies released within AGE_LIMIT years of the current year.
    - Excludes movies with a release date in the future.
    Args:
        movies (list): List of movie dicts.
        current_year (int): The year to use for age filtering.
        today_date (date): The current date for future filtering.
    Returns:
        list: Filtered list of movies.
    """
    return [
        m for m in movies
        if float(m.get('popularity', 0)) > POPULARITY_THRESHOLD
        and (m.get('release_year') and (current_year - int(m['release_year'])) <= AGE_LIMIT)
        and (not m.get('release_date') or datetime.strptime(m['release_date'], '%Y-%m-%d').date() <= today_date)
    ]

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
        "display_date": display_date
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
    studio: str = Query(None, description="Regex pattern for production company name")
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
    Returns:
        JSONResponse: Matching movies and count.
    """
    if not any([imdb_id, title, release_date, movie_id, release_year, runtime, genre, studio]):
        raise HTTPException(status_code=400, detail="Provide at least one query parameter: imdb_id, title, release_date, id, release_year, runtime, genre, or studio.")
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
    return templates.TemplateResponse(request, "about.html", {
        "request": request,
        "current_year": datetime.now().year,
        "version": VERSION
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
    return templates.TemplateResponse("details.html", {
        "request": request,
        "movie": movie,
        "version": VERSION
    })

@app.post("/corrections", response_class=PlainTextResponse)
async def submit_correction(imdb_id: str = Form(...), correction: str = Form(...), user_agent: str = Form(None), movie_title: str = Form(None)):
    """
    Accept a correction for a movie and append it to corrections.jsonl (or configured file).
    Returns Oops if file is not writable.
    """
    if not CORRECTIONS_WRITABLE:
        time.sleep(1.0)
        return PlainTextResponse("Oops! Something went wrong.", status_code=500)
    # Limit correction payload size to prevent abuse
    MAX_CORRECTION_LEN = 1000
    MAX_TITLE_LEN = 300
    MAX_IMDB_ID_LEN = 20
    if (
        len(correction) > MAX_CORRECTION_LEN or
        (movie_title and len(movie_title) > MAX_TITLE_LEN) or
        (imdb_id and len(imdb_id) > MAX_IMDB_ID_LEN)
    ):
        time.sleep(1.0)
        return PlainTextResponse("Oops! Something went wrong.", status_code=413)
    entry = {
        "imdb_id": imdb_id,
        "movie_title": movie_title or "",
        "correction": correction,
        "timestamp": datetime.now().isoformat(),
        "user_agent": user_agent or ""
    }
    try:
        with open(CORRECTIONS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[ERROR] Could not write to corrections file: {e}")
        time.sleep(1.0)
        return PlainTextResponse("Oops! Something went wrong.", status_code=500)
    time.sleep(1.0)  # Add a 1 second delay to mitigate rapid repeated requests
    return "Correction received. Thank you!"
