"""Run with a Python environment containing reportlab and pypdf."""

from pathlib import Path
import tempfile
from unittest.mock import patch

from pypdf import PdfReader

from export_pdf import export_pdf


with tempfile.TemporaryDirectory() as folder:
    source = Path(folder) / 'log.md'
    markdown = '# Disclosure\n\n## Disclosure Summary\n\n- **Parent**\n  - Nested detail\n    - Supporting detail\n\nHuman selected the scope.\n\n'
    markdown += '## Disclosure Log\n\n'
    markdown += '| # | Prompt | Decision |\n| --- | --- | --- |\n'
    markdown += '| 1 | A \\| B <test> & evidence | Not approved |\n'
    markdown += '| 2 | ' + ('Long response ' * 800) + ' | Pending |\n'
    markdown += '\n### Exact prompt\n\n```text\nKeep # literal | <markup> & Unicode: café **literal**\n```\n\nEND OF RECORD\n'
    source.write_text(markdown, encoding='utf-8')
    target = export_pdf(source)
    first = PdfReader(target)
    extracted = '\n'.join(page.extract_text() for page in first.pages)
    assert len(first.pages) > 1
    assert len(first.pages) > 2  # The long table row must span pages beyond the part break.
    assert float(first.pages[0].mediabox.width) < float(first.pages[0].mediabox.height)
    assert 'Disclosure Log' not in first.pages[0].extract_text()
    assert 'Disclosure Log' in first.pages[1].extract_text()
    assert '**Parent**' not in extracted
    positions = {}
    parent_fonts = []

    def position(text, cm, tm, font, size):
        if text.strip() in ('Parent', 'Nested detail', 'Supporting detail'):
            positions[text.strip()] = cm[4] + tm[4]
        if text.strip() == 'Parent':
            parent_fonts.append(str((font or {}).get('/BaseFont', '')))

    first.pages[0].extract_text(visitor_text=position)
    assert positions['Nested detail'] > positions['Parent'], positions
    assert positions['Supporting detail'] > positions['Nested detail'], positions
    assert any('Bold' in font for font in parent_fonts), parent_fonts
    for marker in ('●', '○', '■'):
        assert marker in first.pages[0].extract_text(), marker
    for value in ['Human selected the scope', 'A | B <test> & evidence', 'Keep # literal', 'café', '**literal**', 'END OF RECORD']:
        assert value in extracted, value
    assert extracted.split().count('Long') == 800
    assert source.read_text(encoding='utf-8') == markdown
    assert export_pdf(source) == target
    assert 'END OF RECORD' in PdfReader(target).pages[-1].extract_text()
    previous = target.read_bytes()
    with patch('export_pdf.SimpleDocTemplate.build', side_effect=RuntimeError('Simulated build failure')):
        try:
            export_pdf(source)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Build failure must propagate')
    assert target.read_bytes() == previous
    assert sorted(p.name for p in Path(folder).iterdir()) == ['log.md', 'log.pdf']
    source.write_text('', encoding='utf-8')
    try:
        export_pdf(source)
    except ValueError:
        pass
    else:
        raise AssertionError('Empty source must fail')
    assert target.read_bytes() == previous
    assert sorted(p.name for p in Path(folder).iterdir()) == ['log.md', 'log.pdf']
print('PASS: nested indentation, bold, portrait layout, part break, tables, long rows, literal prompts, Unicode, repeat export, and failure preservation')
