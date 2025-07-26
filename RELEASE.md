# MoviesThisDay Release Notes

## v0.1.12 (2025-07-26)
- SEO: Added meta tags (description, keywords, Open Graph, Twitter Card) and JSON-LD structured data to homepage for improved search engine discoverability and rich previews.
- Static assets: Added `static/` directory and now serve static files (including `og-image.png`) via FastAPI and Docker.
- Docker: Dockerfile now copies the `static/` directory for static asset support in containers.
- Favicon: Improved `gen_favicon.py` to write PNG output, prompt before overwrite, and document usage; favicon is now generated from `static/icon.png` and saved as `static/favicon.png`.
- Accessibility: Improved all main templates (`index.html`, `details.html`, `search.html`) so that movie poster images use descriptive alt text and, if the poster fails to load, a local placeholder image is shown and the alt text updates to "No poster available" for accessibility and a better user experience.
- Version bump to 0.1.12 in `app.py` and documentation.
- General: Updated documentation, release notes, and ensured all new features and fixes are reflected in the codebase.

## v0.1.11 (2025-07-26)
- Database build: TMDB new releases (discover API) are now loaded page by page, but the process stops as soon as a movie's popularity drops below the configured threshold. This optimizes API usage and ensures only popular new releases are included.
- Improved build output: Phase headers now print with clear dividers, and all status messages are consistently formatted for readability.
- Trending and new release movies are always included in the main index, regardless of release date.
- Homepage date navigation: Improved date handling and navigation logic for the date picker and navigation buttons. The calendar now always uses the user's local date, and navigation between days/months is robust to month/year overflow. The client_date parameter is always set and updated automatically for timezone consistency.
- Documentation updated to reflect new build logic, API optimizations, and UI date handling.
- Minor code cleanup and maintainability improvements.

## v0.1.10 (2025-06-26)
- Details page: Improved mobile/iPhone layout—poster image now appears directly below the movie title on small screens for better UX.
- Removed `/corrections` endpoint and all related backend and test code for simplicity and security.
- `/health` endpoint: Fixed memory usage reporting to be accurate on both macOS and Linux.
- General code cleanup, improved maintainability, and updated documentation.

## v0.1.9 (2025-06-22)
- About page: Added Chart.js line graph for movies by year, with trend-based forecasting for both the prior year and current year.
- Forecast logic: Both last year and current year are now forecasted using the previous 5 years (excluding the year being forecasted), and plotted as red points on the graph.
- Improved About page chart legend and forecast point styles for clarity.
- Minor About page JavaScript and UI/UX improvements for maintainability and accuracy.
- Added Movie Ratings (e.g. G, PG, PG-13) display and controls to homepage and search.
- Major maintainability and documentation improvements: Added detailed docstrings and inline comments to all /stats endpoints and key backend logic.
- Implemented in-memory caching for /stats endpoints (movies_by_day, total_movies, movies_by_rating) for improved performance.
- Enhanced movie rating normalization and filtering logic for statistics and search endpoints, including robust mapping and ordering of ratings.
- About page: Added two modern Chart.js bar graphs (movies by day, movies by rating) with improved color, gradient, and month labeling. Displayed total and popular movie counts above the graphs.
- UI/UX: Improved About and Search pages for compactness, clarity, and mobile usability. Search results now show rating under release date, and filter logic is more advanced.
- Minor bugfixes, code cleanup, and improved logging for startup and shutdown events.
- All changes made using best practices for code clarity, maintainability, and documentation.

## v0.1.8 (2025-06-21)
- PKL data file download source updated to S3 for improved reliability and speed.
- Added robust error handling: app now exits with a clear error if PKL download, extraction, or loading fails.
- Improved Docker build/upload workflow: PKL is zipped before build, and uploaded to S3 automatically.
- README updated with new S3 download location for PKL zip file and manual download instructions.
- Added S3 upload step to `upload.sh` and improved verification of PKL/ZIP creation.
- Added `/favicon.ico` route to serve a custom blue-gradient favicon as a base64-encoded PNG, matching the project theme.
- Moved all non-standard library imports (e.g., base64) to the top of `app.py` for best practices and maintainability.
- Confirmed all required third-party packages are present in `requirements.txt`; no changes needed.
- Minor code cleanup and import organization in `app.py`.
- Minor documentation and maintainability improvements.
- Search UI improvements: Movie titles in search results are now clickable links to detail pages, and each result row features a modern hover card with full movie details and a "New Release" badge if applicable. This matches the main table's UX and improves discoverability and consistency.

## v0.1.7 (2025-06-20)
- Trending/new release movies are now always included in the main index table, regardless of release date.
- Added server-side detection of "New Release" (released within last 3 months) for all movies; badge appears in both the main table and hover card.
- Removed all client-side JavaScript for new release detection; logic is now robust and timezone-consistent.
- Improved maintainability by centralizing new release logic in the backend.
- Minor UI/UX improvements and bugfixes.

## v0.1.6 (2025-06-19)
- Date picker calendar now allows selecting any date, including future dates (no max restriction).
- Date input: If a date is picked from the calendar, navigation is automatic; if manually edited, user must press Go or Enter.
- Removed browser tooltip from movie title links (no more native title popover on hover).
- Fixed Docker run.sh to use $(pwd) instead of $(PWD) for compatibility.
- Added `python-multipart` to requirements.txt for FastAPI Form support.
- General UI/UX polish and bugfixes.

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
