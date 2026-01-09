#!/usr/bin/env python3
"""
Convert BibTeX file to HTML and inject into index.html
"""

import argparse
import html
import re
import sys
from pathlib import Path
from pybtex.database import parse_file
from pybtex.plugin import find_plugin
from pybtex.richtext import Text

# Month name to number mapping for sorting
_MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "1": 1,
    "feb": 2,
    "february": 2,
    "2": 2,
    "mar": 3,
    "march": 3,
    "3": 3,
    "apr": 4,
    "april": 4,
    "4": 4,
    "may": 5,
    "5": 5,
    "jun": 6,
    "june": 6,
    "6": 6,
    "jul": 7,
    "july": 7,
    "7": 7,
    "aug": 8,
    "august": 8,
    "8": 8,
    "sep": 9,
    "september": 9,
    "9": 9,
    "oct": 10,
    "october": 10,
    "10": 10,
    "nov": 11,
    "november": 11,
    "11": 11,
    "dec": 12,
    "december": 12,
    "12": 12,
}


def _process_citation_html(citation_text):
    """
    Post-process citation text to:
    1. Remove month from date (APA style shows only year for journal articles)
    2. Make title bold
    3. Make DOI links clickable
    4. Make author name (Schaub, D. P. or Schaub, D.) bold

    Args:
        citation_text: Plain text citation string

    Returns:
        HTML string with clickable DOIs and bold author name
    """
    citation_str = str(citation_text)

    # Remove month from date - APA style shows only year for journal articles
    # Pattern: (YYYY , Month) -> (YYYY)
    # Handle various month formats and spacing
    date_pattern = r"\((\d{4})\s*,\s*[A-Za-z]+\s*\)"
    citation_str = re.sub(date_pattern, r"(\1)", citation_str)

    # Make title bold - title comes after (Year). and ends before journal name or end
    # Pattern: (Year). Title. [Journal or end]
    # The title is everything after "(Year). " until ". " followed by journal or end
    # Journal names typically start with a capital letter after ". "

    # Use a single pattern that matches title ending with period, followed by either:
    # 1. Space + capital letter (journal name starts)
    # 2. End of string or non-capital content (no journal)
    # Use non-greedy match to get the shortest title (up to first period before journal/end)
    title_pattern = (
        r"(\((\d{4})\)\.\s+)(.+?\.)(?=\s+[A-Z][a-zA-Z\s&,]+(?:,|\.)|\s*[^A-Z]|$)"
    )

    def bold_title(match):
        year_part = match.group(1)  # "(2025). "
        title = match.group(3)  # The title text (ends with period)
        return f"{year_part}__TITLE_START__{title}__TITLE_END__"

    citation_str = re.sub(title_pattern, bold_title, citation_str)

    doi_replacements = []  # Store DOI replacements

    # Process DOIs FIRST (before HTML escaping) for more reliable matching
    # Pattern: doi:10.xxxxx (DOI format)
    # DOI format: 10.xxxx/xxxx where xxxx can contain letters, numbers, dots, slashes, hyphens
    # Match until whitespace or end of string
    doi_pattern = r'doi:([0-9]+\.[0-9]+/[^\s<>"\'&]+)'

    def replace_doi_placeholder(match):
        doi_value = match.group(1)
        placeholder = f"__DOI_PLACEHOLDER_{len(doi_replacements)}__"
        doi_replacements.append(doi_value)
        return placeholder

    citation_str = re.sub(doi_pattern, replace_doi_placeholder, citation_str)

    # Process author names (before HTML escaping) to avoid regex complexity
    # Match longer pattern first: "Schaub, D. P." (with flexible spacing)
    citation_str = re.sub(
        r"(Schaub, D\.\s*P\.)",
        r"__SCH_AUB_D_P__",  # Temporary placeholder
        citation_str,
    )
    # Then match shorter pattern: "Schaub, D." (only remaining instances, not followed by P.)
    citation_str = re.sub(
        r"(Schaub, D\.)(?!\s*P\.)",
        r"__SCH_AUB_D__",  # Temporary placeholder
        citation_str,
    )

    # Now escape HTML
    citation_html = html.escape(citation_str)

    # Replace placeholders with HTML tags (using helper function)
    citation_html = citation_html.replace(
        "__SCH_AUB_D_P__", "<strong>Schaub, D. P.</strong>"
    )
    citation_html = citation_html.replace(
        "__SCH_AUB_D__", "<strong>Schaub, D.</strong>"
    )

    # Replace title placeholders with bold tags
    citation_html = re.sub(
        r"__TITLE_START__([^_]+)__TITLE_END__", r"<strong>\1</strong>", citation_html
    )

    # Replace DOI placeholders with actual links
    for i, doi_value in enumerate(doi_replacements):
        placeholder = f"__DOI_PLACEHOLDER_{i}__"
        doi_url = f"https://doi.org/{doi_value}"
        link_html = f'<a href="{html.escape(doi_url)}" target="_blank" rel="noopener noreferrer">doi:{html.escape(doi_value)}</a>'
        citation_html = citation_html.replace(html.escape(placeholder), link_html)

    return citation_html


def _patch_apa7_style():
    """Monkey patch to fix bug in pybtex-apa7-style where richtext.Text is used instead of Text"""
    try:
        import formatting.apa as apa_module
        from pybtex.style.template import join, FieldIsMissing, node

        # Create patched version that maintains the @node decorator behavior
        @node
        def patched_apa_names(children, context, role, **kwargs):
            """Patched version that uses Text instead of richtext.Text"""
            assert not children

            try:
                persons = context["entry"].persons[role]
            except KeyError:
                raise FieldIsMissing(role, context["entry"])

            style = context["style"]

            if len(persons) > 20:
                formatted_names = [
                    style.format_name(person, style.abbreviate_names)
                    for person in persons[:20]
                ]
                # Fix: use Text instead of richtext.Text
                formatted_names += [Text("et al.")]
                return join(sep=", ")[formatted_names].format_data(context)
            else:
                formatted_names = [
                    style.format_name(person, style.abbreviate_names)
                    for person in persons
                ]
                return join(sep=", ", sep2=" & ", last_sep=", & ")[
                    formatted_names
                ].format_data(context)

        # Apply the patch
        apa_module.apa_names = patched_apa_names
    except (ImportError, AttributeError):
        # If the module structure is different, the patch will be skipped
        # and we'll rely on error handling in parse_bibtex
        pass


def _bold_author_name(text):
    """Make author name (Schaub, D. P. or Schaub, D.) bold in text"""
    text = re.sub(r"(Schaub, D\.\s*P\.)", r"<strong>Schaub, D. P.</strong>", text)
    return re.sub(r"(Schaub, D\.)(?!\s*P\.)", r"<strong>Schaub, D.</strong>", text)


def _format_authors(entry, style, backend, bib_data):
    """Format authors from BibTeX entry"""
    try:
        from pybtex.style.template import join

        persons = entry.persons.get("author", [])
        if not persons:
            return ""

        # Format names using the style's formatting
        formatted_names = [
            style.format_name(person, style.abbreviate_names) for person in persons
        ]

        # Join names with commas using the style's join template
        authors_node = join(sep=", ", sep2=" & ", last_sep=", & ")[formatted_names]

        # Create context dictionary for formatting
        context = {
            "entry": entry,
            "style": style,
            "bib_data": bib_data,
        }

        # Format and render to string, then make author name bold
        authors_str = str(authors_node.format_data(context).render(backend))
        return _bold_author_name(authors_str)
    except Exception:
        return ""


def _clean_title(title):
    """Remove BibTeX curly braces from title"""
    # Double braces {{}} are used to preserve literal braces in BibTeX
    title_clean = re.sub(r"\{\{([^}]+)\}\}", r"\1", title)  # Remove double braces
    return re.sub(r"\{([^}]+)\}", r"\1", title_clean)  # Remove single braces


def _get_journal(entry):
    """Extract journal name with fallback to publisher or archiveprefix"""
    return (
        entry.fields.get("journal", "").strip()
        or entry.fields.get("publisher", "").strip()
        or entry.fields.get("archiveprefix", "").strip()
    )


def _format_journal_display(journal, year):
    """Format journal display with optional year"""
    if not journal:
        return ""
    return f"{journal} ({year})" if year else journal


def _get_link_info(entry):
    """Get link URL and text from entry (DOI preferred over URL)"""
    doi = entry.fields.get("doi", "").strip()
    if doi:
        return f"https://doi.org/{doi}", "Read Paper"

    url = entry.fields.get("url", "").strip()
    if url:
        return url, "Read Paper"

    return "", ""


def _parse_year(year_str):
    """Parse year string to integer, returns 0 if invalid"""
    try:
        return int(year_str) if year_str and year_str.isdigit() else 0
    except (ValueError, AttributeError):
        return 0


def _parse_month(month_field):
    """Parse month field to integer (1-12), returns 0 if invalid"""
    if not month_field:
        return 0

    month_str = str(month_field).lower().strip()
    if month_str in _MONTH_MAP:
        return _MONTH_MAP[month_str]

    try:
        month_int = int(month_str)
        return month_int if 1 <= month_int <= 12 else 0
    except (ValueError, AttributeError):
        return 0


def _get_sort_key(entry_item):
    """Get sort key for an entry: (year, month_number)"""
    entry = entry_item[1]
    year = _parse_year(entry.fields.get("year", "0"))
    month = _parse_month(entry.fields.get("month", ""))
    return (year, month)


def _parse_and_sort_bibtex(bibtex_path):
    """Parse BibTeX file and return sorted entries with style/backend setup"""
    _patch_apa7_style()

    bib_data = parse_file(str(bibtex_path), bib_format="bibtex")
    if not bib_data.entries:
        return None, None, None, None

    style = find_plugin("pybtex.style.formatting", "apa7")()
    backend = find_plugin("pybtex.backends", "plaintext")()

    sorted_entries = sorted(
        bib_data.entries.items(),
        key=_get_sort_key,
        reverse=True,
    )

    from pybtex.database import BibliographyData

    sorted_bib_data = BibliographyData({key: entry for key, entry in sorted_entries})

    return sorted_entries, style, backend, sorted_bib_data


def parse_bibtex_card_mode(bibtex_path):
    """Parse BibTeX file and return formatted HTML in card mode with visual prioritization"""
    try:
        sorted_entries, style, backend, sorted_bib_data = _parse_and_sort_bibtex(
            bibtex_path
        )
        if sorted_entries is None:
            return "<p>No publications found.</p>"

        html_parts = []
        for key, entry in sorted_entries:
            title = _clean_title(entry.fields.get("title", "").strip())
            journal = _get_journal(entry)
            year = entry.fields.get("year", "").strip()
            link_url, link_text = _get_link_info(entry)
            authors = _format_authors(entry, style, backend, sorted_bib_data)

            # Build HTML structure
            parts = ['                <div class="publication-card">']

            journal_display = _format_journal_display(journal, year)
            if journal_display:
                parts.append(
                    f'                    <div class="publication-journal">{html.escape(journal_display)}</div>'
                )

            parts.extend(
                [
                    f'                    <div class="publication-title">{html.escape(title)}</div>',
                    f'                    <div class="publication-authors">{authors}</div>',
                ]
            )

            if link_url:
                parts.append(
                    f'                    <a href="{html.escape(link_url)}" target="_blank" rel="noopener noreferrer" class="publication-link">{html.escape(link_text)}<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-external-link ml-0.5 inline-block h-4 w-4" aria-hidden="true"><path d="M15 3h6v6"></path><path d="M10 14 21 3"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path></svg></a>'
                )

            parts.append("                </div>")
            html_parts.append("\n".join(parts))

        return "\n".join(html_parts)

    except Exception as e:
        return _handle_parse_error(e)


def _handle_parse_error(e):
    """Handle parsing errors consistently"""
    print(f"Error parsing BibTeX: {e}", file=sys.stderr)
    import traceback

    traceback.print_exc()
    return f"<p>Error loading publications: {e}</p>"


def parse_bibtex(bibtex_path):
    """Parse BibTeX file and return formatted HTML in APA style"""
    try:
        sorted_entries, style, backend, sorted_bib_data = _parse_and_sort_bibtex(
            bibtex_path
        )
        if sorted_entries is None:
            return "<p>No publications found.</p>"

        html_parts = []
        for key, entry in sorted_entries:
            # Format individual entry with bibliography context
            formatted_entry = style.format_entry(key, entry, bib_data=sorted_bib_data)
            citation_str = str(formatted_entry.text.render(backend))

            # Check if entry has a DOI that's not in the formatted citation
            doi_field = entry.fields.get("doi", "")
            if doi_field and "doi:" not in citation_str.lower():
                citation_str += f" doi:{doi_field}"

            # Post-process to add clickable DOI links and bold author name
            citation_html = _process_citation_html(citation_str)

            html_parts.append(f"""                <div class="publication">
                    <div class="publication-citation">{citation_html}</div>
                </div>
""")

        return "\n".join(html_parts)

    except Exception as e:
        return _handle_parse_error(e)


def inject_html(html_path, publications_html):
    """Inject publications HTML into index.html"""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the publications section and replace content between <h2> and </section>
        pattern = (
            r'(<section id="publications">\s*<h2>Publications</h2>)(.*?)(</section>)'
        )

        replacement = f"\\1\n{publications_html}            \\3"

        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"Successfully injected publications into {html_path}")

    except Exception as e:
        print(f"Error injecting HTML: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Convert BibTeX to HTML")
    parser.add_argument(
        "--mode",
        choices=["citation", "card"],
        default="card",
        help="Output mode: 'citation' for APA citation style (default), 'card' for card-based layout",
    )
    args = parser.parse_args()

    # Get paths relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    bibtex_path = project_root / "data" / "publications.bib"
    html_path = project_root / "index.html"

    if not bibtex_path.exists():
        print(f"Error: BibTeX file not found at {bibtex_path}", file=sys.stderr)
        sys.exit(1)

    if not html_path.exists():
        print(f"Error: HTML file not found at {html_path}", file=sys.stderr)
        sys.exit(1)

    # Parse BibTeX and generate HTML based on mode
    if args.mode == "card":
        publications_html = parse_bibtex_card_mode(bibtex_path)
    else:
        publications_html = parse_bibtex(bibtex_path)

    # Inject into index.html
    inject_html(html_path, publications_html)


if __name__ == "__main__":
    main()
