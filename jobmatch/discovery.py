"""Bounded public-provider discovery; source failure is distinct from no matches."""
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

PROVIDERS = {
    'remotive': ('https://remotive.com/api/remote-jobs?limit=500', 'Remotive', 'Remote listings; API data is delayed 24 hours; latest 500 records.', 'https://remotive.com'),
    'arbeitnow': ('https://www.arbeitnow.com/api/job-board-api', 'Arbeitnow', 'Latest API page; primarily European listings. Non-remote arrangement may be unknown.', 'https://www.arbeitnow.com'),
    'arbeitnow-uk': ('https://www.arbeitnow.co.uk/api/job-board-api', 'Arbeitnow UK', 'Latest UK API page. Non-remote arrangement may be unknown.', 'https://www.arbeitnow.co.uk'),
}

class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed = {'remotive.com', 'www.remotive.com', 'arbeitnow.com', 'www.arbeitnow.com', 'arbeitnow.co.uk', 'www.arbeitnow.co.uk'}
        if urlsplit(newurl).scheme != 'https' or urlsplit(newurl).hostname not in allowed:
            raise ValueError('Provider redirected outside its approved hosts')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch_json(url):
    started, data = time.monotonic(), bytearray()
    with build_opener(SafeRedirect()).open(Request(url, headers={'User-Agent': 'JobMatch-local-demo/0.10', 'Accept': 'application/json'}), timeout=10) as response:
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > 15 * 1024 * 1024 or time.monotonic() - started > 20:
                raise ValueError('Provider response exceeded size/time limits')
    return json.loads(data)

class ListingText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('p', 'li', 'br', 'h1', 'h2', 'h3', 'h4') and not self.skip:
            self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        elif tag in ('p', 'li', 'h1', 'h2', 'h3', 'h4') and not self.skip:
            self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def normalize(provider, payload):
    rows = payload.get('jobs' if provider == 'remotive' else 'data')
    if not isinstance(rows, list):
        raise ValueError('Unexpected provider response schema')
    output = []
    for row in rows[:500]:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k].strip() for k in ('title', 'company_name', 'description', 'url')):
            continue
        link = urlsplit(row['url'])
        if link.scheme != 'https' or not link.hostname or link.username is not None:
            continue
        parser = ListingText(); parser.feed(row['description'])
        description = '\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
        if not description:
            continue
        location = str(row.get('candidate_required_location' if provider == 'remotive' else 'location') or '')
        mode = 'remote' if provider == 'remotive' or row.get('remote') is True else ''
        types = {str(value).casefold() for value in row.get('job_types', []) if isinstance(value, str)} if isinstance(row.get('job_types', []), list) else set()
        if not mode:
            mode = 'hybrid' if 'hybrid' in types else 'onsite' if types & {'onsite', 'on-site'} else ''
        output.append({'id': str(row.get('id', row.get('slug', row['url']))), 'title': row['title'][:200], 'company': row['company_name'][:200],
                       'description': description[:30000], 'description_truncated': len(description) > 30000,
                       'source_url': row['url'], 'location': location[:200], 'work_mode': mode,
                       'provider': PROVIDERS[provider][1], 'provider_home': PROVIDERS[provider][3],
                       'publication_date': str(row.get('publication_date', row.get('created_at', ''))),
                       'notes': ['Description normalized from provider HTML; review the original listing before applying.']})
    return output

def company_key(value):
    words = re.findall(r'\w+', value.casefold())
    while words and words[-1] in {'inc', 'llc', 'ltd', 'limited', 'gmbh', 'corp', 'corporation'}:
        words.pop()
    return ' '.join(words)

def location_contains(location, value, country=False):
    groups = [('us', 'usa', 'united states'), ('uk', 'gb', 'united kingdom'), ('de', 'germany', 'deutschland'),
              ('pk', 'pakistan'), ('ca', 'canada'), ('au', 'australia'), ('in', 'india'), ('fr', 'france'), ('es', 'spain')]
    aliases = next((group for group in groups if value.casefold() in group), (value.casefold(),)) if country else (value.casefold(),)
    return any(re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', location.casefold()) for alias in aliases)

def indeed_link(query):
    terms = [query['role']]
    if query.get('company'):
        terms.append('"' + query['company'].replace('"', '') + '"')
    if query.get('work_mode'):
        terms.append(query['work_mode'])
    location = ', '.join(query.get(key, '') for key in ('city', 'country') if query.get(key))
    return 'https://www.indeed.com/jobs?' + urlencode({'q': ' '.join(terms), 'l': location})

class JobDiscovery:
    def __init__(self, cache_root, fetch=fetch_json):
        self.root, self.fetch = Path(cache_root), fetch
        self.locks = {name: threading.Lock() for name in PROVIDERS}
        self.failures = {}

    def provider(self, name):
        with self.locks[name]:
            now = time.time()
            path = self.root / (name + '.json')
            try:
                cached = json.loads(path.read_text(encoding='utf-8')) if path.exists() and path.stat().st_size < 20 * 1024 * 1024 else None
                if cached and 0 <= now - cached['fetched_at'] < 21600:
                    return cached
            except (OSError, ValueError, KeyError):
                pass
            if now - self.failures.get(name, 0) < 60:
                raise ValueError('Provider retry cooldown; try later')
            try:
                jobs = normalize(name, self.fetch(PROVIDERS[name][0]))
                cached = {'fetched_at': now, 'jobs': jobs}
                self.root.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix('.tmp')
                temporary.write_text(json.dumps(cached), encoding='utf-8')
                temporary.replace(path)
                return cached
            except Exception:
                self.failures[name] = now
                raise

    def search(self, query):
        if not query.get('role', '').strip():
            raise ValueError('Enter a job role to search')
        words = re.findall(r'[\w+#]+', query['role'].casefold())
        if not words:
            raise ValueError('Enter a role containing letters or numbers')
        provider = query.get('provider', 'all')
        if provider != 'all' and provider not in PROVIDERS:
            raise ValueError('Unknown provider')
        names = list(PROVIDERS) if provider == 'all' else [provider]
        sources, found = [], []
        def obtain(name):
            try:
                return name, self.provider(name), None
            except Exception:
                return name, None, 'Provider unavailable; no absence-of-jobs claim is made.'
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(obtain, names))
        for name, data, error in results:
            sources.append({'name': PROVIDERS[name][1], 'home': PROVIDERS[name][3], 'coverage': PROVIDERS[name][2],
                            'status': 'unavailable' if error else 'checked', 'fetched_at': data['fetched_at'] if data else None,
                            'records_checked': len(data['jobs']) if data else 0, 'message': error})
            if not data:
                continue
            for original in data['jobs']:
                job = {**original, 'notes': list(original['notes'])}
                text = (job['title'] + ' ' + job['description']).casefold()
                if not all(re.search(r'(?<!\w)' + (r'(?:developer|engineer|development|engineering)' if word in ('developer', 'engineer') else re.escape(word)) + r'(?!\w)', text) for word in words):
                    continue
                if query.get('company') and company_key(query['company']) != company_key(job['company']):
                    continue
                requested = query.get('work_mode', '')
                if requested and job['work_mode'] and requested != job['work_mode']:
                    continue
                if requested and not job['work_mode']:
                    job['notes'].append('Work arrangement is unknown; confirm whether this is onsite or hybrid.')
                location = job['location'].casefold()
                worldwide = job['work_mode'] == 'remote' and location in ('worldwide', 'anywhere', 'global')
                rejected = False
                for field in ('country', 'city'):
                    wanted = query.get(field, '').strip().casefold()
                    if wanted and not location_contains(location, wanted, country=field == 'country'):
                        remote_city = job['work_mode'] == 'remote' and field == 'city' and query.get('country', '').strip() and location_contains(location, query['country'], country=True)
                        city_without_country = field == 'country' and query.get('city', '').strip() and location_contains(location, query['city'])
                        if worldwide or remote_city or city_without_country:
                            job['notes'].append(f'{field.title()} eligibility needs confirmation with the employer.')
                        else:
                            rejected = True
                if not rejected:
                    if job['description_truncated']:
                        job['notes'].append('Description exceeds the comparison limit; review the full listing.')
                    found.append(job)
        unique = {job['source_url']: job for job in found}
        jobs = list(unique.values())[:20]
        errors = any(source['status'] == 'unavailable' for source in sources)
        checked = any(source['status'] == 'checked' for source in sources)
        status = ('found_partial' if errors else 'found') if jobs else 'incomplete' if checked and errors else 'no_matches' if checked else 'source_unavailable'
        return {'status': status, 'jobs': jobs, 'sources': sources, 'indeed_url': indeed_link(query),
                'notice': 'Search covers the fetched provider records, not every vacancy worldwide. No matches does not prove this role/company has no openings. Indeed is a search link, not a fetched source.',
                'message': f'{len(jobs)} candidate listings found; review source and eligibility.' if jobs else 'No matching records in the checked sources.' if status == 'no_matches' else 'Search is incomplete or unavailable; try the Indeed link or paste a listing.'}
