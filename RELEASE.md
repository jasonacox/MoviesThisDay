# MoviesThisDay Release Notes

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
