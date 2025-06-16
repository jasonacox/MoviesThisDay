import argparse
import pickle
from datetime import datetime

POPULARITY_THRESHOLD = 10  # Set a threshold for movie popularity
AGE_LIMIT = 100  # Maximum age of movie in years (default 100)

# Load the binary index and metadata
with open('movie_db/movies_by_day.pkl', 'rb') as pklfile:
    db = pickle.load(pklfile)
    metadata = db.get('metadata', {})
    index = db.get('index', {})

parser = argparse.ArgumentParser(description="Show movies released on a specific date (MM-DD). Defaults to today.")
parser.add_argument('--date', type=str, help='Date in MM-DD format (e.g., 06-14)')
args = parser.parse_args()

if args.date:
    mm_dd = args.date.replace('-', '_')
else:
    mm_dd = datetime.now().strftime('%m_%d')

current_year = datetime.now().year

movies_today = [
    movie for movie in index.get(mm_dd, [])
    if float(movie.get('popularity', 0)) > POPULARITY_THRESHOLD
    and (current_year - int(movie['release_year'])) <= AGE_LIMIT
]

movies_today.sort(key=lambda m: float(m.get('popularity', 0)), reverse=True)

print(f"Movies released on {mm_dd.replace('_', '-')}:")
if movies_today:
    for movie in movies_today:
        print(f"- {movie['title']} (Popularity: {movie.get('popularity', 'N/A')}, Release Date: {movie['release_date']})")
else:
    print("No movies found for today.")
print(f"Total: {len(movies_today)}")

# Optionally, print metadata
print(f"\nDatabase generated at: {metadata.get('generated_at', 'N/A')}")
print(f"Project: {metadata.get('project_url', 'N/A')}")
if 'avg_popularity_over_10' in metadata:
    print(f"Average popularity (popularity > 10): {metadata['avg_popularity_over_10']:.2f} (from {metadata.get('count_popularity_over_10', 0)} movies)")