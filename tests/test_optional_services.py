import json
import os
import unittest
from unittest.mock import patch
from jobmatch.google_jobs import search_google
from jobmatch.optional_ai import generate_draft


class OptionalServicesTests(unittest.TestCase):
    def test_google_setup_failure_and_full_description(self):
        query = {'role': 'Python Developer', 'company': 'Example', 'city': 'Karachi'}
        with patch.dict(os.environ, {'SERPAPI_API_KEY': ''}):
            self.assertEqual(search_google(query)['status'], 'setup_required')
        payload = {'jobs_results': [{'title': 'Python Developer', 'company_name': 'Example', 'description': 'Required Python and SQL', 'location': 'Karachi', 'apply_options': [{'link': 'https://example.com/job'}]}]}
        with patch.dict(os.environ, {'SERPAPI_API_KEY': 'fictional-test-value'}):
            result = search_google(query, lambda params: payload)
            self.assertEqual(result['jobs'][0]['description'], 'Required Python and SQL')
            self.assertEqual(result['jobs'][0]['provider'], 'Google Jobs via SerpAPI')
            self.assertEqual(search_google(query, lambda params: {'error': 'private provider details'})['status'], 'source_unavailable')

    def test_ai_consent_evidence_and_redacted_errors(self):
        profile = {'reviewed': True, 'pages': [{'text': 'Built Python APIs'}], 'skills': [{'value': 'Python'}], 'experience': [], 'education': []}
        with patch.dict(os.environ, {'NVIDIA_API_KEY': 'fictional-test-value'}):
            with self.assertRaisesRegex(ValueError, 'Confirm sending'):
                generate_draft(profile, False)
            def response(quote):
                return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'paragraphs': [{'text': 'Built APIs using Python', 'source_quote': quote}]})}}]}
            result = generate_draft(profile, True, lambda payload: response('Built Python APIs'))
            self.assertIn('Python', result['text'])
            with self.assertRaisesRegex(ValueError, 'failed evidence validation'):
                generate_draft(profile, True, lambda payload: response('Invented employer'))
            with self.assertRaisesRegex(ValueError, 'failed evidence validation'):
                generate_draft(profile, True, lambda payload: {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'paragraphs': [{'text': 'Improved APIs by 99%', 'source_quote': 'Built Python APIs'}]})}}]})
            with self.assertRaisesRegex(ValueError, 'no provider details'):
                generate_draft(profile, True, lambda payload: (_ for _ in ()).throw(RuntimeError('fictional-test-value')))
