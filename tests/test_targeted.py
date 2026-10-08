import unittest
from jobmatch.profiles import draft_profile
from jobmatch.targeted import compare_target


class TargetedTests(unittest.TestCase):
    def profile(self):
        profile = draft_profile([{'page': 1, 'text': 'Skills\nPython\nEducation\nBS Computing\n'}])
        for field in ('skills', 'experience', 'education'):
            for item in profile[field]:
                item['confirmed'] = True
        profile['reviewed'] = True
        return profile

    def listing(self):
        return {'title': 'Python Developer', 'company': 'Fictional Company', 'source_url': 'https://example.com/job',
                'location': '', 'work_mode': '', 'description': 'Minimum qualifications\nPython and SQL required\nBachelor degree and 2 years of experience\nPreferred qualifications\nRedis experience\nResponsibilities\nBuild REST APIs'}

    def test_exact_evidence_required_preferred_and_weekly_budget(self):
        profile, listing = self.profile(), self.listing()
        result = compare_target(profile, listing, extra_skills=['Redis'], minutes=91)
        python = next(item for item in result['skills'] if item['skill'] == 'Python')
        self.assertEqual((python['kind'], python['status']), ('required', 'supported'))
        self.assertEqual(next(item for item in result['skills'] if item['skill'] == 'SQL')['status'], 'not_evidenced')
        self.assertEqual(next(item for item in result['skills'] if item['skill'] == 'Redis')['kind'], 'preferred')
        self.assertEqual(next(item for item in result['skills'] if item['skill'] == 'REST APIs')['kind'], 'mentioned')
        for item in result['skills']:
            proof = item['evidence']
            self.assertEqual(listing['description'][proof['start']:proof['end']], proof['quote'])
        self.assertTrue(result['other_requirements_to_review'])
        plan = result['interview_plan']
        self.assertEqual(len(plan['days']), 7)
        self.assertEqual(plan['priorities'][0]['skill'], 'SQL')
        for day in plan['days']:
            self.assertEqual(sum(task['minutes'] for task in day['tasks']), 91)
        self.assertIn('not a prediction', plan['notice'])
        self.assertEqual(sum(stage['minutes'] for stage in plan['mock_interview']), 91)
        self.assertTrue(all(question['evidence']['quote'] in listing['description'] for question in plan['questions']))

    def test_unconfirmed_unsafe_url_and_unknown_skill_review(self):
        profile, listing = self.profile(), self.listing()
        profile['reviewed'] = False
        with self.assertRaisesRegex(ValueError, 'Confirm'):
            compare_target(profile, listing)
        profile['reviewed'] = True
        listing['source_url'] = 'javascript:alert(1)'
        with self.assertRaisesRegex(ValueError, 'Source link'):
            compare_target(profile, listing)
        listing['source_url'] = ''
        listing['description'] = 'Requirements: NovelFramework\nPython is not required'
        result = compare_target(profile, listing, extra_skills=['NovelFramework'])
        self.assertEqual(result['recognized_required_skills'], 1)
        self.assertEqual(next(item for item in result['skills'] if item['skill'] == 'Python')['kind'], 'mentioned')
        self.assertEqual(result['required_skills_supported'], 0)

    def test_mixed_qualifiers_and_experience_gap_are_not_invented(self):
        listing = self.listing()
        listing['description'] = 'Requirements\nPython required; SQL preferred\n3+ years of professional experience'
        report = compare_target(self.profile(), listing, context={'experience_years': 1})
        self.assertEqual(report['recognized_required_skills'], 0)
        self.assertTrue(all(item['kind'] == 'mentioned' for item in report['skills']))
        self.assertIn('3 years', report['preference_notes'][0])
