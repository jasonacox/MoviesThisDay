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

# TMDB_movie_dataset_v11.csv columns:
# "id","title","vote_average","vote_count","status",
# "release_date","revenue","runtime","adult","backdrop_path",
# "budget","homepage","imdb_id","original_language",
# "original_title","overview","popularity","poster_path",
# "tagline","genres","production_companies","production_countries",
# "spoken_languages","keywords"

print("Reading TMDB_movie_dataset_v11.csv...")
# Count total rows for progress bar
with open('TMDB_movie_dataset_v11.csv', encoding='utf-8') as f:
    total_rows = sum(1 for _ in f) - 1  # minus header
with open('TMDB_movie_dataset_v11.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    row_count = 0
    added_count = 0
    min_popularity = float('inf')
    max_popularity = float('-inf')
    most_recent_date = None
    most_recent_date_str = None
    sum_popularity_over_10 = 0.0
    count_popularity_over_10 = 0
    # Load OMDb API key from .env
    load_dotenv()
    OMDB_API_KEY = os.getenv('OMDB_API_KEY')
    
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
    
    for row in reader:
        row_count += 1
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
            
        """
        {"Title":"The Avengers","Year":"2012","Rated":"PG-13","Released":"04 May 2012","Runtime":"143 min","Genre":"Action, Sci-Fi","Director":"Joss Whedon","Writer":"Joss Whedon, Zak Penn","Actors":"Robert Downey Jr., Chris Evans, Scarlett Johansson","Plot":"Earth's mightiest heroes must come together and learn to fight as a team if they are going to stop the mischievous Loki and his alien army from enslaving humanity.","Language":"English, Russian","Country":"United States","Awards":"Nominated for 1 Oscar. 39 wins & 81 nominations total","Poster":"https://m.media-amazon.com/images/M/MV5BNGE0YTVjNzUtNzJjOS00NGNlLTgxMzctZTY4YTE1Y2Y1ZTU4XkEyXkFqcGc@._V1_SX300.jpg","Ratings":[{"Source":"Internet Movie Database","Value":"8.0/10"},{"Source":"Rotten Tomatoes","Value":"91%"},{"Source":"Metacritic","Value":"69/100"}],"Metascore":"69","imdbRating":"8.0","imdbVotes":"1,511,483","imdbID":"tt0848228","Type":"movie","DVD":"N/A","BoxOffice":"$623,357,910","Production":"N/A","Website":"N/A","Response":"True"}
        
        Key Fields:
        - Title
        - Released (e.g., "04 May 2012")
        - imdbID (e.g., "tt0848228")
        - Runtime (e.g., "143 min")
        - Language (e.g., "English, Russian")
        - Country (e.g., "United States")
        - Awards (e.g., "Nominated for 1 Oscar. 39 wins & 81 nominations total")
        - imdbRating (e.g., "8.0")
        - imdbVotes (e.g., "1,511,483")
        - Plot (e.g., "Earth's mightiest heroes must come together and learn to fight as a team if they are going to stop the mischievous Loki and his alien army from enslaving humanity.")
        - Genre (e.g., "Action, Sci-Fi")
        - Director (e.g., "Joss Whedon")
        - Actors (e.g., "Robert Downey Jr., Chris Evans, Scarlett Johansson")
        - BoxOffice (e.g., "$623,357,910")
        - Production (e.g., "N/A")
        - Website (e.g., "N/A")
        - Response (e.g., "True")
        """
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
                }
                index[this_day].append(movie)
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
