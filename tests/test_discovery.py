import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from jobmatch.discovery import JobDiscovery, indeed_link

class DiscoveryTests(unittest.TestCase):
    def payload(self):
        return {'jobs': [{'id': 1, 'title': 'Python Developer', 'company_name': 'Example LLC',
                         'url': 'https://remotive.com/remote-jobs/test/1', 'candidate_required_location': 'Worldwide',
                         'description': '<h2>Required:</h2><p>Python and SQL</p><script>bad()</script>'}]}

    def test_cached_provider_country_city_and_safe_listing_text(self):
        calls = []
        def fetch(url): calls.append(url); return self.payload()
        with tempfile.TemporaryDirectory() as root:
            client = JobDiscovery(root, fetch)
            query = {'role': 'Python Developer', 'company': 'Example', 'country': 'Pakistan', 'city': 'Karachi', 'work_mode': 'remote', 'provider': 'remotive'}
            report = client.search(query)
            self.assertEqual(report['status'], 'found')
            self.assertEqual(len(report['jobs']), 1)
            self.assertNotIn('bad()', report['jobs'][0]['description'])
            self.assertTrue(report['jobs'][0]['notes'])
            self.assertEqual(client.search(query)['status'], 'found')
            self.assertEqual(len(calls), 1)
            query['company'] = 'Different Company'
            self.assertEqual(client.search(query)['status'], 'no_matches')
            params = parse_qs(urlsplit(indeed_link(query)).query)
            self.assertIn('Karachi', params['l'][0])

    def test_provider_failure_is_not_no_jobs_and_company_is_not_description_match(self):
        def failed(url): raise OSError('offline')
        with tempfile.TemporaryDirectory() as root:
            report = JobDiscovery(root, failed).search({'role': 'Python', 'provider': 'remotive'})
            self.assertEqual(report['status'], 'source_unavailable')
        payload = self.payload(); payload['jobs'][0]['description'] += ' Work with Google APIs'
        with tempfile.TemporaryDirectory() as root:
            report = JobDiscovery(root, lambda url: payload).search({'role': 'Python', 'company': 'Google', 'provider': 'remotive'})
            self.assertEqual(report['status'], 'no_matches')

    def test_regional_remote_job_does_not_match_an_unrelated_city(self):
        payload = self.payload(); payload['jobs'][0]['candidate_required_location'] = 'USA'
        with tempfile.TemporaryDirectory() as root:
            client = JobDiscovery(root, lambda url: payload)
            self.assertEqual(client.search({'role': 'Python', 'city': 'Karachi', 'provider': 'remotive'})['status'], 'no_matches')
            self.assertEqual(client.search({'role': 'Python', 'country': 'US', 'provider': 'remotive'})['status'], 'found')
