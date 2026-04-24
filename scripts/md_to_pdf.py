"""Markdown を日本語対応 PDF に変換するスクリプト。"""

import sys
from pathlib import Path

from markdown_pdf import MarkdownPdf, Section


FONT_PATH = "C:/Windows/Fonts/YuGothR.ttc"
FONT_PATH_BOLD = "C:/Windows/Fonts/YuGothB.ttc"


def build_css() -> str:
    return f"""
@font-face {{
    font-family: 'YuGothic';
    src: url("{FONT_PATH}");
}}
@font-face {{
    font-family: 'YuGothic';
    src: url("{FONT_PATH_BOLD}");
    font-weight: bold;
}}
body {{
    font-family: 'YuGothic', sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #222;
}}
h1 {{
    font-family: 'YuGothic', sans-serif;
    font-size: 18pt;
    font-weight: bold;
    color: #1a1a1a;
    margin-top: 16px;
    margin-bottom: 8px;
}}
h2 {{
    font-family: 'YuGothic', sans-serif;
    font-size: 14pt;
    font-weight: bold;
    color: #1a1a1a;
    margin-top: 14px;
    margin-bottom: 6px;
}}
h3 {{
    font-family: 'YuGothic', sans-serif;
    font-size: 12pt;
    font-weight: bold;
    color: #222;
    margin-top: 10px;
}}
h4 {{
    font-family: 'YuGothic', sans-serif;
    font-size: 11pt;
    font-weight: bold;
    margin-top: 8px;
}}
p {{
    font-family: 'YuGothic', sans-serif;
    margin: 4px 0;
}}
li {{
    font-family: 'YuGothic', sans-serif;
    margin: 2px 0;
}}
strong, b {{
    font-weight: bold;
    color: #c0392b;
}}
code {{
    font-family: 'YuGothic', monospace;
    font-size: 9pt;
}}
table {{
    border-collapse: collapse;
    margin: 8px 0;
    width: 100%;
}}
th, td {{
    font-family: 'YuGothic', sans-serif;
    border: 1px solid #888;
    padding: 4px 8px;
    text-align: left;
    font-size: 9.5pt;
}}
th {{
    font-weight: bold;
}}
hr {{
    border: none;
    background: transparent;
    height: 0;
    margin: 0;
    padding: 0;
}}
a {{
    color: #0066cc;
    text-decoration: none;
}}
"""


def strip_hr(md: str) -> str:
    """Markdown の水平線 (---, ***, ___) を除去する。

    PyMuPDF Story は CSS で <hr> を非表示化しても灰色バーが残るため、
    Markdown レベルで除去する。
    """
    lines = md.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped in {"---", "***", "___"} or (
            stripped.startswith(("---", "***", "___"))
            and set(stripped) <= set("-*_ ")
        ):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def convert(md_path: Path, pdf_path: Path) -> None:
    content = strip_hr(md_path.read_text(encoding="utf-8"))

    pdf = MarkdownPdf(toc_level=0, optimize=True)
    pdf.meta["title"] = md_path.stem
    pdf.meta["author"] = "Singulab"

    pdf.add_section(Section(content, toc=False), user_css=build_css())
    pdf.save(str(pdf_path))
    print(f"[OK] {pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: md_to_pdf.py <input.md> <output.pdf>", file=sys.stderr)
        sys.exit(1)

    convert(Path(sys.argv[1]), Path(sys.argv[2]))
