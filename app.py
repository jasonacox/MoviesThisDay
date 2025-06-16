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
- Author: Jason A. Cox
- Project: https://github.com/jasonacox/MoviesToday
"""

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pickle
from datetime import datetime
import os
import re
import urllib.request
import zipfile

VERSION = "0.1.0"

POPULARITY_THRESHOLD = 10  # Only show movies with popularity above this value
AGE_LIMIT = 100  # Only show movies released within this many years

app = FastAPI()

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

def filter_movies(movies, current_year, today_date):
    """Filter movies by popularity, age, and release date not in the future."""
    return [
        m for m in movies
        if float(m.get('popularity', 0)) > POPULARITY_THRESHOLD
        and (m.get('release_year') and (current_year - int(m['release_year'])) <= AGE_LIMIT)
        and (not m.get('release_date') or datetime.strptime(m['release_date'], '%Y-%m-%d').date() <= today_date)
    ]

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, date: str = Query(None, description="Date in MM-DD format"), sort: str = Query('popularity', description="Sort by field")):
    """Render the main page with movies for a given day, sorted and filtered."""
    if date:
        # Accept MM-DD or MM_DD
        mm_dd = date.replace('-', '_')
        try:
            dt = datetime.strptime(date, "%m-%d")
            today_str = dt.strftime('%B %d')
        except Exception:
            today_str = date
    else:
        mm_dd = datetime.now().strftime('%m_%d')
        today_str = datetime.now().strftime('%B %d')
    current_year = datetime.now().year
    today_date = datetime.now().date()
    movies = filter_movies(movies_by_day_index.get(mm_dd, []), current_year, today_date)
    # Sorting logic
    if sort == 'name':
        movies.sort(key=lambda m: m.get('title', '').lower())
    elif sort == 'year':
        movies.sort(key=lambda m: int(m.get('release_year', 0)), reverse=True)
    else:  # Default to popularity
        movies.sort(key=lambda m: float(m.get('popularity', 0)), reverse=True)
    current_date_str = datetime.now().strftime('%B %d')
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "movies": movies,
        "today_str": today_str,
        "max_date": datetime.now().strftime('%Y-%m-%d'),
        "sort_by": sort,
        "popularity_max": movies_by_day_metadata.get("avg_popularity_over_10", 100) or 100,
        "current_date_str": current_date_str,
        "version": VERSION
    })

@app.get("/movies/today")
async def movies_today():
    """Return today's movies as JSON, filtered by popularity, age, and release date."""
    today = datetime.now().strftime('%m_%d')
    current_year = datetime.now().year
    today_date = datetime.now().date()
    movies = filter_movies(movies_by_day_index.get(today, []), current_year, today_date)
    return JSONResponse(content={"movies": movies, "metadata": movies_by_day_metadata})

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """
    Render the modern search page for MoviesThisDay with search fields and results table.
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
    id: str = Query(None),
    release_year: str = Query(None),
    runtime: str = Query(None, description="e.g. >120, <90, =100, 90-120"),
    genre: str = Query(None, description="Regex pattern for OMDb genre"),
    studio: str = Query(None, description="Regex pattern for production company name")
):
    # Validate at least one parameter is provided
    if not any([imdb_id, title, release_date, id, release_year, runtime, genre, studio]):
        raise HTTPException(status_code=400, detail="Provide at least one query parameter: imdb_id, title, release_date, id, release_year, runtime, genre, or studio.")
    # Validate regex fields
    if title is not None:
        if not title.strip():
            raise HTTPException(status_code=400, detail="Empty 'title' parameter. Provide a non-empty title regex pattern.")
        try:
            re.compile(title, re.IGNORECASE)
        except re.error:
            raise HTTPException(status_code=400, detail="Invalid regex pattern for 'title'. Provide a valid regex string.")
    if genre is not None:
        if not genre.strip():
            raise HTTPException(status_code=400, detail="Empty 'genre' parameter. Provide a non-empty genre regex pattern.")
        try:
            re.compile(genre, re.IGNORECASE)
        except re.error:
            raise HTTPException(status_code=400, detail="Invalid regex pattern for 'genre'. Provide a valid regex string.")
    if studio is not None:
        if not studio.strip():
            raise HTTPException(status_code=400, detail="Empty 'studio' parameter. Provide a non-empty studio regex pattern.")
        try:
            re.compile(studio, re.IGNORECASE)
        except re.error:
            raise HTTPException(status_code=400, detail="Invalid regex pattern for 'studio'. Provide a valid regex string.")
    if release_date is not None:
        try:
            datetime.strptime(release_date, "%Y-%m-%d")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'release_date' format. Provide YYYY-MM-DD, e.g. 1999-03-31.")
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
    if id:
        results = [m for m in results if str(m.get('id')) == str(id)]
    if title:
        try:
            pattern = re.compile(title, re.IGNORECASE)
            results = [m for m in results if m.get('title') and pattern.search(m['title'])]
        except re.error:
            return JSONResponse(content={"error": "Invalid regex pattern for title."}, status_code=400)
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
        try:
            pattern = re.compile(genre, re.IGNORECASE)
            results = [m for m in results if m.get('omdb_genre') and pattern.search(m['omdb_genre'])]
        except re.error:
            return JSONResponse(content={"error": "Invalid regex pattern for genre."}, status_code=400)
    if studio:
        try:
            pattern = re.compile(studio, re.IGNORECASE)
            results = [m for m in results if m.get('production_companies') and pattern.search(m['production_companies'])]
        except re.error:
            return JSONResponse(content={"error": "Invalid regex pattern for studio."}, status_code=400)
    return JSONResponse(content={"results": results, "count": len(results)})

@app.get("/movies/by-imdb/{imdb_id}")
async def movie_by_imdb(imdb_id: str):
    for movies in movies_by_day_index.values():
        for m in movies:
            if m.get('imdb_id') == imdb_id:
                return JSONResponse(content=m)
    return JSONResponse(content={"error": "Movie not found"}, status_code=404)

@app.get("/movies/by-title")
async def movie_by_title(title: str = Query(..., description="Regex pattern for title")):
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
    If the user accesses /movies/by-day/ without a date, return an error with usage instructions.
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
    Render an About page with information about the tool, usage, and project author.
    """
    from datetime import datetime
    return templates.TemplateResponse(request, "about.html", {
        "request": request,
        "title": "About | MoviesThisDay",
        "about_info": {
            "what": "MoviesThisDay is a simple tool to provide a list of movies made on this date in history. It uses a local TMDB-derived dataset and offers both a modern web UI and a robust API.",
            "how": [
                "Use the homepage (/) to browse movies released on today's date.",
                "Use the date picker or navigation to view other days.",
                "Access the API endpoints for advanced queries (see below)."
            ],
            "api_examples": [
                {"desc": "Movies released today (JSON)", "cmd": "curl -X GET 'http://localhost:8000/movies/today'"},
                {"desc": "Movies by day (MM-DD)", "cmd": "curl -X GET 'http://localhost:8000/movies/by-day/06-15'"},
                {"desc": "Search by title (regex)", "cmd": "curl -G --data-urlencode 'title=matrix' 'http://localhost:8000/movies/by-title'"},
                {"desc": "Search by studio (regex)", "cmd": "curl -G --data-urlencode 'studio=Warner' 'http://localhost:8000/movies/by-studio'"}
            ],
            "author": "Jason A. Cox",
            "project": "Open source project for movie data exploration."
        },
        "current_year": datetime.now().year,
        "version": VERSION
    })

@app.get("/version")
async def version():
    """Return the current MoviesThisDay app version."""
    return {"version": VERSION}
