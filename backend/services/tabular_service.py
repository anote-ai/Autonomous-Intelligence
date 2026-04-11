"""Tabular data ingestion service: CSV, TSV, Excel (XLSX/XLS/ODS).

Tika extracts spreadsheet data as a flat whitespace-separated dump that loses
all column/row structure — making the data nearly unsearchable.  This service
reads spreadsheets natively and converts each sheet into a Markdown table so
that the column headers, values, and relationships are preserved in the index.

Supported formats
-----------------
- CSV  (text/csv)
- TSV  (text/tab-separated-values)
- XLSX (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
- XLS  (application/vnd.ms-excel)
- ODS  (application/vnd.oasis.opendocument.spreadsheet)

Dependencies: ``openpyxl`` (already in most ML stacks) for XLSX/ODS,
``xlrd`` for legacy XLS.  Both are lightweight; CSV/TSV uses stdlib only.
"""
import csv
import io
from typing import Optional

# Maximum rows rendered into Markdown per sheet.  Beyond this we summarise.
_MAX_ROWS_FULL = 500
# Maximum columns rendered per sheet (very wide sheets become unreadable).
_MAX_COLS = 50


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_tabular(
    file_bytes: bytes,
    filename: str,
    mime_type: str = "text/csv",
) -> str:
    """Parse tabular data and return a structured Markdown document.

    The document is suitable for direct storage as ``document_text`` and
    feeding into the chunking + embedding pipeline.

    Returns a plain string; never raises so the document record is always
    created even on parse failure.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        if ext in ("csv",) or mime_type == "text/csv":
            return _ingest_delimited(file_bytes, filename, delimiter=",")
        if ext in ("tsv",) or mime_type == "text/tab-separated-values":
            return _ingest_delimited(file_bytes, filename, delimiter="\t")
        if ext in ("xlsx", "ods") or "spreadsheetml" in mime_type or "opendocument.spreadsheet" in mime_type:
            return _ingest_excel(file_bytes, filename, engine="openpyxl")
        if ext == "xls" or mime_type == "application/vnd.ms-excel":
            return _ingest_excel(file_bytes, filename, engine="xlrd")
        # Fallback: try CSV
        return _ingest_delimited(file_bytes, filename, delimiter=",")
    except Exception as exc:
        return f"[Tabular parsing failed for '{filename}': {exc}]"


# ---------------------------------------------------------------------------
# Delimited (CSV / TSV)
# ---------------------------------------------------------------------------

def _ingest_delimited(file_bytes: bytes, filename: str, delimiter: str) -> str:
    text = _decode(file_bytes)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return f"['{filename}' appears to be empty.]"

    return _format_sheet(filename, rows, sheet_name=None)


# ---------------------------------------------------------------------------
# Excel (XLSX / XLS / ODS)
# ---------------------------------------------------------------------------

def _ingest_excel(file_bytes: bytes, filename: str, engine: str) -> str:
    try:
        import openpyxl  # noqa: F401 — presence check for xlsx/ods
    except ImportError:
        return (
            "[openpyxl is not installed. "
            "Run `pip install openpyxl` to enable Excel ingestion.]"
        )

    try:
        import pandas as pd
    except ImportError:
        return (
            "[pandas is not installed. "
            "Run `pip install pandas openpyxl` to enable Excel ingestion.]"
        )

    buf = io.BytesIO(file_bytes)
    sections: list[str] = [f"# Spreadsheet: {filename}\n"]

    try:
        xf = pd.ExcelFile(buf, engine=engine)
    except Exception as exc:
        return f"[Failed to open '{filename}': {exc}]"

    for sheet_name in xf.sheet_names:
        df = xf.parse(sheet_name, header=None, dtype=str)
        df = df.fillna("")
        rows = [list(r) for r in df.itertuples(index=False, name=None)]
        sections.append(_format_sheet(filename, rows, sheet_name=str(sheet_name)))

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Shared formatting helpers
# ---------------------------------------------------------------------------

def _format_sheet(
    filename: str,
    rows: list[list],
    sheet_name: Optional[str],
) -> str:
    if not rows:
        label = f"Sheet '{sheet_name}'" if sheet_name else filename
        return f"[{label} is empty.]"

    # Truncate very wide tables
    if len(rows[0]) > _MAX_COLS:
        rows = [r[:_MAX_COLS] + ["…"] for r in rows]

    header_row = rows[0]
    data_rows = rows[1:]

    total_rows = len(data_rows)
    truncated = total_rows > _MAX_ROWS_FULL
    display_rows = data_rows[:_MAX_ROWS_FULL]

    lines: list[str] = []

    if sheet_name:
        lines.append(f"## Sheet: {sheet_name}")
        lines.append(
            f"*{total_rows} data row(s), {len(header_row)} column(s)"
            + (" — showing first 500 rows" if truncated else "") + "*\n"
        )

    # Markdown table
    lines.append(_md_table(header_row, display_rows))

    if truncated:
        lines.append(
            f"\n*…{total_rows - _MAX_ROWS_FULL} additional rows not shown. "
            "The full data is embedded in the index.*"
        )
        # Also append all remaining rows as plain CSV so they are indexed
        # (they won't display nicely but will be found by semantic search).
        lines.append("\n### Full data (indexed)\n```")
        for r in data_rows[_MAX_ROWS_FULL:]:
            lines.append(",".join(str(c) for c in r))
        lines.append("```")

    return "\n".join(lines)


def _md_table(headers: list, rows: list[list]) -> str:
    """Render a list of rows as a Markdown table."""
    col_count = max(len(headers), max((len(r) for r in rows), default=0))

    def pad(row: list, n: int) -> list:
        return list(row) + [""] * (n - len(row))

    h = pad(headers, col_count)
    header_line = "| " + " | ".join(str(c) for c in h) + " |"
    sep_line = "| " + " | ".join("---" for _ in h) + " |"
    data_lines = [
        "| " + " | ".join(str(c) for c in pad(r, col_count)) + " |"
        for r in rows
    ]
    return "\n".join([header_line, sep_line] + data_lines)


# ---------------------------------------------------------------------------
# Plain-text ingestion (TXT, MD, RST, code files, etc.)
# ---------------------------------------------------------------------------

def ingest_plaintext(file_bytes: bytes, filename: str) -> str:
    """Decode a plain-text file and return its contents with a filename header.

    Tries UTF-8 first, then falls back to latin-1 so that legacy files with
    8-bit characters are never silently dropped.
    """
    content = _decode(file_bytes)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    return f"# {filename}\n\n```{ext}\n{content}\n```"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _decode(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("latin-1")
