#!/usr/bin/env python3
"""Check movies_by_day.pkl for duplicate movies by TMDB id and imdb_id."""

import pickle
from collections import defaultdict

with open("movies_by_day.pkl", "rb") as f:
    db = pickle.load(f)

index = db.get("index", {})

# Track all occurrences keyed by tmdb id and imdb_id
by_tmdb_id = defaultdict(list)
by_imdb_id = defaultdict(list)

for day_key, movies in index.items():
    for m in movies:
        tmdb_id = m.get("id")
        imdb_id = m.get("imdb_id")
        entry = (day_key, m.get("title"), m.get("release_date"))
        if tmdb_id:
            by_tmdb_id[tmdb_id].append(entry)
        if imdb_id and imdb_id != "N/A" and imdb_id != "":
            by_imdb_id[imdb_id].append(entry)

tmdb_dups = {k: v for k, v in by_tmdb_id.items() if len(v) > 1}
imdb_dups = {k: v for k, v in by_imdb_id.items() if len(v) > 1}

print(f"Total index keys: {len(index)}")
print(f"Total movies: {sum(len(v) for v in index.values())}")
print()

if tmdb_dups:
    print(f"TMDB ID duplicates ({len(tmdb_dups)} movies):")
    for tmdb_id, occurrences in sorted(tmdb_dups.items(), key=lambda x: -len(x[1])):
        print(f"  TMDB {tmdb_id}:")
        for day_key, title, release_date in occurrences:
            print(f"    [{day_key}] {title} ({release_date})")
else:
    print("No TMDB ID duplicates found.")

print()

if imdb_dups:
    print(f"IMDb ID duplicates ({len(imdb_dups)} movies):")
    for imdb_id, occurrences in sorted(imdb_dups.items(), key=lambda x: -len(x[1])):
        print(f"  IMDb {imdb_id}:")
        for day_key, title, release_date in occurrences:
            print(f"    [{day_key}] {title} ({release_date})")
else:
    print("No IMDb ID duplicates found.")
