#!/usr/bin/env python3
"""
MoviesToday Movie Database Build Script

This script processes a TMDB movie dataset CSV, enriches it with OMDb data (if available),
and builds a date-indexed movie database for the MoviesToday web service and API.

Features:
- Reads TMDB_movie_dataset_v11.csv and filters for English, non-adult, feature-length movies
- Fetches and caches OMDb data for popular movies (if OMDb API key is provided)
- Normalizes and enriches movie records with OMDb fields (genre, director, actors, etc.)
- Indexes movies by release month and day (MM_DD) for fast lookup
- Outputs both a JSON and a binary pickle file with metadata and the indexed movie data
- Designed for use by the MoviesToday FastAPI app

Requirements:
- pip install requests python-dotenv colorama

Author: Jason A. Cox
Project: https://github.com/jasonacox/MoviesToday
"""

import csv
import json
import os
import pickle
import requests
import time
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)

index = defaultdict(list)

# Configuration
LANGUAGES = ["en"]  # Only include English movies
ADULT = ["false"]  # Only include non-adult movies
RUNTIME = 20  # Minimum runtime in minutes
POPULARITY_THRESHOLD = 10  # Minimum popularity to consider fetching OMDB data
DEBUG = False  # Set to True for debug output
OMDB_RAW = "omdb_raw.jsonl"  # Raw OMDb data file
TMDB_TRENDING_CSV = "TMDB_trending_movies.csv"  # TMDB trending movies CSV file
TMDB_SNAPSHOT = "2025-07-01"  # Snapshot date for TMDB trending movies

# TMDB_movie_dataset_v11.csv columns:
# "id","title","vote_average","vote_count","status",
# "release_date","revenue","runtime","adult","backdrop_path",
# "budget","homepage","imdb_id","original_language",
# "original_title","overview","popularity","poster_path",
# "tagline","genres","production_companies","production_countries",
# "spoken_languages","keywords"


# Helper for colored status messages
def status(msg, color=Fore.CYAN, bold=True, bullet=True, header=False):
    """
    Print a colored status message with optional formatting.

    Args:
        msg (str): The message to print.
        color: Foreground color from colorama.Fore.
        bold (bool): If True, use bright style.
        bullet (bool): If True, prepend a bullet.
        header (bool): If True, print as a header with separators.
    """
    msg = msg.strip()
    style = Style.BRIGHT if bold else ""
    prefix = f"{style}{color}"
    suffix = Style.RESET_ALL

    if header:
        line = "=" * 60
        print(f"{prefix}\n{line}\n{msg}\n{line}{suffix}")
    else:
        bullet_str = " * " if bullet else ""
        print(f"{prefix}{bullet_str}{msg}{suffix}")


status("\nMoviesToday Database Build Script\n", Fore.WHITE, bold=True, header=True)

# =============================
# PHASE 1 - Setting up environment
# =============================
status("\nPhase 1 - Setting up environment\n", Fore.GREEN, header=True)
# Check for TMDB_movie_dataset_v11.csv before processing
TMDB_CSV = "TMDB_movie_dataset_v11.csv"
if not os.path.exists(TMDB_CSV):
    status(f"[ERROR] {TMDB_CSV} not found. Exiting now.\n", Fore.RED)
    exit(1)

# Load API kes from .env
status("Loading environment and API keys...", Fore.YELLOW, bullet=True)
load_dotenv()
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# TMDB genre id to name mapping
TMDB_GENRE_ID_TO_NAME = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}

# =============================
# PHASE 2 - Fetching TMDB trending movies
# =============================
status("\nPhase 2 - Fetching TMDB trending movies\n", Fore.GREEN, header=True)
# Fetch TMDB trending movies past snapshot date
if not TMDB_API_KEY:
    status(
        "[WARNING] No TMDB API key found. Skipping TMDB trending movies fetch.",
        Fore.YELLOW,
    )
else:
    status("Fetching TMDB trending movies...", Fore.GREEN)
    trending_movies = []
    trending_seen_ids = set()
    tmdb_trend = f"https://api.themoviedb.org/3/trending/movie/day"
    # Fetch trending movies (single page)
    for tmdb_url in [tmdb_trend]:
        status(f"Fetching TMDB movies... via {tmdb_url}")
        try:
            headers = {
                "accept": "application/json",
                "Authorization": "Bearer " + TMDB_API_KEY,
            }
            response = requests.get(tmdb_url, headers=headers, timeout=10)
            if response.status_code == 200:
                trending_data = response.json()
                status(f"Found {len(trending_data['results'])} trending movies.")
                for movie in trending_data["results"]:
                    trending_output = {}
                    # look up imdb for movie
                    id_movie = movie.get("id")
                    url = (
                        f"https://api.themoviedb.org/3/movie/{id_movie}?language=en-US"
                    )
                    resp2 = requests.get(url, headers=headers, timeout=10)
                    resp2_data = resp2.json()
                    trending_output["id"] = movie.get("id")
                    trending_output["title"] = movie.get("title")
                    trending_output["vote_average"] = resp2_data.get("vote_average")
                    trending_output["vote_count"] = resp2_data.get("vote_count")
                    trending_output["status"] = resp2_data.get("status", "")
                    trending_output["release_date"] = movie.get("release_date")
                    trending_output["revenue"] = resp2_data.get("revenue")
                    trending_output["runtime"] = resp2_data.get("runtime", "")
                    trending_output["adult"] = movie.get("adult", False)
                    trending_output["backdrop_path"] = resp2_data.get("backdrop_path")
                    trending_output["budget"] = resp2_data.get("budget")
                    trending_output["homepage"] = resp2_data.get("homepage")
                    trending_output["imdb_id"] = resp2_data.get("imdb_id", "")
                    trending_output["original_language"] = resp2_data.get("original_language")
                    trending_output["original_title"] = resp2_data.get("original_title", "")
                    overview = resp2_data.get("overview", "")
                    if overview:
                        overview = (
                            overview.replace("\r", " ")
                            .replace("\n", " ")
                            .replace("\t", " ")
                        )
                        filtered_overview = "".join(
                            c for c in overview if c.isalnum() or c in " .,!?;:()-'\"[]"
                        )
                        trending_output["overview"] = " ".join(filtered_overview.split())
                    else:
                        trending_output["overview"] = ""
                    trending_popularity = movie.get("popularity", 0.0)
                    if trending_popularity < POPULARITY_THRESHOLD:
                        trending_popularity = ( trending_popularity / POPULARITY_THRESHOLD ) + 10
                    trending_output["popularity"] = trending_popularity
                    trending_output["poster_path"] = resp2_data.get("poster_path")
                    trending_output["tagline"] = resp2_data.get("tagline", "")
                    genre_ids = movie.get("genre_ids", [])
                    if genre_ids and isinstance(genre_ids, list):
                        genre_names = [
                            TMDB_GENRE_ID_TO_NAME.get(gid)
                            for gid in genre_ids
                            if gid in TMDB_GENRE_ID_TO_NAME
                        ]
                        trending_output["genres"] = ", ".join(genre_names)
                    else:
                        trending_output["genres"] = ""
                    production_companies = resp2_data.get("production_companies", [])
                    company_names = [
                        company.get("name", "")
                        for company in production_companies
                        if company.get("name")
                    ]
                    trending_output["production_companies"] = ", ".join(company_names)
                    trending_output["production_countries"] = resp2_data.get("production_countries", [])
                    trending_output["spoken_languages"] = resp2_data.get("spoken_languages", [])
                    trending_output["keywords"] = resp2_data.get("keywords", {}).get("keywords", [])
                    if trending_output["id"] not in trending_seen_ids:
                        trending_seen_ids.add(trending_output["id"])
                        trending_movies.append(trending_output.copy())
                    # If title begins with TRON highlight in yellow
                    if trending_output['title'].startswith("TRON"):
                        status(
                            f"Added: {trending_output['title']} (ID: {trending_output['imdb_id']})",
                            Fore.YELLOW
                        )
                    else:
                        status(
                            f"Added: {trending_output['title']} (ID: {trending_output['imdb_id']})"
                        )
            else:
                status(
                    f"[ERROR] TMDB API request failed with status code {response.status_code}: {response.text}",
                    Fore.RED,
                )
                continue
        except requests.exceptions.RequestException as e:
            status(f"[ERROR] Error fetching TMDB trending movies: {e}", Fore.RED)

    # Fetch movies month by month from TMDB_SNAPSHOT through 2 years past today.
    # TMDB caps results at 500 pages per query, so a single release_date.gte spanning
    # many months would silently truncate; one month at a time stays well within that limit.
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + TMDB_API_KEY,
    }
    snapshot_date = datetime.strptime(TMDB_SNAPSHOT, "%Y-%m-%d").date()
    end_date = datetime.now().date().replace(year=datetime.now().year + 2)
    month_start = snapshot_date
    while month_start <= end_date:
        # Last day of this month
        if month_start.month == 12:
            month_end = month_start.replace(day=31)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
        gte = month_start.strftime("%Y-%m-%d")
        lte = min(month_end, end_date).strftime("%Y-%m-%d")
        status(f"TMDB: Fetching movies {gte} to {lte}...", Fore.GREEN)
        page = 1
        while True:
            popularity = 0.0
            tmdb_current_year = (
                f"https://api.themoviedb.org/3/discover/movie"
                f"?include_adult=false&include_video=false&language=en-US"
                f"&page={page}&release_date.gte={gte}&release_date.lte={lte}"
                f"&sort_by=release_date&with_runtime.gte=20"
            )
            try:
                response = requests.get(tmdb_current_year, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    status(
                        f"  Page {page}/{data.get('total_pages', '?')}: {len(data['results'])} movies"
                    )
                    for movie in data["results"]:
                        popularity = movie.get("popularity", 0.0)
                        try:
                            popularity = float(popularity)
                        except (ValueError, TypeError):
                            popularity = 0.0
                        if popularity < POPULARITY_THRESHOLD:
                            release_date_str = movie.get("release_date")
                            is_upcoming = False
                            if release_date_str:
                                try:
                                    release_date_dt = datetime.strptime(release_date_str, "%Y-%m-%d").date()
                                    is_upcoming = release_date_dt > datetime.now().date()
                                except Exception:
                                    is_upcoming = False
                            if is_upcoming and popularity > (POPULARITY_THRESHOLD / 2):
                                status(
                                    f"Upcoming movie '{movie.get('title','?')}' has popularity {popularity} - updating to {popularity + 5}",
                                    Fore.YELLOW,
                                )
                                popularity = popularity + 5
                            else:
                                continue
                        if movie.get("id") in trending_seen_ids:
                            continue
                        trending_output = {}
                        id_movie = movie.get("id")
                        url = f"https://api.themoviedb.org/3/movie/{id_movie}?language=en-US"
                        resp2 = requests.get(url, headers=headers, timeout=10)
                        resp2_data = resp2.json()
                        trending_output["id"] = movie.get("id")
                        trending_output["title"] = movie.get("title")
                        trending_output["vote_average"] = resp2_data.get("vote_average")
                        trending_output["vote_count"] = resp2_data.get("vote_count")
                        trending_output["status"] = resp2_data.get("status", "")
                        trending_output["release_date"] = movie.get("release_date")
                        trending_output["revenue"] = resp2_data.get("revenue")
                        trending_output["runtime"] = resp2_data.get("runtime", "")
                        trending_output["adult"] = movie.get("adult", False)
                        trending_output["backdrop_path"] = resp2_data.get("backdrop_path")
                        trending_output["budget"] = resp2_data.get("budget")
                        trending_output["homepage"] = resp2_data.get("homepage")
                        trending_output["imdb_id"] = resp2_data.get("imdb_id", "")
                        trending_output["original_language"] = resp2_data.get("original_language")
                        trending_output["original_title"] = resp2_data.get("original_title", "")
                        overview = resp2_data.get("overview", "")
                        if overview:
                            overview = (
                                overview.replace("\r", " ")
                                .replace("\n", " ")
                                .replace("\t", " ")
                            )
                            filtered_overview = "".join(
                                c for c in overview if c.isalnum() or c in " .,!?;:()-'\"[]"
                            )
                            trending_output["overview"] = " ".join(filtered_overview.split())
                        else:
                            trending_output["overview"] = ""
                        trending_output["popularity"] = popularity
                        trending_output["poster_path"] = resp2_data.get("poster_path")
                        trending_output["tagline"] = resp2_data.get("tagline", "")
                        genre_ids = movie.get("genre_ids", [])
                        if genre_ids and isinstance(genre_ids, list):
                            genre_names = [
                                TMDB_GENRE_ID_TO_NAME.get(gid)
                                for gid in genre_ids
                                if gid in TMDB_GENRE_ID_TO_NAME
                            ]
                            trending_output["genres"] = ", ".join(genre_names)
                        else:
                            trending_output["genres"] = ""
                        production_companies = resp2_data.get("production_companies", [])
                        company_names = [
                            company.get("name", "")
                            for company in production_companies
                            if company.get("name")
                        ]
                        trending_output["production_companies"] = ", ".join(company_names)
                        trending_output["production_countries"] = resp2_data.get("production_countries", [])
                        trending_output["spoken_languages"] = resp2_data.get("spoken_languages", [])
                        trending_output["keywords"] = resp2_data.get("keywords", {}).get("keywords", [])
                        if trending_output["id"] not in trending_seen_ids:
                            trending_seen_ids.add(trending_output["id"])
                            trending_movies.append(trending_output.copy())
                            status(
                                f"Added: {trending_output['title']} (ID: {trending_output['imdb_id']})"
                            )
                        else:
                            status(
                                f"Skipped duplicate: {trending_output['title']} (ID: {trending_output['id']})",
                                Fore.YELLOW,
                            )
                    total_pages = data.get("total_pages", 1)
                    if page >= total_pages:
                        break
                    page += 1
                else:
                    status(
                        f"[ERROR] TMDB API request failed with status code {response.status_code}: {response.text}",
                        Fore.RED,
                    )
                    break
            except requests.exceptions.RequestException as e:
                status(f"[ERROR] Error fetching TMDB movies ({gte} to {lte}): {e}", Fore.RED)
                break
        # Advance to first day of next month
        if month_start.month == 12:
            month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_start = month_start.replace(month=month_start.month + 1, day=1)
    # save it
    with open(TMDB_TRENDING_CSV, "w", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=trending_output.keys(), quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        for movie in trending_movies:
            writer.writerow(movie)
    status(f"TMDB new movies saved to {TMDB_TRENDING_CSV}.", Fore.GREEN, bullet=True)
    status(f"Found {len(trending_movies)} new TMDB movies.", Fore.GREEN, bullet=True)

# Concatenate TMDB_CSV and TMDB_TRENDING_CSV to temporary file
COMBINED_TMDB_CSV = "combined_tmdb.csv"
status(
    f"Combining {TMDB_CSV} and {TMDB_TRENDING_CSV} into {COMBINED_TMDB_CSV}...",
    Fore.CYAN,
)
with open(COMBINED_TMDB_CSV, "w", encoding="utf-8") as combined_file:
    # Write contents of the first file
    with open(TMDB_CSV, "r", encoding="utf-8") as file1:
        combined_file.write(file1.read())
    # Write contents of the second file, skipping the header
    with open(TMDB_TRENDING_CSV, "r", encoding="utf-8") as file2:
        lines = file2.readlines()
        combined_file.writelines(lines[1:])  # Skip header row

# =============================
# PHASE 3 - Processing combined TMDB data
# =============================
status("\nPhase 3 - Processing combined TMDB data\n", Fore.GREEN, header=True)
status(f"Reading {COMBINED_TMDB_CSV}...", Fore.CYAN)
# Count total rows for progress bar
with open(COMBINED_TMDB_CSV, encoding="utf-8") as f:
    total_rows = sum(1 for _ in f) - 1  # minus header
with open(COMBINED_TMDB_CSV, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    row_count = 0
    added_count = 0
    min_popularity = float("inf")
    max_popularity = float("-inf")
    most_recent_date = None
    most_recent_date_str = None
    sum_popularity_over_10 = 0.0
    count_popularity_over_10 = 0

    # =============================
    # PHASE 4 - Processing main CSV and enriching with OMDb data
    # =============================
    status(
        "\nPhase 4 - Processing main CSV and enriching with OMDb data\n",
        Fore.GREEN,
        header=True,
    )
    status("Loading OMDb cache...", Fore.YELLOW)

    # Load OMDb cache if it exists
    omdb_cache = {}
    if os.path.exists(OMDB_RAW):
        with open(OMDB_RAW, "r", encoding="utf-8") as raw_file:
            for line_num, line in enumerate(raw_file, 1):
                try:
                    data = json.loads(line)
                    imdb_id = data.get("imdbID")
                    if imdb_id:
                        omdb_cache[imdb_id] = data
                except json.JSONDecodeError as e:
                    status(f"[OMDb Cache] Skipping malformed JSON on line {line_num}: {e} - {line}", Fore.RED)
                except Exception as e:
                    status(f"[OMDb Cache] Unexpected error on line {line_num}: {e} - {line}", Fore.RED)
        status(
            f"Loaded {len(omdb_cache)} OMDb entries from cache.",
            Fore.YELLOW,
        )
    else:
        status("No OMDb cache file found.", Fore.YELLOW)

    # Use a requests.Session for OMDb requests to enable connection reuse
    omdb_session = requests.Session()
    # Open OMDb raw file once for the entire loop rather than per-fetch
    omdb_raw_file = open(OMDB_RAW, "a", encoding="utf-8") if OMDB_API_KEY else None

    # Main CSV processing loop

    status("Processing main CSV and enriching with OMDb data...", Fore.CYAN)
    status(f"Total rows in {TMDB_CSV}: {total_rows}")
    seen_ids = set()
    tmdb_id_to_movie = {}  # movie_id -> movie dict in the index (O(1) duplicate updates)
    imdb_id_to_movie = {}  # imdb_id -> movie dict already in the index
    for row in reader:
        row_count += 1
        movie_id = row["id"]
        # check for Lookout
        #if row["title"].startswith("Lookout"):
        #    print(row)
        #    input(f"Found Lookout movie: {row['title']} (ID: {movie_id})")
        # If we've already inserted this movie id, update it directly via dict lookup (O(1))
        if movie_id in seen_ids:
            mov = tmdb_id_to_movie[movie_id]
            old_release_date = mov.get("release_date")
            new_release_date = row["release_date"]
            mov.update({
                "popularity": row["popularity"],
                "vote_average": row["vote_average"],
                "vote_count": row["vote_count"],
                "title": row["title"],
                "release_date": new_release_date,
                "release_year": new_release_date.split("-")[0] if new_release_date else None,
                "status": row["status"],
                "revenue": row["revenue"],
                "runtime": row["runtime"],
                "budget": row["budget"],
                "adult": row["adult"],
                "backdrop_path": row["backdrop_path"],
                "homepage": row["homepage"],
                "imdb_id": row["imdb_id"],
                "original_language": row["original_language"],
                "original_title": row["original_title"],
                "overview": row["overview"],
                "poster_path": row["poster_path"],
                "tagline": row["tagline"],
                "genres": row["genres"],
                "production_companies": row["production_companies"],
                "production_countries": row["production_countries"],
                "spoken_languages": row["spoken_languages"],
                "keywords": row["keywords"],
            })
            # If release_date changed, move movie to the new MM_DD bucket
            if new_release_date and new_release_date != old_release_date:
                if len(new_release_date.split("-")) == 3:
                    new_mm_dd = f"{new_release_date.split('-')[1]}_{new_release_date.split('-')[2]}"
                    if old_release_date and len(old_release_date.split("-")) == 3:
                        old_mm_dd = f"{old_release_date.split('-')[1]}_{old_release_date.split('-')[2]}"
                        if new_mm_dd != old_mm_dd and mov in index.get(old_mm_dd, []):
                            index[old_mm_dd].remove(mov)
                            index[new_mm_dd].append(mov)
            continue
        # Check if the movie meets our criteria
        is_non_adult = row["adult"].lower() in ADULT
        is_target_language = row["original_language"] in LANGUAGES 

        # Convert runtime to integer, with 0 as default for empty values
        try:
            runtime = int(row["runtime"]) if row["runtime"] else 0
        except ValueError:
            runtime = 0

        is_long_enough = runtime >= RUNTIME or runtime == 0  # allow 0 (unknown) runtimes

        # Convert popularity to float for min/max
        try:
            popularity = float(row["popularity"]) if row["popularity"] else 0.0
        except ValueError:
            popularity = 0.0
        # Track average popularity > 10
        if popularity > 10:
            sum_popularity_over_10 += popularity
            count_popularity_over_10 += 1
        # Example of a row:
        # {
        #     "Title": "The Avengers",
        #     "Year": "2012",
        #     "Rated": "PG-13",
        #     "Released": "04 May 2012",
        #     "Runtime": "143 min",
        #     "Genre": "Action, Sci-Fi",
        #     "Director": "Joss Whedon",
        #     "Writer": "Joss Whedon, Zak Penn",
        #     "Actors": "Robert Downey Jr., Chris Evans, Scarlett Johansson",
        #     "Plot": "Earth's mightiest heroes must come together and learn to fight as a team if they are going to stop the mischievous Loki and his alien army from enslaving humanity.",
        #     "Language": "English, Russian",
        #     "Country": "United States",
        #     "Awards": "Nominated for 1 Oscar. 39 wins & 81 nominations total",
        #     "Poster": "https://m.media-amazon.com/images/M/MV5BNGE0YTVjNzUtNzJjOS00NGNlLTgxMzctZTY4YTE1Y2Y1ZTU4XkEyXkFqcGc@._V1_SX300.jpg",
        #     "Ratings": [
        #         {"Source": "Internet Movie Database", "Value": "8.0/10"},
        #         {"Source": "Rotten Tomatoes", "Value": "91%"},
        #         {"Source": "Metacritic", "Value": "69/100"}
        #     ],
        #     "Metascore": "69",
        #     "imdbRating": "8.0",
        #     "imdbVotes": "1,511,483",
        #     "imdbID": "tt0848228",
        #     "Type": "movie",
        #     "DVD": "N/A",
        #     "BoxOffice": "$623,357,910",
        #     "Production": "N/A",
        #     "Website": "N/A",
        #     "Response": "True"
        # }

        # Check for Lookout
        #if row["title"].lower().startswith("Lookout"):
        #    print(row)
        #    input(f"Found Lookout movie: {row['title']} (ID: {movie_id})")

        # Only check OMDb for valid movies
        if is_non_adult and is_target_language and is_long_enough:
            if DEBUG:
                status(
                    f"Movie {row_count}/{total_rows}: {row['title']} (ID: {row['id']})"
                )
            imdb_id = row.get("imdb_id")
            release_date = row.get("release_date")
            omdb_date = None
            omdb_json = None
            if imdb_id and OMDB_API_KEY:
                if imdb_id in omdb_cache:
                    omdb_json = omdb_cache[imdb_id]
                elif popularity >= POPULARITY_THRESHOLD:
                    # Fetch from OMDb API with retries for popular movies
                    for attempt in range(3):
                        try:
                            omdb_resp = omdb_session.get(
                                f"http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}",
                                timeout=10,
                            )
                            if omdb_resp.status_code == 200:
                                omdb_json = omdb_resp.json()
                                # write raw OMDb data to file and update cache
                                try:
                                    omdb_raw_file.write(
                                        json.dumps(omdb_json, ensure_ascii=False) + "\n"
                                    )
                                except Exception as e:
                                    status(f"Error writing OMDb data to file: {e}", Fore.RED)
                                omdb_cache[imdb_id] = omdb_json
                                break
                            else:
                                status(
                                    f"OMDb API error for {imdb_id}: {omdb_resp.status_code} - {omdb_resp.text}",
                                    Fore.RED,
                                )
                                break
                        except requests.exceptions.Timeout:
                            status(
                                f"Timeout fetching OMDb for {imdb_id}, attempt {attempt+1}/3",
                                Fore.YELLOW,
                            )
                            time.sleep(1)
                        except Exception as e:
                            status(f"Error fetching OMDb for {imdb_id}: {e}", Fore.RED)
                            break
                if omdb_json:
                    omdb_date = omdb_json.get("Released")
                    if omdb_date and omdb_date != "N/A":
                        try:
                            omdb_dt = datetime.strptime(omdb_date, "%d %b %Y")
                            omdb_date_str = omdb_dt.strftime("%Y-%m-%d")
                            if omdb_date_str and omdb_date_str != "N/A":
                                row["release_date"] = omdb_date_str
                        except Exception:
                            status(
                                f"Could not parse OMDb date '{omdb_date}' for {row['title']}",
                                Fore.RED,
                            )
                    # Save the OMDb data to the row
                    row["omdb_title"] = omdb_json.get("Title")
                    row["omdb_released"] = omdb_json.get("Released")
                    row["omdb_genre"] = omdb_json.get("Genre") or row.get("genre", "")
                    row["omdb_director"] = omdb_json.get("Director")
                    row["omdb_actors"] = omdb_json.get("Actors")
                    row["omdb_plot"] = omdb_json.get("Plot") or row.get("overview", "")
                    row["omdb_language"] = omdb_json.get("Language") or row.get("original_language", "")
                    row["omdb_country"] = omdb_json.get("Country") or row.get("production_countries", "")
                    row["omdb_awards"] = omdb_json.get("Awards")
                    row["omdb_imdb_rating"] = omdb_json.get("imdbRating")
                    row["omdb_imdb_votes"] = omdb_json.get("imdbVotes")
                    row["omdb_box_office"] = omdb_json.get("BoxOffice") or row.get("revenue")
                    row["omdb_poster"] = omdb_json.get("Poster") or row.get("poster_path")
                    row["omdb_rated"] = omdb_json.get("Rated")
        # Track min/max popularity
        if is_non_adult and is_target_language and is_long_enough:
            if popularity < min_popularity:
                min_popularity = popularity
            if popularity > max_popularity:
                max_popularity = popularity
            release_date = row["release_date"]
            # Track most recent release_date
            if release_date and len(release_date.split("-")) == 3:
                try:
                    dt = datetime.strptime(release_date, "%Y-%m-%d")
                    if (most_recent_date is None) or (dt > most_recent_date):
                        most_recent_date = dt
                        most_recent_date_str = release_date
                except ValueError:
                    pass
                month, day = release_date.split("-")[1:3]
                this_day = f"{month}_{day}"
                # Create the movie dictionary that will be used by the web service
                movie = {
                    "id": row["id"],
                    "title": row["title"],
                    "release_date": row["release_date"],
                    "original_language": row["original_language"],
                    "popularity": row["popularity"],
                    "vote_average": row["vote_average"],
                    "vote_count": row["vote_count"],
                    "imdb_id": row["imdb_id"],
                    "language": row["original_language"],
                    "release_year": row["release_date"].split("-")[0]
                    if row["release_date"]
                    else None,
                    "runtime": runtime,
                    "omdb_genre": row.get("omdb_genre"),
                    "omdb_imdb_rating": row.get("omdb_imdb_rating"),
                    "omdb_imdb_votes": row.get("omdb_imdb_votes"),
                    "omdb_box_office": row.get("omdb_box_office"),
                    "production_companies": row.get("production_companies", ""),
                    "omdb_poster": row.get("omdb_poster"),
                    "omdb_plot": row.get("omdb_plot"),
                    "omdb_rated": row.get("omdb_rated"),
                }
                # print(f" -- Adding movie: {movie['title']} (ID: {movie_id}, Release Date: {movie['release_date']})")
                # Deduplicate by IMDb ID — keep the highest-popularity entry
                imdb_id_val = movie.get("imdb_id")
                if imdb_id_val and imdb_id_val not in ("", "N/A"):
                    if imdb_id_val in imdb_id_to_movie:
                        existing = imdb_id_to_movie[imdb_id_val]
                        try:
                            existing_pop = float(existing.get("popularity", 0))
                            new_pop = float(movie.get("popularity", 0))
                        except (ValueError, TypeError):
                            existing_pop = new_pop = 0.0
                        if new_pop <= existing_pop:
                            continue
                        # New entry has higher popularity — evict the old one
                        old_date = existing.get("release_date", "")
                        if old_date and len(old_date.split("-")) == 3:
                            old_mm_dd = f"{old_date.split('-')[1]}_{old_date.split('-')[2]}"
                            bucket = index.get(old_mm_dd, [])
                            if existing in bucket:
                                bucket.remove(existing)
                                seen_ids.discard(existing["id"])
                                added_count -= 1
                    imdb_id_to_movie[imdb_id_val] = movie
                index[this_day].append(movie)
                seen_ids.add(movie_id)
                tmdb_id_to_movie[movie_id] = movie
                added_count += 1
        # Progress bar
        if row_count % 1000 == 0 or row_count == total_rows:
            percent = row_count / total_rows * 100
            bar = ("#" * int(percent // 4)).ljust(25)
            print(
                f"\r   Processing: [{bar}] {percent:.1f}% ({row_count}/{total_rows})",
                end="",
            )
    print()  # Newline after progress bar
    if omdb_raw_file:
        omdb_raw_file.close()
    if count_popularity_over_10 > 0:
        avg_popularity_over_10 = sum_popularity_over_10 / count_popularity_over_10
        status(
            f"Average popularity (popularity > 10): {avg_popularity_over_10:.2f} (from {count_popularity_over_10} movies)",
            Fore.CYAN,
        )
    else:
        status("No movies with popularity > 10 found.", Fore.CYAN)
status(
    f"Processed {row_count} rows. Added {added_count} non-adult movies to index.",
    Fore.GREEN,
)

# =============================
# PHASE 5 - Applying updates from updates.jsonl
# =============================
status("\nPhase 5 - Applying updates from updates.jsonl\n", Fore.GREEN, header=True)
status("Applying updates from updates.jsonl (if present)...", Fore.CYAN)


def apply_updates_jsonl(idx, updates_file_path):
    if not os.path.exists(updates_file_path):
        status(
            f"No updates file found at {updates_file_path}. Skipping updates.",
            Fore.YELLOW,
        )
        return
    imdb_to_movie = {}
    movie_to_day = {}
    # Build lookup tables for imdb_id -> movie and movie -> MM_DD key
    for day_key, day_movies in idx.items():
        for mov in day_movies:
            if mov.get("imdb_id"):
                imdb_to_movie[mov["imdb_id"]] = mov
                movie_to_day[id(mov)] = day_key
    with open(updates_file_path, "r", encoding="utf-8") as updates_file:
        for update_line in updates_file:
            try:
                update_obj = json.loads(update_line)
                update_imdb_id = update_obj.get("imdb_id")
                if not update_imdb_id:
                    continue
                mov = imdb_to_movie.get(update_imdb_id)
                if mov:
                    old_release_date = mov.get("release_date")
                    # Apply all fields except imdb_id and id
                    for k, v in update_obj.items():
                        if k not in ("imdb_id", "id"):
                            mov[k] = v
                    # If release_date changed, update release_year and move movie to new MM_DD index
                    new_release_date = mov.get("release_date")
                    if new_release_date and new_release_date != old_release_date:
                        # Update release_year to match new release_date
                        if len(new_release_date.split("-")) == 3:
                            mov["release_year"] = new_release_date.split("-")[0]
                        # Remove from old MM_DD
                        if old_release_date and len(old_release_date.split("-")) == 3:
                            old_mmdd = f"{old_release_date.split('-')[1]}_{old_release_date.split('-')[2]}"
                            if mov in idx.get(old_mmdd, []):
                                idx[old_mmdd].remove(mov)
                        # Add to new MM_DD
                        if len(new_release_date.split("-")) == 3:
                            new_mmdd = f"{new_release_date.split('-')[1]}_{new_release_date.split('-')[2]}"
                            idx[new_mmdd].append(mov)
                        # Update movie_to_day for this movie
                        movie_to_day[id(mov)] = new_mmdd
                    status(f"Updated {update_imdb_id}: {update_obj}")
                else:
                    status(
                        f"Update for {update_imdb_id} not applied (not found in index)",
                        Fore.YELLOW,
                    )
            except json.JSONDecodeError as err:
                status(f"Error parsing update line: {err}", Fore.RED)


# Apply updates if updates.jsonl exists
updates_path = "updates.jsonl"
if os.path.exists(updates_path):
    apply_updates_jsonl(index, updates_path)

# =============================
# PHASE 6 - Computing metrics
# =============================
status("\nPhase 6 - Computing metrics\n", Fore.GREEN, header=True)
# --- Compute popularity rank for all movies ---
status("Computing popularity ranks...", Fore.CYAN)
movie_popularity_list = []  # List of (movie_id, popularity)
for movies_per_day in index.values():
    for movie in movies_per_day:
        try:
            pop = float(movie.get("popularity", 0.0))
        except (ValueError, TypeError):
            pop = 0.0
        movie_popularity_list.append((movie["id"], pop))
# Sort by popularity descending
movie_popularity_list.sort(key=lambda x: x[1], reverse=True)
# Assign rank (1 = most popular)
movie_id_to_rank = {
    movie_id: rank + 1 for rank, (movie_id, _) in enumerate(movie_popularity_list)
}
# Add rank to each movie
for movies_per_day in index.values():
    for movie in movies_per_day:
        movie["popularity_rank"] = movie_id_to_rank.get(movie["id"])
status("Popularity ranks assigned.", Fore.GREEN)

# Prepare metadata
status("Preparing metadata...", Fore.CYAN)
num_movies = sum(len(movies) for movies in index.values())
num_movies_popular = 0
for movies in index.values():
    for movie in movies:
        try:
            if float(movie.get("popularity", 0.0)) >= POPULARITY_THRESHOLD:
                num_movies_popular += 1
        except (ValueError, TypeError):
            pass
metadata = {
    "generated_at": datetime.now().isoformat(),
    "build_timestamp": int(time.time()),
    "project_url": "https://github.com/jasonacox/MoviesToday",
    "min_popularity": min_popularity if min_popularity != float("inf") else None,
    "max_popularity": max_popularity if max_popularity != float("-inf") else None,
    "most_recent_release_date": most_recent_date_str,
    "avg_popularity_over_10": avg_popularity_over_10
    if count_popularity_over_10 > 0
    else None,
    "count_popularity_over_10": count_popularity_over_10,
    "num_movies": num_movies,
    "num_movies_popular": num_movies_popular,
    "LANGUAGES": LANGUAGES,
    "ADULT": ADULT,
    "RUNTIME": RUNTIME,
    "POPULARITY_THRESHOLD": POPULARITY_THRESHOLD,
}

# =============================
# PHASE 7 - Writing output files
# =============================
status("\nPhase 7 - Writing output files\n", Fore.GREEN, header=True)
# Write the index to a JSON file
json_path = "movies_by_day.json"
status(f"Writing movies_by_day.json...", Fore.MAGENTA)
json_output = {"metadata": metadata, "index": dict(index)}
with open(json_path, "w", encoding="utf-8") as jsonfile:
    json.dump(json_output, jsonfile, ensure_ascii=False, indent=2)
json_size = os.path.getsize(json_path)
status(f"Done! JSON file created as {json_path} ({json_size} bytes).", Fore.GREEN)

# Write the index to a binary pickle file
pkl_path = "movies_by_day.pkl"
status(f"Writing movies_by_day.pkl (binary index)...", Fore.MAGENTA)
pkl_output = {"metadata": metadata, "index": dict(index)}
with open(pkl_path, "wb") as pklfile:
    pickle.dump(pkl_output, pklfile)
pkl_size = os.path.getsize(pkl_path)

# =============================
# PHASE 8 - Completed - Status Report
# =============================
status("\nPhase 8 - Completed - Status Report\n", Fore.GREEN, header=True)
# Print final status
status(f"Binary file created as {pkl_path} ({pkl_size} bytes).", Fore.GREEN)
status(f"Total unique release date indexes created: {len(index)}", Fore.CYAN)
status(f"Min popularity: {metadata['min_popularity']}", Fore.CYAN)
status(f"Max popularity: {metadata['max_popularity']}", Fore.CYAN)
status(f"Most recent release_date: {metadata['most_recent_release_date']}", Fore.CYAN)
status(f"Total movies processed: {metadata['num_movies']}", Fore.CYAN)
status(f"Total popular movies (above {POPULARITY_THRESHOLD}): {metadata['num_movies_popular']}", Fore.CYAN)

print()

# Example: how to load the binary index
# with open('movies_by_day.pkl', 'rb') as pklfile:
#     index = pickle.load(pklfile)
#     print(index.get('06_14', []))
