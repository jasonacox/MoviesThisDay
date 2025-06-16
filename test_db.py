import pickle
import os
import pytest
from datetime import datetime

# Path to the movies_by_day.pkl file
PKL_PATH = os.path.join(os.path.dirname(__file__), 'movie_db', 'movies_by_day.pkl')

def load_db():
    with open(PKL_PATH, 'rb') as f:
        db = pickle.load(f)
    return db.get('metadata', {}), db.get('index', {})

def test_metadata_keys():
    metadata, _ = load_db()
    assert isinstance(metadata, dict)
    # Accept either 'total_movies' or 'count_popularity_over_10' as valid keys
    assert 'avg_popularity_over_10' in metadata
    assert 'count_popularity_over_10' in metadata
    assert 'generated_at' in metadata
    assert 'max_popularity' in metadata

def test_index_structure():
    _, index = load_db()
    assert isinstance(index, dict)
    # Check MM_DD keys
    for key in index.keys():
        assert len(key) == 5 and key[2] == '_', f"Key format error: {key}"
        month, day = key.split('_')
        assert 1 <= int(month) <= 12
        assert 1 <= int(day) <= 31

def test_movies_entry():
    _, index = load_db()
    # Pick a known date (e.g., June 15)
    movies = index.get('06_15', [])
    assert isinstance(movies, list)
    if movies:
        movie = movies[0]
        assert 'title' in movie
        assert 'release_date' in movie
        assert 'popularity' in movie
        assert 'imdb_id' in movie
        assert 'release_year' in movie
        assert 'omdb_genre' in movie
        assert 'production_companies' in movie