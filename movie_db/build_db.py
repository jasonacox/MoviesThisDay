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
from datetime import datetime
from dotenv import load_dotenv

index = defaultdict(list)

# Configuration
LANGUAGES = ['en']          # Only include English movies
ADULT = ['false']           # Only include non-adult movies
RUNTIME = 20                # Minimum runtime in minutes
POPULARITY_THRESHOLD = 10   # Minimum popularity to consider fetching OMDB data
DEBUG = False               # Set to True for debug output
OMDB_RAW = "omdb_raw.jsonl" # Raw OMDb data file
TMDB_TRENDING_CSV = 'TMDB_trending_movies.csv'  # TMDB trending movies CSV file

# TMDB_movie_dataset_v11.csv columns:
# "id","title","vote_average","vote_count","status",
# "release_date","revenue","runtime","adult","backdrop_path",
# "budget","homepage","imdb_id","original_language",
# "original_title","overview","popularity","poster_path",
# "tagline","genres","production_companies","production_countries",
# "spoken_languages","keywords"

# Check for TMDB_movie_dataset_v11.csv before processing
TMDB_CSV = 'TMDB_movie_dataset_v11.csv'
if not os.path.exists(TMDB_CSV):
    print(f"[ERROR] {TMDB_CSV} not found. Exiting now.\n")
    exit(1)

# Load API kes from .env
load_dotenv()
OMDB_API_KEY = os.getenv('OMDB_API_KEY')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

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
    37: "Western"
}

# Fetch TMDB trending movies
if not TMDB_API_KEY:
    print("[WARNING] No TMDB API key found. Skipping TMDB trending movies fetch.")
else:
    trending_movies = []
    tmdb_trend = f'https://api.themoviedb.org/3/trending/movie/day'
    tmdb_current_year = f'https://api.themoviedb.org/3/discover/movie?language=en-US&sort_by=popularity.desc&include_adult=false&include_video=false&page=1&primary_release_year={datetime.now().year}'
    for tmdb_url in [tmdb_trend, tmdb_current_year]:
        print(f"Fetching TMDB movies... via {tmdb_url}")
        try:
            headers = {
                "accept": "application/json",
                "Authorization": "Bearer " + TMDB_API_KEY
            }
            response = requests.get(tmdb_url, headers=headers, timeout=10)
            if response.status_code == 200:
                trending_data = response.json()
                print(f"Found {len(trending_data['results'])} trending movies.")
                #print(trending_data)
                # "id","title","vote_average","vote_count","status","release_date","revenue","runtime","adult","backdrop_path","budget","homepage","imdb_id","original_language","original_title","overview","popularity","poster_path","tagline","genres","production_companies","production_countries","spoken_languages","keywords"
                # Save trending movies to CSV in the same format as TMDB_CSV
                for movie in trending_data['results']:
                    trending_output = {}
                    # look up imdb for movie
                    id_movie = movie.get('id')
                    url = f"https://api.themoviedb.org/3/movie/{id_movie}?language=en-US"
                    resp2 = requests.get(url, headers=headers, timeout=10)
                    #print(f"---{id_movie}--->>")
                    #print(resp2.json())
                    trending_output["id"] = movie.get("id")
                    trending_output["title"] = movie.get("title")
                    trending_output["vote_average"] = resp2.json().get("vote_average")
                    trending_output["vote_count"] = resp2.json().get("vote_count")
                    trending_output["status"] = resp2.json().get("status", "")
                    trending_output["release_date"] = movie.get("release_date")
                    trending_output["revenue"] = resp2.json().get("revenue")
                    trending_output["runtime"] = resp2.json().get("runtime", "")
                    trending_output["adult"] = movie.get("adult", False)
                    trending_output["backdrop_path"] = resp2.json().get("backdrop_path")
                    trending_output["budget"] = resp2.json().get("budget")
                    trending_output["homepage"] = resp2.json().get("homepage")
                    trending_output["imdb_id"] = resp2.json().get("imdb_id", "")
                    trending_output["original_language"] = resp2.json().get("original_language")
                    trending_output["original_title"] = resp2.json().get("original_title", "")
                    # Filter overview text to only allow alphanumeric chars and basic punctuation
                    overview = resp2.json().get("overview", "")
                    if overview:
                        # Replace line breaks first
                        overview = overview.replace("\r", " ").replace("\n", " ").replace("\t", " ")
                        # Filter to only allow alphanumeric chars and basic punctuation
                        filtered_overview = ''.join(c for c in overview if c.isalnum() or c in " .,!?;:()-'\"[]")
                        # Normalize whitespace
                        trending_output["overview"] = ' '.join(filtered_overview.split())
                    else:
                        trending_output["overview"] = ""
                    trending_output["popularity"] = movie.get("popularity", 0.0)
                    trending_output["poster_path"] = resp2.json().get("poster_path")
                    trending_output["tagline"] = resp2.json().get("tagline", "")
                    # Convert genre_ids to genre names
                    genre_ids = movie.get("genre_ids", [])
                    if genre_ids and isinstance(genre_ids, list):
                        genre_names = [TMDB_GENRE_ID_TO_NAME.get(gid) for gid in genre_ids if gid in TMDB_GENRE_ID_TO_NAME]
                        trending_output["genres"] = ", ".join(genre_names)
                    else:
                        trending_output["genres"] = ""
                    # Convert production companies to comma-separated string
                    production_companies = resp2.json().get("production_companies", [])
                    company_names = [company.get("name", "") for company in production_companies if company.get("name")]
                    trending_output["production_companies"] = ", ".join(company_names)
                    trending_output["production_countries"] = resp2.json().get("production_countries", [])
                    trending_output["spoken_languages"] = resp2.json().get("spoken_languages", [])
                    trending_output["keywords"] = resp2.json().get("keywords", {}).get("keywords", [])
                    trending_movies.append(trending_output.copy())
                    print(f"Added: {trending_output['title']} (ID: {trending_output['imdb_id']})")
            else:
                print(f"[ERROR] TMDB API request failed with status code {response.status_code}: {response.text}")
                continue
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error fetching TMDB trending movies: {e}")
    # save it
    with open(TMDB_TRENDING_CSV, 'w', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=trending_output.keys(), quoting=csv.QUOTE_ALL)
        # writer.writeheader()
        for movie in trending_movies:
            writer.writerow(movie)
    print(f"TMDB new movies saved to {TMDB_TRENDING_CSV}.")
    print(f"Found {len(trending_movies)} new TMDB movies.")

# Concatenate TMDB_CSV and TMDB_TRENDING_CSV to temporary file
COMBINED_TMDB_CSV = 'combined_tmdb.csv'
print(f"Combining {TMDB_CSV} and {TMDB_TRENDING_CSV} into {COMBINED_TMDB_CSV}...")
with open(COMBINED_TMDB_CSV, 'w', encoding='utf-8') as combined_file:
    # Write contents of the first file
    with open(TMDB_CSV, 'r', encoding='utf-8') as file1:
        combined_file.write(file1.read())
    # Write contents of the second file, skipping the header
    with open(TMDB_TRENDING_CSV, 'r', encoding='utf-8') as file2:
        lines = file2.readlines()
        combined_file.writelines(lines[1:])  # Skip header row

print(f"Reading {COMBINED_TMDB_CSV}...")
# Count total rows for progress bar
with open(COMBINED_TMDB_CSV, encoding='utf-8') as f:
    total_rows = sum(1 for _ in f) - 1  # minus header
with open(COMBINED_TMDB_CSV, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    row_count = 0
    added_count = 0
    min_popularity = float('inf')
    max_popularity = float('-inf')
    most_recent_date = None
    most_recent_date_str = None
    sum_popularity_over_10 = 0.0
    count_popularity_over_10 = 0

    # Load OMDb cache if it exists
    omdb_cache = {}
    if os.path.exists(OMDB_RAW):
        with open(OMDB_RAW, 'r', encoding='utf-8') as raw_file:
            for line in raw_file:
                try:
                    data = json.loads(line)
                    imdb_id = data.get('imdbID')
                    if imdb_id:
                        omdb_cache[imdb_id] = data
                except Exception:
                    pass
    
    # Use a requests.Session for OMDb requests to enable connection reuse
    omdb_session = requests.Session()
    
    # Main CSV processing loop
    print(f"Total rows in {TMDB_CSV}: {total_rows}")
    seen_ids = set()
    for row in reader:
        row_count += 1
        movie_id = row['id']
        # If we've already inserted this movie id, update popularity in the index and continue
        if movie_id in seen_ids:
            #print(f"Movie ID {movie_id} already seen, updating popularity... {row['title']}")
            #print(row)
            # Search index for this movie id and update popularity, vote_average, vote_count, and title
            for movies_list in index.values():
                for mov in movies_list:
                    if mov['id'] == movie_id:
                        mov['popularity'] = row['popularity']
                        mov['vote_average'] = row['vote_average']
                        mov['vote_count'] = row['vote_count']
                        mov['title'] = row['title']
                        #print(f"^^ Updated movie {mov['title']} (ID: {movie_id}) with new popularity {mov['popularity']}")
                        break
            continue
        # Check if the movie meets our criteria
        is_non_adult = row['adult'].lower() in ADULT
        is_target_language = row['original_language'] in LANGUAGES
        
        # Convert runtime to integer, with 0 as default for empty values
        try:
            runtime = int(row['runtime']) if row['runtime'] else 0
        except ValueError:
            runtime = 0
            
        is_long_enough = runtime >= RUNTIME
        
        # Convert popularity to float for min/max
        try:
            popularity = float(row['popularity']) if row['popularity'] else 0.0
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

        # Only check OMDb for valid movies
        if is_non_adult and is_target_language and is_long_enough:
            if DEBUG:
                print(f"Movie {row_count}/{total_rows}: {row['title']} (ID: {row['id']})")
            imdb_id = row.get('imdb_id')
            release_date = row.get('release_date')
            omdb_date = None
            omdb_json = None
            if imdb_id and OMDB_API_KEY:
                if imdb_id in omdb_cache:
                    omdb_json = omdb_cache[imdb_id]
                elif popularity >= POPULARITY_THRESHOLD:
                    for attempt in range(3):
                        try:
                            omdb_resp = omdb_session.get(f'http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}', timeout=10)
                            if omdb_resp.status_code == 200:
                                omdb_json = omdb_resp.json()
                                # write raw OMDb data to file and update cache
                                with open(OMDB_RAW, 'a', encoding='utf-8') as raw_file:
                                    raw_file.write(json.dumps(omdb_json, ensure_ascii=False) + '\n')
                                omdb_cache[imdb_id] = omdb_json
                                break
                            else:
                                print(f"OMDb API error for {imdb_id}: {omdb_resp.status_code} - {omdb_resp.text}")
                                break
                        except requests.exceptions.Timeout:
                            print(f"Timeout fetching OMDb for {imdb_id}, attempt {attempt+1}/3")
                            time.sleep(1)
                        except Exception as e:
                            print(f"Error fetching OMDb for {imdb_id}: {e}")
                            break
                if omdb_json:
                    omdb_date = omdb_json.get('Released')
                    if omdb_date and omdb_date != 'N/A':
                        try:
                            omdb_dt = datetime.strptime(omdb_date, '%d %b %Y')
                            omdb_date_str = omdb_dt.strftime('%Y-%m-%d')
                            if omdb_date_str and omdb_date_str != 'N/A':
                                row['release_date'] = omdb_date_str
                        except Exception:
                            print(f"Could not parse OMDb date '{omdb_date}' for {row['title']}")
                    # Save the OMDb data to the row
                    row['omdb_title'] = omdb_json.get('Title')
                    row['omdb_released'] = omdb_json.get('Released')
                    row['omdb_genre'] = omdb_json.get('Genre')
                    row['omdb_director'] = omdb_json.get('Director')
                    row['omdb_actors'] = omdb_json.get('Actors')
                    row['omdb_plot'] = omdb_json.get('Plot')
                    row['omdb_language'] = omdb_json.get('Language')
                    row['omdb_country'] = omdb_json.get('Country')
                    row['omdb_awards'] = omdb_json.get('Awards')
                    row['omdb_imdb_rating'] = omdb_json.get('imdbRating')
                    row['omdb_imdb_votes'] = omdb_json.get('imdbVotes')
                    row['omdb_box_office'] = omdb_json.get('BoxOffice')
                    row['omdb_poster'] = omdb_json.get('Poster')
        # Track min/max popularity
        if is_non_adult and is_target_language and is_long_enough:
            if popularity < min_popularity:
                min_popularity = popularity
            if popularity > max_popularity:
                max_popularity = popularity
            release_date = row['release_date']
            # Track most recent release_date
            if release_date and len(release_date.split('-')) == 3:
                try:
                    dt = datetime.strptime(release_date, '%Y-%m-%d')
                    if (most_recent_date is None) or (dt > most_recent_date):
                        most_recent_date = dt
                        most_recent_date_str = release_date
                except ValueError:
                    pass
                month, day = release_date.split('-')[1:3]
                this_day = f"{month}_{day}"
                # Create the movie dictionary that will be used by the web service
                movie = {
                    'id': row['id'],
                    'title': row['title'],
                    'release_date': row['release_date'],
                    'original_language': row['original_language'],
                    'popularity': row['popularity'],
                    'vote_average': row['vote_average'],
                    'vote_count': row['vote_count'],
                    'imdb_id': row['imdb_id'],
                    'language': row['original_language'],
                    'release_year': row['release_date'].split('-')[0] if row['release_date'] else None,
                    'runtime': runtime,
                    'omdb_genre': row.get('omdb_genre'),
                    'omdb_imdb_rating': row.get('omdb_imdb_rating'),
                    'omdb_imdb_votes': row.get('omdb_imdb_votes'),
                    'omdb_box_office': row.get('omdb_box_office'),
                    'production_companies': row.get('production_companies', ''),
                    'omdb_poster': row.get('omdb_poster'),
                    'omdb_plot': row.get('omdb_plot'),
                }
                #print(f" -- Adding movie: {movie['title']} (ID: {movie_id}, Release Date: {movie['release_date']})")
                index[this_day].append(movie)
                seen_ids.add(movie_id)
                added_count += 1
        # Progress bar
        if row_count % 1000 == 0 or row_count == total_rows:
            percent = row_count / total_rows * 100
            bar = ('#' * int(percent // 4)).ljust(25)
            print(f"\rProcessing: [{bar}] {percent:.1f}% ({row_count}/{total_rows})", end='')
    print()  # Newline after progress bar
    if count_popularity_over_10 > 0:
        avg_popularity_over_10 = sum_popularity_over_10 / count_popularity_over_10
        print(f"Average popularity (popularity > 10): {avg_popularity_over_10:.2f} (from {count_popularity_over_10} movies)")
    else:
        print("No movies with popularity > 10 found.")
print(f"Processed {row_count} rows. Added {added_count} non-adult movies to index.")

# --- Apply corrections from updates.jsonl (if present) ---
def apply_updates_jsonl(idx, updates_file_path):
    if not os.path.exists(updates_file_path):
        print(f"No updates file found at {updates_file_path}. Skipping updates.")
        return
    print(f"Applying updates from {updates_file_path} (jsonl)...")
    imdb_to_movie = {}
    movie_to_day = {}
    # Build lookup tables for imdb_id -> movie and movie -> MM_DD key
    for day_key, day_movies in idx.items():
        for mov in day_movies:
            if mov.get('imdb_id'):
                imdb_to_movie[mov['imdb_id']] = mov
                movie_to_day[id(mov)] = day_key
    with open(updates_file_path, 'r', encoding='utf-8') as updates_file:
        for update_line in updates_file:
            try:
                update_obj = json.loads(update_line)
                update_imdb_id = update_obj.get('imdb_id')
                if not update_imdb_id:
                    continue
                mov = imdb_to_movie.get(update_imdb_id)
                if mov:
                    old_release_date = mov.get('release_date')
                    # Apply all fields except imdb_id and id
                    for k, v in update_obj.items():
                        if k not in ('imdb_id', 'id'):
                            mov[k] = v
                    # If release_date changed, move movie to new MM_DD index
                    new_release_date = mov.get('release_date')
                    if new_release_date and new_release_date != old_release_date:
                        # Remove from old MM_DD
                        if old_release_date and len(old_release_date.split('-')) == 3:
                            old_mmdd = f"{old_release_date.split('-')[1]}_{old_release_date.split('-')[2]}"
                            if mov in idx.get(old_mmdd, []):
                                idx[old_mmdd].remove(mov)
                        # Add to new MM_DD
                        if len(new_release_date.split('-')) == 3:
                            new_mmdd = f"{new_release_date.split('-')[1]}_{new_release_date.split('-')[2]}"
                            idx[new_mmdd].append(mov)
                        # Update movie_to_day for this movie
                        movie_to_day[id(mov)] = new_mmdd
                    print(f"Updated {update_imdb_id}: {update_obj}")
                else:
                    print(f"Update for {update_imdb_id} not applied (not found in index)")
            except json.JSONDecodeError as err:
                print(f"Error parsing update line: {err}")

# Apply updates if updates.jsonl exists
updates_path = 'updates.jsonl'
if os.path.exists(updates_path):
    apply_updates_jsonl(index, updates_path)

# --- Compute popularity rank for all movies ---
print("Computing popularity ranks...")
movie_popularity_list = []  # List of (movie_id, popularity)
for movies_per_day in index.values():
    for movie in movies_per_day:
        try:
            pop = float(movie.get('popularity', 0.0))
        except (ValueError, TypeError):
            pop = 0.0
        movie_popularity_list.append((movie['id'], pop))
# Sort by popularity descending
movie_popularity_list.sort(key=lambda x: x[1], reverse=True)
# Assign rank (1 = most popular)
movie_id_to_rank = {movie_id: rank+1 for rank, (movie_id, _) in enumerate(movie_popularity_list)}
# Add rank to each movie
for movies_per_day in index.values():
    for movie in movies_per_day:
        movie['popularity_rank'] = movie_id_to_rank.get(movie['id'])
print("Popularity ranks assigned.")

# Prepare metadata
metadata = {
    'generated_at': datetime.now().isoformat(),
    'project_url': 'https://github.com/jasonacox/MoviesToday',
    'min_popularity': min_popularity if min_popularity != float('inf') else None,
    'max_popularity': max_popularity if max_popularity != float('-inf') else None,
    'most_recent_release_date': most_recent_date_str,
    'avg_popularity_over_10': avg_popularity_over_10 if count_popularity_over_10 > 0 else None,
    'count_popularity_over_10': count_popularity_over_10
}

# Write the index to a JSON file
json_path = 'movies_by_day.json'
print(f"Writing {json_path}...")
json_output = {
    'metadata': metadata,
    'index': dict(index)
}
with open(json_path, 'w', encoding='utf-8') as jsonfile:
    json.dump(json_output, jsonfile, ensure_ascii=False, indent=2)
json_size = os.path.getsize(json_path)
print(f"Done! JSON file created as {json_path} ({json_size} bytes).")

# Write the index to a binary pickle file
pkl_path = 'movies_by_day.pkl'
print(f"Writing {pkl_path} (binary index)...")
pkl_output = {
    'metadata': metadata,
    'index': dict(index)
}
with open(pkl_path, 'wb') as pklfile:
    pickle.dump(pkl_output, pklfile)
pkl_size = os.path.getsize(pkl_path)
print(f"Done! Binary file created as {pkl_path} ({pkl_size} bytes).")

print(f"Total unique release date indexes created: {len(index)}")
print("All done!")
print(f"Min popularity: {metadata['min_popularity']}")
print(f"Max popularity: {metadata['max_popularity']}")
print(f"Most recent release_date: {metadata['most_recent_release_date']}")

# Example: how to load the binary index
# with open('movies_by_day.pkl', 'rb') as pklfile:
#     index = pickle.load(pklfile)
#     print(index.get('06_14', []))
