#!/usr/bin/env python3
"""Render disclosure Markdown to a matching PDF. Requires reportlab."""

import argparse
from html import escape
from pathlib import Path
import re
import tempfile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle


def export_pdf(source):
    source = Path(source)
    if source.suffix.lower() != '.md':
        raise ValueError('Expected a Markdown (.md) source file')
    text = source.read_text(encoding='utf-8')
    if not text.strip():
        raise ValueError('The Markdown source is empty')
    regular, bold = 'Helvetica', 'Helvetica-Bold'
    for folder, names in [
        ('/System/Library/Fonts/Supplemental', ('Arial.ttf', 'Arial Bold.ttf')),
        ('/usr/share/fonts/truetype/dejavu', ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf')),
    ]:
        if all((Path(folder) / name).is_file() for name in names):
            for label, name in zip(('Disclosure', 'DisclosureBold'), names):
                pdfmetrics.registerFont(TTFont(label, str(Path(folder) / name)))
            regular, bold = 'Disclosure', 'DisclosureBold'
            break
    pdfmetrics.registerFontFamily(regular, normal=regular, bold=bold)
    styles = getSampleStyleSheet()
    for name in ('Normal', 'Title', 'Heading1', 'Heading2'):
        styles[name].fontName = regular if name == 'Normal' else bold
    styles['Normal'].fontSize = 11
    styles['Normal'].leading = 15
    styles['Normal'].spaceAfter = 6
    cell = ParagraphStyle('Cell', fontName=regular, fontSize=8, leading=11)
    code = ParagraphStyle('Prompt', parent=styles['Normal'], backColor=colors.HexColor('#f2f4f7'), spaceAfter=0)
    width, height = A4
    margin = 48
    story = []
    lines = text.splitlines()
    i, fenced = 0, False

    def paragraph(value, style=styles['Normal'], literal=False, bullet=None):
        value = escape(value)
        if not literal:
            value = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', value.replace('\\|', '|'))
        return Paragraph(value, style, bulletText=bullet)

    # shortcut: disclosure Markdown blocks only; use a full renderer for rich Markdown.
    while i < len(lines):
        raw = lines[i].expandtabs(2)
        line = raw.strip()
        if line.startswith('```'):
            fenced = not fenced
            if not fenced:
                story.append(Spacer(1, 8))
        elif fenced:
            story.append(paragraph(raw, code, literal=True) if line else Spacer(1, 8))
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                parts = re.split(r'(?<!\\)\|', lines[i].strip().strip('|'))
                if not all(re.fullmatch(r'\s*:?-+:?\s*', part) for part in parts):
                    rows.append([paragraph(part.strip(), cell) for part in parts])
                i += 1
            if any(len(row) != len(rows[0]) for row in rows):
                raise ValueError('Unequal table columns; escape literal pipes as \\|')
            table = LongTable(rows, colWidths=(width - 2 * margin) / len(rows[0]), repeatRows=1, splitInRow=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e4eaf1')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#b8c2cf')),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.extend([table, Spacer(1, 12)])
            continue
        elif line:
            heading = re.match(r'^(#{1,3})\s+(.+)$', line)
            if heading:
                if (heading[2] == 'Disclosure Log' or heading[2].startswith('Part 2:')) and story:
                    story.append(PageBreak())
                style = styles[('Title', 'Heading1', 'Heading2')[len(heading[1]) - 1]]
                story.append(paragraph(heading[2], style))
            elif line.startswith('- '):
                level = (len(raw) - len(raw.lstrip())) // 2
                indent = level * 24
                following = next((item for item in lines[i + 1:] if item.strip()), '')
                has_children = following.lstrip().startswith('- ') and len(following) - len(following.lstrip()) > len(raw) - len(raw.lstrip())
                style = ParagraphStyle('Bullet', parent=styles['Normal'],
                                       leftIndent=indent + 14, bulletIndent=indent,
                                       bulletFontName=regular, bulletFontSize=10,
                                       spaceBefore=6 if level == 0 else 0,
                                       spaceAfter=2,
                                       keepWithNext=has_children)
                story.append(paragraph(line[2:], style, bullet=('●', '○', '■')[min(level, 2)]))
            else:
                story.append(paragraph(line))
        i += 1

    def footer(canvas, doc):
        canvas.setFont(regular, 8)
        canvas.drawString(margin, 20, 'AI-use disclosure | Session snapshot')
        canvas.drawRightString(width - margin, 20, str(doc.page))

    target = source.with_suffix('.pdf')
    with tempfile.NamedTemporaryFile(dir=source.parent, suffix='.pdf', delete=False) as stream:
        temporary = Path(stream.name)
    try:
        doc = SimpleDocTemplate(str(temporary), pagesize=(width, height),
                                leftMargin=margin, rightMargin=margin,
                                topMargin=margin, bottomMargin=margin,
                                title='AI Prompt Log and Disclosure Summary')
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown', type=Path)
    print(export_pdf(parser.parse_args().markdown))
