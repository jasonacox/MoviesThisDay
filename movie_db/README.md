# Movies Database

This folder contains scripts to build an optimized movie database organized by release date (MM-DD).

## Create

1. To create this database, you must first download the [TMDB](https://developer.themoviedb.org/docs/getting-started) raw database from https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies?resource=download

2. The build script uses the OMDB API to gather additional details for the movie, including the release date (TMDB has invalid release dates). This requires that you set up a `OMDB_API_KEY` key in the .env file (see https://www.omdbapi.com/ to sign up for a key). 

Note: The build script will only query for movies that meet criteria defined by globals: non-adult content, popularity > 10, English language, and runtime > 20 minutes. Queries to OMDB will be cached in omdb_raw.jsonl to reduce API calls for future runs, or in case of failure.

3. Run the `build_db.py` to process movies and index them by date. It will create a JSON and PKL file for use by the web service (movies_by_day.pkl).

```bash
python build_db.py
```

## Test

Verify the conversion was successful by running the `test.py`.

```bash
python test_db.py
```

