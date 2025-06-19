# MoviesThisDay Release Notes

## v0.1.6 (2025-06-19)
- Version bump and maintenance updates.
- (Add new changes here)

## v0.1.5 (2025-06-19)
- Added `/corrections` POST route for submitting movie corrections (configurable file, robust error handling, Docker/env support).
- Added `/movie/{imdb_id}` route for JSON details of a movie by IMDb ID.
- New interactive `correction_tool.py` for searching, selecting, and updating movie fields (with color, field selection, and release_year suggestion).
- `build_db.py` applies updates from `updates.jsonl` before exporting the movie index, including moving movies if `release_date` changes.
- Improved documentation and docstrings across all scripts and endpoints.
- Updated README to document new routes, correction workflow, and Docker usage.
- General UI/UX improvements and code cleanup.
- Date picker now auto-navigates when a date is picked from the calendar, but not when manually edited (manual edits require pressing Go or Enter).

## v0.1.4 (2025-06-18)
- Added `/details/{imdb_id}` route and details page: full movie info, poster, ratings, and correction form.
- Correction form now posts to a configurable file via the `CORRECTIONS_FILE` environment variable (default: `/data/corrections.jsonl`).
- Docker and `run.sh` updated to mount a persistent `data` directory and set `CORRECTIONS_FILE` for containerized deployments.
- Correction file writability is checked at startup; if not writable, the correction endpoint returns an error.
- Correction endpoint now returns a generic error message for all invalid or failed submissions.
- IMDB link is now part of the IMDB ID in details view (not in the header).
- If available, OMDb poster is shown as a thumbnail to the right of the details card.
- Details page fields de-duplicated and improved for clarity and compactness.
- README updated to document `/details/{imdb_id}` and new Docker/environment variable setup.

## v0.1.3 (2025-06-17)
- Added GitHub Actions workflow for automated testing on push/PR.
- Added build status badge to README.
- Improved pytest coverage with additional edge case and error tests.
- Updated About and README to document Swagger UI at `/docs`.
- Refactored `/about` route and About page for static content and maintainability.
- Improved code style, docstrings, and exception handling in `app.py`.
- Enhanced stats output formatting and markdown in `movie_db/STATS.md`.
- General code cleanup and linter fixes.
- Improved mobile/tablet usability for the main and search results tables: both are now always horizontally scrollable with all columns visible, no columns hidden.
- Fixed Jinja2 template errors and restored IMDB link in main table.
- Created and populated `RELEASE.md` with release notes for all versions.

## v0.1.2 (2025-06-15)
- Major refactor for clarity and maintainability.
- About page made static except for version/year.
- `/about` route cleaned up to only pass minimal context.
- Expanded docstrings for all route handlers and key functions.
- Removed unused imports and code from `app.py`.
- Converted ASCII stats to markdown tables in `STATS.md`.
- Improved histogram formatting in `stats.py`.
- All navigation and API examples in About are now static.
- FastAPI app and templates are consistent with new About page.

## v0.1.1 (2025-06-10)
- Added advanced search page (`/search`) with sidebar form and paginated results.
- Improved error handling and validation for all endpoints.
- Added project metadata and stats to About page.
- Improved UI theming and navigation.
- Added Dockerfile and run.sh for easy deployment.

## v0.1.0 (2025-06-01)
- Initial public release.
- FastAPI backend with endpoints for movies by day, title, year, genre, studio, and advanced lookup.
- Modern Bootstrap web UI for browsing and searching movies.
- Auto-download of movie database on first run.
- About page with project info and API examples.
- Basic test coverage for all endpoints and data integrity.
