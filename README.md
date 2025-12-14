# Personal Website

A simple single-page personal website with automatic BibTeX to HTML conversion, deployed via GitHub Pages.

## Setup

1. **Configure GitHub Pages:**
   - Go to your repository Settings → Pages
   - Set Source to "GitHub Actions"

2. **Add your content:**
   - Edit `index.html` to customize your name and content
   - Add your publications to `data/publications.bib` in BibTeX format
   - Customize `styles.css` to match your preferred design

3. **Local testing:**

   ```bash
   # Install dependencies and run conversion
   uv run bibtex-to-html

   # Serve the site locally using the built-in server
   uv run serve

   # Or specify a custom port
   uv run serve --port 8080
   ```

4. **Setup pre-commit hooks (optional but recommended):**

   ```bash
   # Install dev dependencies including pre-commit
   uv sync --extra dev

   # Install pre-commit hooks
   uv run pre-commit install
   ```

## How It Works

1. When you push to the `main` branch, GitHub Actions automatically:
   - Installs Python dependencies using `uv`
   - Runs the BibTeX conversion script
   - Deploys the updated site to GitHub Pages

2. The Python script (`scripts/bibtex_to_html.py`):
   - Reads `data/publications.bib`
   - Parses BibTeX entries
   - Generates HTML for each publication
   - Injects the HTML into `index.html`

## File Structure

- `index.html` - Main HTML page
- `styles.css` - CSS styling
- `data/publications.bib` - BibTeX file with your publications
- `pyproject.toml` - Python project configuration
- `scripts/bibtex_to_html.py` - BibTeX to HTML conversion script
- `scripts/serve.py` - Local HTTP server script
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `.github/workflows/deploy.yml` - GitHub Actions workflow

## Implementation Details

- `index.html`: Single-page HTML structure with header, main content sections (About, Interests, Education, Publications), and footer. Contains a profile-container div wrapping profile image and profile info for responsive layout. Contains a container div wrapping Interests and Education sections for side-by-side layout. Contains a placeholder div for publications injection.
- `styles.css`: Modern, responsive CSS with clean typography, card-based publication styling, and mobile-friendly layout. Uses flexbox for side-by-side profile layout (image left, info right) on desktop (min-width: 900px), stacks vertically on mobile. Uses flexbox for side-by-side Interests/Education layout starting at 600px with responsive gap that gradually reduces as page narrows (using clamp with minimum 3px), switches to vertical stacking below 600px when sections would overlap. All sections remain centered on page with smooth responsive padding and max-width transitions (using clamp and min/calc functions) - sections smoothly reduce width and padding as page narrows, only adjusting when content needs narrower styling. Publication citations are displayed as single formatted text blocks in APA style.
- `data/publications.bib`: BibTeX file containing publication entries in standard BibTeX format.
- `pyproject.toml`: Python project configuration using uv for dependency management, defines bibtex-to-html and serve script entry points, includes pybtex and pybtex-apa7-style dependencies for APA citation formatting, includes pre-commit as optional dev dependency, requires Python >=3.9.
- `.pre-commit-config.yaml`: Pre-commit hooks configuration with ruff for Python linting and formatting, and pre-commit-hooks for common checks (private key detection, AST validation, file formatting, merge conflict detection).
- `scripts/bibtex_to_html.py`: Parses BibTeX file using pybtex, formats entries in APA 7th edition citation style, generates HTML with formatted citations, injects formatted HTML into index.html publications section, handles errors gracefully.
- `scripts/serve.py`: Local HTTP server script that calls `python -m http.server`, changes to project root directory before serving, supports custom port via command-line argument (default: 8000).
- `.github/workflows/deploy.yml`: GitHub Actions workflow that triggers on push to main, installs uv and dependencies, runs BibTeX conversion, deploys to GitHub Pages.
