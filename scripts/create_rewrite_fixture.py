"""Create a fictional Word export for CI rendering; never reads private profiles."""
from pathlib import Path
from jobmatch.profiles import draft_profile, extract_pages
from jobmatch.rewrite import draft_resume, docx_bytes
from scripts.create_sample_resume import sample_pdf

profile = draft_profile(extract_pages(sample_pdf()))
profile['reviewed'] = True
target = Path('reports/resume-draft-sample.docx')
target.parent.mkdir(exist_ok=True)
target.write_bytes(docx_bytes(draft_resume(profile)['text']))
print('Created fictional résumé export fixture')
