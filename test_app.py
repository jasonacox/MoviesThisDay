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

def test_details_page_found():
    # Try a known movie (The Matrix) if present, else skip
    resp = client.get("/details/tt0133093")
    if resp.status_code == 200:
        assert "text/html" in resp.headers["content-type"]
        assert "Matrix" in resp.text or "matrix" in resp.text
    else:
        assert resp.status_code == 404
        assert "Movie not found" in resp.text

def test_details_page_not_found():
    resp = client.get("/details/tt0000000")
    assert resp.status_code == 404
    assert "Movie not found" in resp.text

def test_corrections_endpoint_success(monkeypatch):
    # Patch CORRECTIONS_WRITABLE to True and file open to a dummy
    from app import CORRECTIONS_WRITABLE, CORRECTIONS_FILE
    if not CORRECTIONS_WRITABLE:
        pytest.skip("Corrections file not writable in this environment")
    data = {
        "imdb_id": "tt0133093",
        "correction": "Test correction",
        "user_agent": "pytest",
        "movie_title": "The Matrix"
    }
    resp = client.post("/corrections", data=data)
    assert resp.status_code == 200
    assert "Thank you" in resp.text

def test_corrections_endpoint_invalid(monkeypatch):
    # Too long correction
    from app import CORRECTIONS_WRITABLE
    if not CORRECTIONS_WRITABLE:
        pytest.skip("Corrections file not writable in this environment")
    data = {
        "imdb_id": "tt0133093",
        "correction": "x" * 2000,
        "user_agent": "pytest",
        "movie_title": "The Matrix"
    }
    resp = client.post("/corrections", data=data)
    assert resp.status_code == 413 or resp.status_code == 500
    assert "Oops" in resp.text

def test_corrections_endpoint_not_writable(monkeypatch):
    # Patch CORRECTIONS_WRITABLE to False
    import app
    monkeypatch.setattr(app, "CORRECTIONS_WRITABLE", False)
    data = {
        "imdb_id": "tt0133093",
        "correction": "Test correction",
        "user_agent": "pytest",
        "movie_title": "The Matrix"
    }
    resp = client.post("/corrections", data=data)
    assert resp.status_code == 500
    assert "Oops" in resp.text

def test_stats_movies_by_year():
    resp = client.get("/stats/movies_by_year")
    assert resp.status_code == 200
    data = resp.json()
    assert "year_counts" in data
    assert isinstance(data["year_counts"], dict)
    # Should have at least a few years
    assert len(data["year_counts"]) > 5

def test_stats_movies_by_day():
    resp = client.get("/stats/movies_by_day")
    assert resp.status_code == 200
    data = resp.json()
    assert "date_counts" in data
    assert isinstance(data["date_counts"], dict)
    assert len(data["date_counts"]) > 0

def test_stats_total_movies():
    resp = client.get("/stats/total_movies")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_movies" in data
    assert "popular_movies" in data
    assert isinstance(data["total_movies"], int)
    assert isinstance(data["popular_movies"], int)


def test_stats_movies_by_rating():
    resp = client.get("/stats/movies_by_rating")
    assert resp.status_code == 200
    data = resp.json()
    assert "rating_counts" in data
    assert isinstance(data["rating_counts"], dict)
    assert len(data["rating_counts"]) > 0


def test_robots_txt():
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.text.startswith("User-agent: ")
    assert "Disallow: /docs" in resp.text


def test_favicon():
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200
    assert resp.headers["content-type"] in ("image/x-icon", "image/vnd.microsoft.icon", "image/png")
    assert resp.content  # Should not be empty


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "database" in data


def test_ping():
    resp = client.get("/ping")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
