"""Explainable text-readiness checks, not a prediction of any employer's ATS."""
import re
from .profiles import SECTIONS

def check_resume(profile):
    text = '\n'.join(page['text'] for page in profile['pages'])
    headings = {SECTIONS.get(line.strip().lower().rstrip(':')) for line in text.splitlines()}
    email = re.search(r'\b[^\s@]+@[^\s@]+\.[^\s@]+\b', text)
    phone = next((match for match in re.finditer(r'\+?\d[\d ()-]{6,25}\d', text)
                  if 8 <= len(re.sub(r'\D', '', match.group())) <= 15
                  and not re.fullmatch(r'\d{4}\s*-\s*\d{4}', match.group())), None)
    dates = re.search(r'\b(?:19|20)\d{2}\b', text)
    bad = sum(character == '\ufffd' or ord(character) < 32 and character not in '\n\r\t' or character == '\x7f' for character in text)
    heading_points = sum(points for name, points in [('skills', 6), ('education', 6), ('experience', 6)] if name in headings)
    heading_points += 2 if headings & {'summary', 'projects'} else 0
    checks = [
        {'name': 'Extractable text', 'points': 35 if len(text.strip()) >= 150 else 15 if len(text.strip()) >= 50 else 0, 'maximum': 35,
         'detail': f'{len(text.strip())} extracted characters across {len(profile["pages"])} pages. This checks this parser, not every ATS.'},
        {'name': 'Contact details detectable', 'points': (10 if email else 0) + (10 if phone else 0), 'maximum': 20,
         'detail': f'Email {"detected" if email else "not detected"}; phone {"detected" if phone else "not detected"}. Review accuracy yourself.'},
        {'name': 'Recognizable section headings', 'points': heading_points, 'maximum': 20,
         'detail': 'English skills, education and experience headings receive six points each; summary/projects receive two. Other languages/headings may be missed.'},
        {'name': 'Dates detectable', 'points': 10 if dates else 0, 'maximum': 10,
         'detail': 'A four-digit year was detected.' if dates else 'No four-digit year detected; check dates where relevant.'},
        {'name': 'Readable extracted characters', 'points': 15 if not bad else 8 if bad / max(1, len(text)) < .01 else 0, 'maximum': 15,
         'detail': f'{bad} replacement/control characters found; inspect extracted source text.'},
    ]
    score = sum(check['points'] for check in checks)
    return {'score': score, 'maximum': 100, 'local_checklist_met': score >= 80 and len(text.strip()) >= 150,
            'label': 'Meets the local text checklist' if score >= 80 and len(text.strip()) >= 150 else 'Review suggested before submission',
            'checks': checks,
            'notice': 'ATS readiness estimate from a fixed local checklist. It is not an employer ATS test, hiring probability, or guarantee of passing screening.',
            'limitations': ['Checks extracted text only; columns, images, reading order and employer-specific rules are not verified.',
                            'This score does not measure job-specific qualifications. Use the job comparison separately.',
                            'Headings/contact/date detection are heuristics and may miss valid international formats.'],
            'recommendations': [check['detail'] for check in checks if check['points'] < check['maximum']]}
