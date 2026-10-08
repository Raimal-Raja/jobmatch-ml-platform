"""Source-preserving résumé drafts and dependency-free single-column DOCX export."""
import re
import unicodedata
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape
from .profiles import SECTIONS

TITLES = {'summary': 'Professional Summary', 'skills': 'Technical Skills', 'experience': 'Experience',
          'education': 'Education', 'projects': 'Projects', 'certifications': 'Certifications'}

def draft_resume(profile):
    if not profile.get('reviewed'):
        raise ValueError('Confirm your profile before preparing a rewrite')
    lines = []
    for page in profile['pages']:
        for original in page['text'].splitlines():
            line = unicodedata.normalize('NFKC', original).strip()
            if not line:
                continue
            section = SECTIONS.get(line.lower().rstrip(':'))
            if section:
                line = 'Education and Certifications' if 'certifications' in line.lower() and section == 'education' else TITLES[section]
            else:
                line = re.sub(r'^[\x7f•▪●]+\s*', '- ', line)
                line = ''.join(character for character in line if ord(character) >= 32 or character == '\t')
            lines.append(line)
    return {'text': '\n'.join(lines),
            'notice': 'Editable source-preserving reformat of the original extracted résumé. It does not invent skills, employment, dates, degrees or metrics and cannot guarantee ATS acceptance.',
            'review_items': ['Review the full draft against your original PDF, including projects and certifications.',
                             'Apply any profile corrections to this draft before downloading; original source claims remain unless you edit them.',
                             'Repair unreadable characters and line wrapping. Use genuine accomplishments; do not insert missing job requirements as qualifications.']}

def docx_bytes(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 50000:
        raise ValueError('Résumé draft must contain 1–50,000 characters')
    if '\ufffd' in text or any(ord(c) < 32 and c not in '\n\r\t' for c in text):
        raise ValueError('Correct unreadable/control characters in the draft before exporting')
    namespaces = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    headings = set(TITLES.values()) | {'Education and Certifications'}
    paragraphs = []
    for index, line in enumerate(line.strip() for line in text.splitlines() if line.strip()):
        style = 'Title' if index == 0 else 'Heading1' if line in headings else 'Normal'
        paragraphs.append(f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>')
    document = f'<?xml version="1.0" encoding="UTF-8"?><w:document {namespaces}><w:body>{"".join(paragraphs)}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="864" w:right="864" w:bottom="864" w:left="864"/></w:sectPr></w:body></w:document>'
    styles = f'''<?xml version="1.0" encoding="UTF-8"?><w:styles {namespaces}>
    <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="60" w:line="240" w:lineRule="auto"/><w:widowControl/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="21"/><w:color w:val="000000"/></w:rPr></w:style>
    <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>
    <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:outlineLvl w:val="0"/><w:spacing w:before="160" w:after="80"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style></w:styles>'''
    files = {'word/document.xml': document, 'word/styles.xml': styles,
        '[Content_Types].xml': '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>',
        '_rels/.rels': '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        'word/_rels/document.xml.rels': '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'}
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content.encode('utf-8'))
    return output.getvalue()
