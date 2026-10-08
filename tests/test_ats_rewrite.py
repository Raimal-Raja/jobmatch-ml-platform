import unittest
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET
from jobmatch.ats import check_resume
from jobmatch.profiles import draft_profile
from jobmatch.rewrite import draft_resume, docx_bytes

class ResumeReadinessTests(unittest.TestCase):
    def profile(self):
        text = 'Fictional Candidate\nfictional@example.com | +1 202 555 0137\nProfessional Summary\nDevelops tested Python software with careful data validation.\nSkills\nPython, SQL\nExperience\nDeveloper at Fictional Labs 2023-2025\nBuilt a pipeline for 120 records.\nEducation\nBS Computing 2023\n'
        profile = draft_profile([{'page': 1, 'text': text}]); profile['reviewed'] = True
        return profile

    def test_score_components_and_non_guarantee(self):
        result = check_resume(self.profile())
        self.assertEqual(result['score'], sum(check['points'] for check in result['checks']))
        self.assertEqual(sum(check['maximum'] for check in result['checks']), 100)
        self.assertTrue(result['local_checklist_met'])
        self.assertIn('not an employer ATS test', result['notice'])
        weak = check_resume(draft_profile([{'page': 1, 'text': 'short'}]))
        self.assertFalse(weak['local_checklist_met'])
        self.assertLess(weak['score'], 80)

    def test_draft_preserves_facts_and_export_is_plain_ooxml(self):
        profile = self.profile(); draft = draft_resume(profile)
        for fact in ('120 records', '2023-2025', 'Fictional Labs', 'Python, SQL'):
            self.assertIn(fact, draft['text'])
        self.assertNotIn('Kubernetes', draft['text'])
        with zipfile.ZipFile(BytesIO(docx_bytes(draft['text']))) as archive:
            for name in archive.namelist():
                ET.fromstring(archive.read(name))
            self.assertNotIn('word/header1.xml', archive.namelist())
            self.assertNotIn('word/vbaProject.bin', archive.namelist())
            self.assertIn(b'120 records', archive.read('word/document.xml'))
        with self.assertRaises(ValueError):
            docx_bytes('Unreadable \ufffd text')
        profile['reviewed'] = False
        with self.assertRaises(ValueError):
            draft_resume(profile)
