"""Optional licensed Google Jobs discovery through SerpAPI, not page scraping."""
import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen
from .discovery import normalize, company_key


def search_google(query, fetch=None):
    key = os.environ.get('SERPAPI_API_KEY', '')
    terms = ' '.join(value for value in (query['role'], query.get('company'), query.get('work_mode')) if value)
    location = ', '.join(query.get(field, '') for field in ('city', 'country') if query.get(field))
    link = 'https://www.google.com/search?' + urlencode({'q': terms + ' jobs ' + location})
    if not key:
        return {'status': 'setup_required', 'jobs': [], 'sources': [], 'google_url': link,
                'message': 'Google search API setup required. Open Google search or use permitted providers.',
                'notice': 'Automatic Google Jobs discovery needs SERPAPI_API_KEY; no résumé is sent.'}
    params = {'engine': 'google_jobs', 'q': terms, 'api_key': key}
    if location:
        params['location'] = location
    try:
        if fetch:
            payload = fetch(params)
        else:
            with urlopen('https://serpapi.com/search.json?' + urlencode(params), timeout=30) as response:
                raw = response.read(5 * 1024 * 1024 + 1)
                if len(raw) > 5 * 1024 * 1024:
                    raise ValueError('Oversized search response')
                payload = json.loads(raw)
        if payload.get('error') or not isinstance(payload.get('jobs_results', []), list):
            raise ValueError('Search error')
        rows = []
        for job in payload.get('jobs_results', [])[:20]:
            links = job.get('apply_options', [])
            url = next((item.get('link') for item in links if isinstance(item, dict) and str(item.get('link', '')).startswith('https://')), '')
            if query.get('company') and company_key(query['company']) != company_key(job.get('company_name', '')):
                continue
            rows.append({'title': job.get('title'), 'company_name': job.get('company_name'),
                         'description': job.get('description'), 'url': url, 'location': job.get('location', '')})
        jobs = normalize('arbeitnow', {'data': rows})
        for job in jobs:
            job.update(provider='Google Jobs via SerpAPI', provider_home='https://serpapi.com/google-jobs-api')
            job['notes'].append('Review original listing: indexing does not prove an opening is current; location and work arrangement need confirmation.')
        return {'status': 'found' if jobs else 'no_matches', 'jobs': jobs, 'sources': [], 'google_url': link,
                'message': f'{len(jobs)} Google Jobs candidate listings available for review.',
                'notice': 'Descriptions come from Google Jobs via SerpAPI. This is not exhaustive; indexing may be stale. Filters are search criteria, not verified eligibility.'}
    except Exception:
        return {'status': 'source_unavailable', 'jobs': [], 'sources': [], 'google_url': link,
                'message': 'Google Jobs source unavailable. Use the search link or paste a full listing.',
                'notice': 'Unavailable search does not mean there are no jobs. No résumé was sent.'}
