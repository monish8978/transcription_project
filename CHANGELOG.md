# Changelog

All notable changes to the **Transcription Project** will be documented in this file.

## [Unreleased] - 2026-06-27

### Added
- **Security**: Added `API_KEY` environment variable in the `.env` file for secure authentication.
- **Security**: Implemented strict File Type Validation to only accept `.wav` and `.mp3` files.
- **Security**: Implemented a maximum File Size Limit of 100MB, processed in 1MB chunks to prevent memory overload (DoS protection).
- **Security**: Added API Rate Limiting using `slowapi`:
  - `POST /api/v1/transcribe` limited to **10 requests per minute**.
  - `GET /api/v1/status/{task_id}` limited to **30 requests per minute**.
- **Documentation**: Generated and added `API_Documentation.md` and `API_Documentation.pdf` detailing endpoints, parameters, limits, and error codes.
- **Documentation**: Added comprehensive comments to all variables within the `.env` file for better maintainability.

### Changed
- **Dependencies**: Added `slowapi` to `requirements.txt`.
- **Security (CORS)**: Restricted CORS `allow_origins` policy in `app/main.py` from `["*"]` to safe domains like `["http://your-domain.com", "http://localhost"]`.
- **Documentation (README.md)**: Updated API submission documentation to include three practical `cURL` examples (`file_url`, `file_path`, and `file upload`), with empty placeholder values for `X-API-Key`.
