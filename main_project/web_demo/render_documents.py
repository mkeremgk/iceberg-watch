"""Render the project's deliberately small Markdown subset as readable site pages."""
from html import escape
from pathlib import Path
import re

PAGES = {'technical-report': 'Technical report', 'architecture': 'Architecture',
         'data-setup': 'Data and reproduction', 'sources': 'Sources and publication'}


def inline(text):
    text = escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', r'<a href="\2">\1</a>', text)
    return text


def diagram():
    steps = [('Local preparation', 'Satellite measurements and geographic references'),
             ('AWS analysis', 'OpenCV candidates, associations and conditional paths'),
             ('Checked exports', 'Saved coordinates, distances and source hashes'),
             ('Public website', 'Recorded Antarctic maps and a separate synthetic example')]
    blocks = []
    for i, (title, detail) in enumerate(steps):
        y = 15 + i * 110
        blocks.append(f'<rect x="15" y="{y}" width="670" height="82" rx="12" fill="#e6efeb"/>'
                      f'<text x="38" y="{y+31}" font-size="20" font-weight="bold">{title}</text>'
                      f'<text x="38" y="{y+58}" font-size="15">{detail}</text>')
        if i < 3:
            blocks.append(f'<path d="M350 {y+84} v24 m-5 -6 l5 6 5 -6" fill="none" stroke="#367574" stroke-width="2"/>')
    return '<svg viewBox="0 0 700 445" role="img" aria-label="Local preparation feeds AWS analysis, checked exports and the public website" xmlns="http://www.w3.org/2000/svg">' + ''.join(blocks) + '</svg>'


def render_markdown(text):
    output, paragraph, code = [], [], None
    language = ''
    def flush():
        if paragraph:
            output.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if code is None:
                code, language = [], line[3:].strip()
            else:
                output.append(diagram() if language == 'mermaid' else '<pre><code>' + escape('\n'.join(code)) + '</code></pre>')
                code = None
        elif code is not None:
            code.append(line)
        elif not line.strip():
            flush()
        elif line.startswith('#'):
            flush()
            heading, title = line.split(' ', 1)
            level = len(heading)
            output.append(f'<h{level}>{inline(title)}</h{level}>')
        else:
            paragraph.append(line.strip())
    flush()
    if code is not None:
        raise ValueError('Unclosed documentation code block')
    return '\n'.join(output)


def render_documents(directory: Path):
    nav = '<nav class="doc-nav"><a href="index.html">← Return to the explorer</a>' + ''.join(
        f'<a href="{slug}.html">{title}</a>' for slug, title in PAGES.items()) + '</nav>'
    for slug, title in PAGES.items():
        body = render_markdown((directory / f'{slug}.md').read_text())
        page = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title} | Iceberg Watch</title><link rel="stylesheet" href="styles.css"></head><body><main class="document">{nav}{body}<p><a href="{slug}.md">Download this document as Markdown</a></p></main></body></html>'
        (directory / f'{slug}.html').write_text(page)
