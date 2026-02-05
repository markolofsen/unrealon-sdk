"""
HTML cleaner for parser prepare scripts.

Cleans HTML and saves in multiple formats for analysis.

Usage:
    from unrealon.parsers.utils import clean_and_save, ALL_FORMATS

    clean_and_save(html, "listing", out_dir=Path("cleaned"))

Output formats:
    - html: cleaned DOM
    - md: markdown
    - aom.yaml: AOM accessibility tree
    - xtree.txt: XTree structure
"""
from __future__ import annotations

import logging
from pathlib import Path

from sdkrouter_tools.html import CleanerConfig, HTMLCleaner, OutputFormat

log = logging.getLogger(__name__)

ALL_FORMATS = {
    OutputFormat.HTML: "html",
    OutputFormat.MARKDOWN: "md",
    OutputFormat.AOM: "aom.yaml",
    OutputFormat.XTREE: "xtree.txt",
}


def clean_and_save(
    html: str,
    name: str,
    out_dir: Path,
    *,
    save_raw: bool = True,
    formats: dict | None = None,
    verbose: bool = True,
) -> None:
    """
    Clean HTML and save in multiple output formats.

    Args:
        html: Raw HTML string
        name: Base filename (without extension)
        out_dir: Output directory
        save_raw: Whether to save original HTML as {name}_raw.html
        formats: Dict of OutputFormat -> extension (default: ALL_FORMATS)
        verbose: Print progress to stdout

    Saves to out_dir/:
        {name}_raw.html  - original browser HTML (if save_raw=True)
        {name}.html      - cleaned DOM
        {name}.md        - markdown
        {name}.aom.yaml  - AOM tree
        {name}.xtree.txt - XTree
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    formats = formats or ALL_FORMATS

    # Save raw HTML
    if save_raw:
        raw_path = out_dir / f"{name}_raw.html"
        raw_path.write_text(html, encoding="utf-8")
        log.info("Saved raw HTML: %s (%d chars)", raw_path.name, len(html))

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"  {name.upper()}")
        print(f"{'=' * 60}")
        if save_raw:
            print(f"  Raw: {name}_raw.html ({len(html):,} chars)")

    # Run cleaner in each output format and save
    for fmt, ext in formats.items():
        config = CleanerConfig(output_format=fmt, filter_classes=True)
        cleaner = HTMLCleaner(config)
        result = cleaner.clean(html)

        out_path = out_dir / f"{name}.{ext}"
        out_path.write_text(result.output, encoding="utf-8")

        stats = result.stats
        if verbose:
            print(f"  {fmt.value:10s} → {out_path.name} ({len(result.output):,} chars, "
                  f"{stats.cleaned_tokens:,} tok, -{stats.reduction_percent:.0f}%)")
        log.info("Saved %s: %s (%d chars)", fmt.value, out_path.name, len(result.output))

    if verbose:
        print(f"{'=' * 60}")
