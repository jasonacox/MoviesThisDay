import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_index():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "MoviesThisDay" in resp.text

def test_movies_today():
    response = client.get('/movies/today')
    # Accept 200 (success) or 500 (TMDb error/no API key)
    assert response.status_code in [200, 500]
    data = response.json()
    if response.status_code == 200:
        assert 'movies' in data
        assert isinstance(data['movies'], list)
    else:
        assert 'error' in data

def test_index_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "MoviesThisDay" in resp.text

def test_movies_today():
    resp = client.get("/movies/today")
    assert resp.status_code == 200
    data = resp.json()
    assert "movies" in data
    assert "metadata" in data

def test_search_page():
    resp = client.get("/search")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "MoviesThisDay" in resp.text

def test_about_page():
    resp = client.get("/about")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "MoviesThisDay" in resp.text

def test_movies_lookup_title():
    resp = client.get("/movies/lookup", params={"title": "matrix"})
    assert resp.status_code == 200
    assert "results" in resp.json()

def test_movies_lookup_studio():
    resp = client.get("/movies/lookup", params={"studio": "Warner"})
    assert resp.status_code == 200
    assert "results" in resp.json()

def test_movies_lookup_invalid():
    resp = client.get("/movies/lookup")
    assert resp.status_code == 400
    assert "detail" in resp.json()

def test_movies_lookup_invalid_regex():
    resp = client.get("/movies/lookup", params={"title": "["})
    assert resp.status_code == 400
    assert "detail" in resp.json() or "error" in resp.json()
    resp = client.get("/movies/lookup", params={"studio": "["})
    assert resp.status_code == 400
    assert "detail" in resp.json() or "error" in resp.json()
    resp = client.get("/movies/lookup", params={"genre": "["})
    assert resp.status_code == 400
    assert "detail" in resp.json() or "error" in resp.json()

def test_movies_lookup_invalid_runtime():
    resp = client.get("/movies/lookup", params={"runtime": "abc"})
    assert resp.status_code == 200  # Should not error, just return 0 results
    assert "results" in resp.json()

def test_movies_by_imdb():
    resp = client.get("/movies/by-imdb/tt0133093")
    assert resp.status_code in (200, 404)

def test_movies_by_title():
    resp = client.get("/movies/by-title", params={"title": "matrix"})
    assert resp.status_code == 200
    assert "results" in resp.json()

def test_movies_by_release_date():
    resp = client.get("/movies/by-release-date/1999-03-31")
    assert resp.status_code in (200, 400)  # 400 if date not found

def test_movies_by_year():
    resp = client.get("/movies/by-year/1999")
    assert resp.status_code == 200
    assert "results" in resp.json()

def test_movies_by_year_invalid():
    resp = client.get("/movies/by-year/abcd")
    assert resp.status_code == 400
    assert "detail" in resp.json()

def test_movies_by_genre():
    resp = client.get("/movies/by-genre", params={"genre": "Action"})
    assert resp.status_code == 200
    assert "results" in resp.json()

def test_movies_by_studio():
    resp = client.get("/movies/by-studio", params={"studio": "Warner"})
    assert resp.status_code == 200
    assert "results" in resp.json()

def test_movies_by_day():
    resp = client.get("/movies/by-day/06-15")
    assert resp.status_code == 200
    assert "results" in resp.json()

def test_movies_by_day_empty_result():
    resp = client.get("/movies/by-day/01-01")  # Unlikely to have no movies, but possible
    assert resp.status_code == 200
    assert "results" in resp.json()
    # Accept 0 or more results

def test_movies_by_day_invalid():
    resp = client.get("/movies/by-day/13-40")
    assert resp.status_code == 400
    assert "detail" in resp.json() or "error" in resp.json()

def test_movies_by_day_missing():
    resp = client.get("/movies/by-day")
    assert resp.status_code == 400
    assert "error" in resp.json()

def test_version_endpoint():
    resp = client.get("/version")
    assert resp.status_code == 200
    assert "version" in resp.json()

def test_docs_and_openapi():
    resp = client.get("/docs")
    assert resp.status_code == 200
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
