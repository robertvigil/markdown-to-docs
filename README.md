# Markdown Documentation Pipeline

Convert Markdown documents to Word (.docx), PDF, and HTML with support for Mermaid diagrams, LaTeX math, images, and custom templates.

## Features

- **Multiple output formats** — Word, PDF, and HTML from the same Markdown source
- **Mermaid diagrams** — `.mmd` files rendered to PNG automatically
- **LaTeX math** — inline and display equations, rendered natively in each format
- **Automatic section numbering** — pandoc numbers headings in the output; no manual numbering needed in source
- **Table of contents** — auto-generated for all output formats
- **Word templates** — custom styling via `reference.docx`
- **Self-contained HTML** — images and KaTeX embedded, no external dependencies
- **PDF engine flexibility** — supports xelatex, pdflatex, typst, and weasyprint
- **Runtime tool detection** — checks what's installed and only offers available formats

## Quick start

```bash
# Build Word documents
uv run build.py -f docx

# Build PDF
uv run build.py -f pdf

# Build HTML
uv run build.py -f html

# Build all available formats
uv run build.py -f all

# Check what tools are installed
uv run build.py --check
```

## Requirements

- [pandoc](https://pandoc.org/) 3.1.3+
- [uv](https://docs.astral.sh/uv/)
- A PDF engine (for PDF output): [TeX Live](https://tug.org/texlive/) (xelatex/pdflatex), [Typst](https://typst.app/), or [weasyprint](https://weasyprint.org/)

Python dependencies (`mermaid-py`) are declared inline in `build.py` and installed automatically by uv.

Run `uv run build.py --check` to see what's available on your system.

## Usage

```
uv run build.py -f FORMAT [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-f, --format` | **Required.** Output format: `docx`, `pdf`, `html`, or `all` (repeatable) |
| `--pdf-engine` | PDF engine override: `xelatex`, `pdflatex`, `typst`, `weasyprint` |
| `--file` | Build a single source file (e.g. `--file budget-process`) |
| `--check` | Show available tools and output formats |
| `--clean` | Remove the `build/` directory |

### Examples

```bash
# Single file, specific format
uv run build.py -f pdf --file budget-process

# Multiple formats
uv run build.py -f docx -f html

# PDF with a specific engine
uv run build.py -f pdf --pdf-engine pdflatex

# Clean and rebuild everything
uv run build.py --clean && uv run build.py -f all
```

## Project structure

```
.
├── src/                  # Markdown source documents
│   ├── images/           # Screenshots and static images
│   └── *.md              # Each file becomes a separate output document
├── diagrams/             # Mermaid diagram sources (.mmd)
├── filters/
│   └── toc.lua           # Lua filter for static table of contents
├── templates/
│   └── reference.docx    # Word style template
├── build/                # Output directory (generated)
│   └── diagrams/         # Rendered diagram PNGs
└── build.py              # Build script
```

## Writing documents

### Front matter

Use `title` and `subtitle` only:

```yaml
---
title: "Document Title"
subtitle: "Optional Subtitle"
---
```

### Supported Markdown features

| Feature | Syntax | Notes |
|---------|--------|-------|
| Headings | `# H1` through `#### H4` | Auto-numbered in output; H1-H3 appear in the TOC |
| Cross-references | `[Label](#heading-anchor)` | Link by heading anchor, not by number |
| Tables | Pipe tables | Standard Markdown table syntax |
| Images | `![Alt](images/file.png)` | Place files in `src/images/` |
| Mermaid diagrams | `![Alt](diagram-name.png)` | Source `.mmd` files in `diagrams/` |
| Code blocks | Triple backticks with optional language | Syntax highlighting in HTML and PDF |
| Inline code | Single backticks | Use for file paths, commands, URLs |
| Math (inline) | `$x^2$` | LaTeX notation |
| Math (display) | `$$\sum_{i=1}^n i$$` | Rendered via LaTeX/OMML/KaTeX per format |
| Bold / Italic | `**bold**` / `*italic*` | |
| Strikethrough | `~~text~~` | |
| Links | `[text](url)` | |
| Blockquote callouts | `> **Note:** ...` | Use **Note:**, **Important:**, **Warning:** |
| Ordered / unordered lists | `1.` / `-` | Nesting supported |
| Task lists | `- [ ] item` | |
| Directory trees | Fenced code block with box-drawing characters | Use Windows `tree` output |
| Footnoted trees | Superscript markers (¹ ² ³) on folders + reference table | See sample-process.md |

### Windows paths

Always wrap Windows paths in backticks since backslashes are Markdown escape characters:

```markdown
Files are stored at `S:\budget\2026 Budget Files\Capital Expenditures`.
```

## How it works

1. **Diagram rendering** — all `.mmd` files in `diagrams/` are rendered to PNG via mermaid-py
2. **Document conversion** — pandoc converts each `.md` file in `src/` to the requested format(s)

Format-specific behavior:

| | Word (.docx) | PDF | HTML |
|---|---|---|---|
| TOC | Static via Lua filter | Static via Lua filter | Pandoc built-in `--toc` |
| Math | Word OMML equations | Native LaTeX | KaTeX (embedded) |
| Images | Embedded | Embedded | Base64 embedded |
| Styling | `templates/reference.docx` | LaTeX defaults + DejaVu Sans Mono | Pandoc default + KaTeX CSS |
| PDF engine | N/A | xelatex (default), pdflatex, typst, weasyprint | N/A |

## Customizing the Word template

The file `templates/reference.docx` controls the appearance of Word output. To customize it:

1. Open `templates/reference.docx` in Word or LibreOffice Writer.
2. Modify the styles (Heading 1, Heading 2, Body Text, etc.) to match your branding — fonts, colors, spacing, etc.
3. Adjust page margins, headers, and footers as needed.
4. Save the file (keep it as `.docx`).
5. Rebuild — the new styles are applied automatically.

> **Tip:** Do not add content to the reference template. Pandoc only reads the styles from this file, not the text.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Images missing in output | Check the filename matches exactly (case-sensitive). Verify the file exists in `src/images/` or `build/diagrams/`. |
| TOC is empty | Ensure the `toc.lua` filter is in `filters/` and the build script references it. |
| Diagram rendering fails | Check your internet connection — `mermaid-py` uses the mermaid.ink API. |
| Styles don't match template | Make sure you edited styles in `templates/reference.docx`, not just text. |
| pandoc not found | Install pandoc: `sudo apt install pandoc`. |
| PDF build fails | Run `uv run build.py --check` to verify a PDF engine is installed. |
| Box-drawing chars missing in PDF | The build uses DejaVu Sans Mono for monospace — ensure the font is installed. |
| Math not rendering in HTML | Requires an internet connection on first view if KaTeX CDN is used, or embedded KaTeX (current default). |

---

*This project was vibe-coded with [Claude Code](https://claude.ai/claude-code).*
