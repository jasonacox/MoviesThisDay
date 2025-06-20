# Movies Database

This folder contains scripts to build an optimized movie database organized by release date (MM-DD).

## Trending & New Release Movies

- The database build process now ensures that trending and newly released movies (from TMDB trending API) are always included in the main index, regardless of release date.
- All correction and update logic (from `updates.jsonl`) is applied before export, so new/corrected movies are always visible after a rebuild.

## Create

1. To create this database, you must first download the [TMDB](https://developer.themoviedb.org/docs/getting-started) raw database from https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies?resource=download

2. The build script uses the OMDB API to gather additional details for the movie, including the release date (TMDB has invalid release dates). This requires that you set up a `OMDB_API_KEY` key in the .env file (see https://www.omdbapi.com/ to sign up for a key). 

Note: The build script will only query for movies that meet criteria defined by globals: non-adult content, popularity > 10, English language, and runtime > 20 minutes. Queries to OMDB will be cached in omdb_raw.jsonl to reduce API calls for future runs, or in case of failure.

3. Run the `build_db.py` script to process movies and index them by date. It will create a JSON and PKL file for use by the web service (`movies_by_day.pkl`).

```bash
python build_db.py
```

## Corrections & Updates

To submit corrections or updates to movie data (such as fixing release dates, titles, or other fields), use the interactive correction tool:

```bash
python correction_tool.py
```

- Search for a movie by title or IMDB ID.
- Select the movie from a colorized, sorted list.
- Edit the fields that need to be changed.
- If you change the `release_date` year, the tool will suggest updating `release_year` for consistency.
- All updates are appended to `updates.jsonl` (one JSON object per line).
- These updates are automatically applied during the next database build (make sure you run `build_db.py` to rebuild with correction).

> **Note:** The correction tool requires the `colorama` package for cross-platform color support. Install it with:
> ```bash
> pip install colorama
> ```

## Test

Verify the conversion was successful by running the `test_db.py`.

```bash
python test_db.py
```

