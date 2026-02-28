# /// script
# requires-python = ">=3.10"
# dependencies = ["mermaid-py"]
# ///
"""Build script: renders Mermaid diagrams and converts Markdown to documents."""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import mermaid as md
from mermaid.graph import Graph

PROJECT_DIR = Path(__file__).parent
DIAGRAMS_SRC = PROJECT_DIR / "src" / "diagrams"
DIAGRAMS_OUT = PROJECT_DIR / "build" / "diagrams"
TEMPLATES_DIR = PROJECT_DIR / "templates"
FILTERS_DIR = PROJECT_DIR / "filters"
SRC_DIR = PROJECT_DIR / "src"
BUILD_DIR = PROJECT_DIR / "build"

PDF_ENGINES = ["xelatex", "pdflatex", "typst", "weasyprint"]
FORMATS = ["docx", "pdf", "html"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build documentation from Markdown sources.",
    )
    parser.add_argument(
        "-f", "--format",
        nargs="+",
        choices=FORMATS + ["all"],
        required="--check" not in sys.argv and "--clean" not in sys.argv,
        help='Output format(s). Use "all" to build every format whose tools are available.',
    )
    parser.add_argument(
        "--pdf-engine",
        choices=PDF_ENGINES,
        default=None,
        help="PDF engine to use (default: auto-detect best available).",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Build a single source file (e.g. budget-process or budget-process.md).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Show detected tools and available output formats, then exit.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the build/ directory and exit.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Dependency detection
# ---------------------------------------------------------------------------

def detect_tools():
    """Check which external tools are available on PATH."""
    tools = {}
    for name in ["pandoc"] + PDF_ENGINES:
        tools[name] = shutil.which(name)
    return tools


def detect_best_pdf_engine(tools):
    """Return the best available PDF engine name, or None."""
    for engine in PDF_ENGINES:
        if tools.get(engine):
            return engine
    return None


def resolve_pdf_engine(tools, override=None):
    """Resolve which PDF engine to use. Exit with error if none available."""
    if override:
        if not tools.get(override):
            print(f"ERROR: Requested PDF engine '{override}' not found on PATH.")
            sys.exit(1)
        return override
    engine = detect_best_pdf_engine(tools)
    if engine is None:
        print("ERROR: No PDF engine found. Install one of: " + ", ".join(PDF_ENGINES))
        sys.exit(1)
    return engine


def get_pandoc_version():
    """Return pandoc version string, or None if not available."""
    try:
        result = subprocess.run(
            ["pandoc", "--version"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.splitlines()[0].split()[-1]
    except FileNotFoundError:
        pass
    return None


# ---------------------------------------------------------------------------
# --check
# ---------------------------------------------------------------------------

def run_check(tools):
    """Print a report of available tools and formats."""
    print("Documentation Build — Tool Check")
    print("=" * 50)

    pandoc_ver = get_pandoc_version() if tools["pandoc"] else None
    pandoc_label = f"{tools['pandoc']} ({pandoc_ver})" if pandoc_ver else "not found"
    print(f"\n  pandoc ............ {pandoc_label}")

    try:
        import mermaid  # noqa: F401
        print("  mermaid-py ........ OK")
    except ImportError:
        print("  mermaid-py ........ not found")

    print("\nPDF engines:")
    best = detect_best_pdf_engine(tools)
    for engine in PDF_ENGINES:
        path = tools.get(engine)
        marker = " (default)" if engine == best else ""
        label = f"{path}{marker}" if path else "not found"
        print(f"  {engine:16s} {label}")

    print("\nAvailable output formats:")
    for fmt in FORMATS:
        if fmt == "pdf":
            if best:
                print(f"  pdf ............... YES (via {best})")
            else:
                print("  pdf ............... NO (no PDF engine found)")
        elif tools["pandoc"]:
            print(f"  {fmt:16s} YES")
        else:
            print(f"  {fmt:16s} NO (pandoc not found)")

    md_files = sorted(SRC_DIR.glob("*.md"))
    mmd_files = sorted(DIAGRAMS_SRC.glob("*.mmd"))

    if md_files:
        print(f"\nSource files ({len(md_files)}):")
        for f in md_files:
            print(f"  {f.relative_to(PROJECT_DIR)}")

    if mmd_files:
        print(f"\nDiagram sources ({len(mmd_files)}):")
        for f in mmd_files:
            print(f"  {f.relative_to(PROJECT_DIR)}")

    print()


# ---------------------------------------------------------------------------
# --clean
# ---------------------------------------------------------------------------

def run_clean():
    """Remove the build/ directory."""
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"Removed {BUILD_DIR.relative_to(PROJECT_DIR)}/")
    else:
        print("Nothing to clean (build/ does not exist).")


# ---------------------------------------------------------------------------
# Source file resolution
# ---------------------------------------------------------------------------

def resolve_source_files(file_arg):
    """Return list of source .md files to build."""
    if file_arg is None:
        files = sorted(SRC_DIR.glob("*.md"))
        if not files:
            print("ERROR: No .md files found in src/")
            sys.exit(1)
        return files

    candidate = Path(file_arg)

    # Absolute or relative path that exists
    if candidate.is_file():
        return [candidate.resolve()]

    # Filename within SRC_DIR
    in_src = SRC_DIR / candidate.name
    if in_src.is_file():
        return [in_src]

    # Try adding .md extension
    if not candidate.suffix:
        in_src_ext = SRC_DIR / (candidate.name + ".md")
        if in_src_ext.is_file():
            return [in_src_ext]

    print(f"ERROR: Source file not found: {file_arg}")
    print(f"  Looked in: {SRC_DIR}")
    available = sorted(SRC_DIR.glob("*.md"))
    if available:
        print("  Available files:")
        for f in available:
            print(f"    {f.name}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Diagram rendering
# ---------------------------------------------------------------------------

def render_diagrams():
    """Render all .mmd files to PNG using mermaid-py."""
    DIAGRAMS_OUT.mkdir(parents=True, exist_ok=True)
    mmd_files = sorted(DIAGRAMS_SRC.glob("*.mmd"))

    if not mmd_files:
        print("  No .mmd files found in src/diagrams/")
        return []

    rendered = []
    for mmd_file in mmd_files:
        source = mmd_file.read_text()
        out_path = DIAGRAMS_OUT / mmd_file.with_suffix(".png").name
        print(f"  Rendering {mmd_file.name} -> {out_path.name} ...")

        graph = Graph(mmd_file.stem, source)
        result = md.Mermaid(graph)
        result.to_png(str(out_path))

        if out_path.exists():
            size_kb = out_path.stat().st_size / 1024
            print(f"    OK ({size_kb:.1f} KB)")
            rendered.append(out_path)
        else:
            print(f"    WARNING: {out_path.name} was not created")

    return rendered


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def heading_to_anchor(text):
    """Convert heading text to a pandoc-style anchor identifier."""
    anchor = text.lower()
    anchor = re.sub(r'[^\w\s-]', '', anchor)  # remove punctuation except hyphens
    anchor = anchor.strip()
    anchor = re.sub(r'[\s]+', '-', anchor)     # spaces to hyphens
    return anchor


def validate_links(md_files):
    """Check that all internal anchor links point to valid headings."""
    errors = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")

        # Collect anchors from headings (lines starting with #)
        anchors = set()
        for line in content.splitlines():
            m = re.match(r'^(#{1,6})\s+(.+?)(?:\s*#*\s*)?$', line)
            if m:
                anchors.add(heading_to_anchor(m.group(2)))

        # Find all internal links: [text](#anchor)
        for m in re.finditer(r'\[([^\]]*)\]\(#([^)]+)\)', content):
            link_text, target = m.group(1), m.group(2)
            if target not in anchors:
                # Find line number
                pos = m.start()
                line_num = content[:pos].count('\n') + 1
                errors.append((md_file.name, line_num, target, link_text))

    if errors:
        print("\n  WARNING: broken internal links found:")
        for fname, line_num, target, link_text in errors:
            print(f"    {fname}:{line_num} — #{target} (\"{link_text}\")")
        print()
    return errors


def validate_bare_paths(md_files):
    """Check for Windows paths outside backticks/code blocks (breaks LaTeX)."""
    errors = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        in_code_block = False
        for line_num, line in enumerate(content.splitlines(), 1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            # Remove inline code spans before checking
            stripped = re.sub(r'`[^`]+`', '', line)
            for m in re.finditer(r'[A-Z]:\\[\w\\]', stripped):
                # Extract the full path for the message
                path_match = re.search(r'[A-Z]:\\[^\s,)]+', stripped[m.start():])
                path_text = path_match.group(0) if path_match else m.group(0)
                errors.append((md_file.name, line_num, path_text))

    if errors:
        print("\n  WARNING: bare Windows paths found (wrap in backticks):")
        for fname, line_num, path in errors:
            print(f"    {fname}:{line_num} — {path}")
        print()
    return errors


# ---------------------------------------------------------------------------
# Document building
# ---------------------------------------------------------------------------

def build_pandoc_cmd(md_file, fmt, pdf_engine=None):
    """Assemble the pandoc command for a given format. Returns (cmd, out_file)."""
    ext_map = {"docx": ".docx", "pdf": ".pdf", "html": ".html"}
    out_file = BUILD_DIR / md_file.with_suffix(ext_map[fmt]).name

    resource_path = os.pathsep.join([
        str(PROJECT_DIR),
        str(SRC_DIR),
        str(SRC_DIR / "images"),
        str(DIAGRAMS_OUT),
    ])

    cmd = [
        "pandoc", str(md_file),
        "-o", str(out_file),
        f"--resource-path={resource_path}",
        "--number-sections",
    ]

    if fmt == "docx":
        cmd.append(f"--lua-filter={FILTERS_DIR / 'toc.lua'}")
        cmd.append(f"--reference-doc={TEMPLATES_DIR / 'reference.docx'}")

    elif fmt == "pdf":
        cmd.append(f"--pdf-engine={pdf_engine}")
        if pdf_engine == "weasyprint":
            cmd.append("--toc")
        else:
            cmd.append(f"--lua-filter={FILTERS_DIR / 'toc.lua'}")
        if pdf_engine in ("xelatex", "pdflatex"):
            cmd.extend([
                "-V", "geometry:margin=1in",
                "-V", "colorlinks=true",
                "-V", "mainfont=Liberation Sans",
                "-V", "monofont=DejaVu Sans Mono",
            ])

    elif fmt == "html":
        cmd.extend(["--standalone", "--toc", "--toc-depth=3", "--embed-resources",
                     "--katex=https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/",
                     f"--css={TEMPLATES_DIR / 'style.css'}"])

    return cmd, out_file


def build_document(md_file, fmt, pdf_engine=None):
    """Convert a single Markdown file to the given format using pandoc."""
    cmd, out_file = build_pandoc_cmd(md_file, fmt, pdf_engine)

    print(f"  {md_file.name} -> {out_file.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"    ERROR: pandoc failed:\n{result.stderr}")
        sys.exit(1)

    if result.stderr:
        print(f"    pandoc warnings: {result.stderr}")

    if out_file.exists():
        size_kb = out_file.stat().st_size / 1024
        print(f"    OK ({size_kb:.1f} KB)")
        return out_file
    else:
        print(f"    ERROR: {out_file.name} was not created")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    if args.clean:
        run_clean()
        return

    tools = detect_tools()

    if args.check:
        run_check(tools)
        return

    # Validate pandoc
    if not tools["pandoc"]:
        print("ERROR: pandoc not found on PATH. Install pandoc 3.1.3+.")
        sys.exit(1)

    # Resolve formats
    formats = []
    for f in args.format:
        if f == "all":
            formats.extend(FORMATS)
        elif f not in formats:
            formats.append(f)

    # For "all", skip pdf if no engine available
    if "all" in args.format and not detect_best_pdf_engine(tools):
        formats = [f for f in formats if f != "pdf"]
        print("Note: Skipping PDF (no PDF engine found).")

    # Resolve PDF engine if needed
    pdf_engine = None
    if "pdf" in formats:
        pdf_engine = resolve_pdf_engine(tools, args.pdf_engine)

    # Warn if --pdf-engine given but pdf not in formats
    if args.pdf_engine and "pdf" not in formats:
        print("Note: --pdf-engine is ignored for non-PDF formats.")

    # Resolve source files
    md_files = resolve_source_files(args.file)

    # Build header
    format_label = ", ".join(f.upper() for f in formats)
    print("=" * 60)
    print(f"Documentation Build [{format_label}]")
    print("=" * 60)

    # Validate sources
    print("\nValidating sources...")
    validate_links(md_files)
    validate_bare_paths(md_files)

    # Step 1: Diagrams
    total_steps = 1 + len(formats)
    step = 1
    print(f"\n[{step}/{total_steps}] Rendering Mermaid diagrams...")
    rendered = render_diagrams()

    # Build each format
    results = {}
    for fmt in formats:
        step += 1
        label = fmt.upper()
        if fmt == "pdf":
            label += f" (via {pdf_engine})"
        print(f"\n[{step}/{total_steps}] Building {label}...")
        built = []
        for md_file in md_files:
            out = build_document(md_file, fmt, pdf_engine)
            built.append(out)
        results[fmt] = built

    # Summary
    print("\n" + "=" * 60)
    print("Build complete!")
    print(f"  Diagrams rendered: {len(rendered)}")
    for fmt, files in results.items():
        print(f"  {fmt.upper()} documents: {len(files)}")
        for f in files:
            print(f"    - {f.relative_to(PROJECT_DIR)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
