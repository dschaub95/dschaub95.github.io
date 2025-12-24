#!/usr/bin/env python3
"""
Convert BibTeX file to HTML and inject into index.html
"""

import re
import sys
from pathlib import Path
from pybtex.database import parse_file
from pybtex.plugin import find_plugin
from pybtex.richtext import Text


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
    import html

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

    # Replace placeholders with HTML tags
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


def parse_bibtex(bibtex_path):
    """Parse BibTeX file and return formatted HTML in APA style"""
    try:
        # Apply monkey patch to fix bug in pybtex-apa7-style
        _patch_apa7_style()

        # Parse BibTeX file using pybtex
        bib_data = parse_file(str(bibtex_path), bib_format="bibtex")

        if not bib_data.entries:
            return "<p>No publications found.</p>"

        # Load APA style formatter (APA 7th edition)
        style = find_plugin("pybtex.style.formatting", "apa7")()
        # Use plain text backend
        backend = find_plugin("pybtex.backends", "plaintext")()

        # Sort entries by year and month (descending) - newest first
        def get_sort_key(entry_item):
            """Get sort key for an entry: (year, month_number)"""
            entry = entry_item[1]
            year_str = entry.fields.get("year", "0")

            # Extract year as integer
            try:
                year = int(year_str) if year_str.isdigit() else 0
            except (ValueError, AttributeError):
                year = 0

            # Extract month and convert to number for sorting
            month_field = entry.fields.get("month", "")
            # Handle different month formats (string, number, etc.)
            if month_field:
                month_str = str(month_field).lower().strip()
            else:
                month_str = ""

            month_map = {
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

            # Try to parse month
            month = 0  # Default to 0 (no month) - will sort after entries with months
            if month_str:
                # Check if it's a month name or number string
                if month_str in month_map:
                    month = month_map[month_str]
                else:
                    # Try to parse as integer
                    try:
                        month_int = int(month_str)
                        if 1 <= month_int <= 12:
                            month = month_int
                    except (ValueError, AttributeError):
                        month = 0

            # Return tuple: (year, month) for sorting
            # Higher year/month values = newer, so reverse=True gives newest first
            return (year, month)

        sorted_entries = sorted(
            bib_data.entries.items(),
            key=get_sort_key,
            reverse=True,  # True to get newest first
        )

        # Create bibliography with entries in sorted order for context
        # Python 3.7+ dicts maintain insertion order
        from pybtex.database import BibliographyData

        sorted_bib_data = BibliographyData(
            {key: entry for key, entry in sorted_entries}
        )

        # Format entries individually in sorted order to ensure correct ordering
        html_parts = []
        for key, entry in sorted_entries:
            # Format individual entry with bibliography context
            formatted_entry = style.format_entry(key, entry, bib_data=sorted_bib_data)

            # Render as plain text
            citation_text = formatted_entry.text.render(backend)
            # Convert to string
            citation_str = str(citation_text)

            # Check if entry has a DOI that's not in the formatted citation
            doi_field = entry.fields.get("doi", "")
            if doi_field and "doi:" not in citation_str.lower():
                # Append DOI to citation if it exists in entry but not in formatted text
                citation_str += f" doi:{doi_field}"

            # Post-process to add clickable DOI links and bold author name
            citation_html = _process_citation_html(citation_str)

            html_parts.append(f"""                <div class="publication">
                    <div class="publication-citation">{citation_html}</div>
                </div>
""")

        return "\n".join(html_parts)

    except Exception as e:
        print(f"Error parsing BibTeX: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return f"<p>Error loading publications: {e}</p>"


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

    # Parse BibTeX and generate HTML
    publications_html = parse_bibtex(bibtex_path)

    # Inject into index.html
    inject_html(html_path, publications_html)


if __name__ == "__main__":
    main()
