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

def test_correction_tool_append_and_edit(monkeypatch, tmp_path):
    """
    Test that append_correction writes to updates.jsonl and edit_movie_fields suggests release_year update.
    """
    import movie_db.correction_tool as ct
    # Patch CORRECTIONS_PATH to a temp file
    updates_file = tmp_path / "updates.jsonl"
    monkeypatch.setattr(ct, "CORRECTIONS_PATH", str(updates_file))
    # Simulate an update
    imdb_id = "tt9999999"
    updates = {"release_date": "2025-06-19", "title": "Test Movie"}
    movie = {"imdb_id": imdb_id, "title": "Test Movie", "release_date": "2025-06-19"}
    ct.append_correction(imdb_id, updates, movie)
    # Check file written
    with open(updates_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert any(imdb_id in line for line in lines)

    # Test edit_movie_fields release_year suggestion
    # Simulate user changing release_date and accepting release_year update
    inputs = iter(["2", "2026-01-01", "y", "q"])  # Select field 2 (release_date)
    test_movie = {"title": "Test Movie", "release_date": "2025-01-01", "release_year": "2025", "imdb_id": "tt9999999"}
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    updates = ct.edit_movie_fields(dict(test_movie))
    assert updates["release_date"] == "2026-01-01"
    assert updates["release_year"] == "2026"


def test_correction_tool_quit(monkeypatch):
    """
    Test that pick_movie returns None on blank or 'q' input.
    """
    import movie_db.correction_tool as ct
    # Simulate blank input
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert ct.pick_movie([{"title": "A", "imdb_id": "tt1"}]) is None
    # Simulate 'q' input
    monkeypatch.setattr("builtins.input", lambda _: "q")
    assert ct.pick_movie([{"title": "A", "imdb_id": "tt1"}]) is None