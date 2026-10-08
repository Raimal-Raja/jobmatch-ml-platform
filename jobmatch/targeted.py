"""Compare one chosen listing and prepare evidence-linked interview practice."""
import re
from urllib.parse import urlsplit
from .constraints import VOCABULARY, validate_context

SKILLS = tuple(dict.fromkeys(VOCABULARY + ('Flask', 'TensorFlow', 'NumPy', 'MySQL', 'SQLite',
    'MongoDB', 'Redis', 'Selenium', 'Playwright', 'GitHub Actions', 'algorithms',
    'data structures', 'system design', 'unit testing', 'communication', 'problem solving')))
HEADINGS = {
    'required': 'required', 'requirements': 'required', 'minimum qualifications': 'required',
    'basic qualifications': 'required', 'essential qualifications': 'required',
    'required skills': 'required', 'required qualifications': 'required',
    'preferred': 'preferred', 'preferred qualifications': 'preferred', 'nice to have': 'preferred',
    'desirable': 'preferred', 'bonus': 'preferred', 'qualifications': 'mentioned',
    'responsibilities': 'mentioned', 'what you will do': 'mentioned', "what you'll do": 'mentioned',
    'about us': 'mentioned', 'benefits': 'mentioned', 'about the role': 'mentioned',
}
PRACTICE = {
    'python': ('Explain mutable defaults, iterators and exception handling using small examples.', 'Write a function that validates and deduplicates records; test empty and malformed input.'),
    'sql': ('Explain joins, grouping and indexes, including when an index may not help.', 'Write a grouped query over a small dataset and check duplicate and NULL cases.'),
    'rest apis': ('Explain HTTP methods, status codes, validation and pagination.', 'Design a small API endpoint; describe request validation, error responses and tests.'),
    'docker': ('Explain images, containers, volumes and reproducible builds.', 'Containerize a small application and explain startup configuration and persistence.'),
    'git': ('Explain branches, commits and resolving a merge conflict.', 'Walk through a small change, review its diff and demonstrate a safe conflict resolution.'),
    'unit testing': ('Explain isolated tests, fixtures and choosing meaningful edge cases.', 'Write tests for a small function, including one failure path and a boundary case.'),
    'algorithms': ('Explain time and space complexity for two ways to solve a simple problem.', 'Solve a small search or sorting problem aloud and test boundary cases.'),
    'data structures': ('Compare lists, hash maps and sets for a concrete task.', 'Choose a structure for deduplicating and looking up records; explain complexity and trade-offs.'),
}

def parse_listing(text, extra_skills=()):
    if not isinstance(text, str) or not text.strip() or len(text) > 30000:
        raise ValueError('Paste a job description containing 1–30,000 characters')
    vocabulary = tuple(dict.fromkeys(SKILLS + tuple(extra_skills)))
    heading_pattern = re.compile(r'^\s*(' + '|'.join(re.escape(h) for h in sorted(HEADINGS, key=len, reverse=True)) + r')\s*(?::|$)', re.I)
    kind = 'mentioned'
    items, source_requirements, seen = [], [], set()
    for match in re.finditer(r'[^\n\r]+', text):
        line = match.group()
        heading = heading_pattern.match(line)
        if heading:
            kind = HEADINGS[heading.group(1).lower()]
            if not line[heading.end():].strip():
                continue
        line_kind = kind
        preferred_cue = re.search(r'\b(preferred|nice to have|optional|a plus)\b', line, re.I)
        required_cue = re.search(r'\b(must|required|essential)\b', line, re.I)
        if preferred_cue and (required_cue or heading and kind == 'required'):
            line_kind = 'mentioned'
        elif preferred_cue:
            line_kind = 'preferred'
        elif required_cue and not heading:
            line_kind = 'required'
        if re.search(r'\bnot required\b', line, re.I):
            line_kind = 'mentioned'
        proof = {'source': 'job_description', 'start': match.start(), 'end': match.end(), 'quote': line}
        if line_kind in ('required', 'preferred'):
            source_requirements.append({'kind': line_kind, 'evidence': proof, 'status': 'needs_review'})
        candidates = [(found.start(), found.end(), skill) for skill in vocabulary
                      for found in re.finditer(r'(?<![\w+#])' + re.escape(skill) + r'(?![\w+#])', line, re.I)]
        accepted = []
        for start, end, skill in sorted(candidates, key=lambda item: -(item[1] - item[0])):
            if not any(start < previous_end and end > previous_start for previous_start, previous_end, _ in accepted):
                accepted.append((start, end, skill))
        for _, _, skill in sorted(accepted):
            key = (skill.lower(), line_kind)
            if key not in seen:
                seen.add(key)
                items.append({'skill': skill, 'kind': line_kind, 'evidence': proof})
    return items, source_requirements

def interview_plan(items, minutes):
    ordered = sorted(items, key=lambda item: (item['kind'] != 'required', item['status'] != 'not_evidenced', item['kind'] == 'mentioned'))
    # Repeated mentions across sections do not consume multiple practice priorities.
    priorities, seen = [], set()
    for item in ordered:
        if item['skill'].lower() not in seen:
            priorities.append(item)
            seen.add(item['skill'].lower())
    priorities = priorities[:3]
    questions = []
    for item in priorities:
        skill = item['skill']
        concept, exercise = PRACTICE.get(skill.lower(),
            (f'Explain a core concept in {skill}, when you would use it, and one limitation.',
             f'Work through a small {skill} task aloud, then explain how you would test it.'))
        questions.extend([
            {'topic': skill, 'question': concept,
             'check': 'Define the concept clearly; give an example and explain the trade-off.', 'evidence': item['evidence']},
            {'topic': skill, 'question': exercise,
             'check': 'State assumptions, explain your steps, test edge cases and discuss an improvement.', 'evidence': item['evidence']},
        ])
    blocks = [minutes // 3, minutes // 3, minutes - 2 * (minutes // 3)]
    focus = [item['skill'] for item in priorities]
    days = [
        ('Review the target', ['Read the listing and separate required, preferred and unclear requirements.', 'Check each résumé quotation; record gaps without adding unsupported claims.', 'Choose three practice priorities and collect examples you can honestly discuss.']),
    ]
    for index in range(3):
        topic = focus[index] if index < len(focus) else 'your confirmed experience and the remaining listing requirements'
        days.append((f'Practice {topic}', [f'Review fundamentals for {topic}, using documentation or course notes.', f'Complete a small exercise for {topic}; explain your reasoning aloud.', 'Test your work, record mistakes and prepare a two-minute explanation.']))
    days.extend([
        ('Integrated practice', ['Use the target requirements to scope a small practical task.', 'Implement or walk through the task; test edge cases and explain choices.', 'Prepare a truthful project or employment example with your contribution and limitations.']),
        ('Mock interview', ['Answer the suggested technical questions aloud under a time limit.', 'Practice a project walkthrough and one teamwork/problem-solving example you actually experienced.', 'Score clarity, correctness, evidence and testing; list the weakest answers.']),
        ('Review and rehearse', ['Revisit mistakes and the most important not-evidenced requirements.', 'Repeat a short mock interview and rehearse a concise introduction.', 'Prepare questions about the role and confirm interview logistics with the recruiter.']),
    ])
    agenda_times = [minutes // 10, minutes * 3 // 10, minutes * 3 // 10, minutes * 2 // 10]
    agenda_times.append(minutes - sum(agenda_times))
    agenda = [('Introduction', 'Introduce yourself and explain why this pasted role interests you.'),
              ('Technical discussion', 'Use the evidence-linked practice questions; explain assumptions and trade-offs.'),
              ('Practical exercise', 'Work through a small task for the top priority, narrating your reasoning and tests.'),
              ('Project or employment walkthrough', 'Describe a real contribution from your confirmed experience; distinguish individual work from team work.'),
              ('Questions and feedback', 'Ask about the role, then record weak answers and the next practice action.')]
    return {'notice': 'Suggested practice inferred from the pasted listing, not a prediction of this employer’s actual questions or interview stages. A week of study does not replace required experience.',
            'priorities': priorities, 'questions': questions,
            'mock_interview': [{'stage': stage, 'minutes': duration, 'action': action}
                               for duration, (stage, action) in zip(agenda_times, agenda)],
            'days': [{'day': index + 1, 'focus': title, 'total_minutes': minutes,
                      'tasks': [{'minutes': duration, 'action': action} for duration, action in zip(blocks, actions)]}
                     for index, (title, actions) in enumerate(days)]}

def compare_target(profile, listing, context=None, extra_skills=(), minutes=90):
    if not profile.get('reviewed'):
        raise ValueError('Confirm all profile fields before comparing a target job')
    if type(minutes) is not int or not 15 <= minutes <= 240:
        raise ValueError('Daily preparation time must be 15–240 minutes')
    if len(extra_skills) > 50 or any(not isinstance(s, str) or not s.strip() or len(s) > 80 for s in extra_skills):
        raise ValueError('Supply up to 50 additional skill names, each 1–80 characters')
    source = listing.get('source_url', '')
    if source and (urlsplit(source).scheme not in ('http', 'https') or not urlsplit(source).hostname or urlsplit(source).username is not None):
        raise ValueError('Source link must be an http/https URL without embedded credentials')
    context = validate_context(dict(context or {}))
    confirmed = [item for item in profile['skills'] if item['confirmed']]
    skills, statements = parse_listing(listing['description'], tuple(extra_skills) + tuple(item['value'] for item in confirmed))
    for item in skills:
        proofs = [entry for entry in confirmed if entry['value'].lower() == item['skill'].lower()]
        item.update(status='supported' if proofs else 'not_evidenced', resume_evidence=proofs)
    required = [item for item in skills if item['kind'] == 'required']
    other = []
    for statement in statements:
        quote = statement['evidence']['quote']
        if re.search(r'\b(years?|degree|bachelor|master|phd|authorization|visa|eligible|certification)\b', quote, re.I):
            other.append(statement)
    conflicts = []
    for statement in statements:
        years = re.search(r'\b(\d+)\+?\s*(?:[-–]\s*\d+\s*)?years?\s+(?:of\s+)?(?:(?:relevant|professional|development|work)\s+)?experience\b', statement['evidence']['quote'], re.I)
        if statement['kind'] == 'required' and years and 'experience_years' in context and context['experience_years'] < int(years.group(1)):
            conflicts.append(f"The listing states {years.group(1)} years of experience; you supplied {context['experience_years']}. Study does not replace this requirement.")
    if listing.get('location') and context.get('locations') and listing['location'].lower() not in {s.lower() for s in context['locations']}:
        conflicts.append('The supplied job location is outside your listed locations; check eligibility with the employer.')
    if listing.get('work_mode') and context.get('work_modes') and listing['work_mode'] not in context['work_modes']:
        conflicts.append('The supplied work arrangement differs from your preference.')
    return {'listing': listing, 'skills': skills, 'requirement_statements': statements,
            'other_requirements_to_review': other, 'preference_notes': conflicts,
            'required_skills_supported': sum(item['status'] == 'supported' for item in required),
            'recognized_required_skills': len(required),
            'warnings': ['Not evidenced means absent from your confirmed skills, not proof that you lack the skill.',
                         'Skill extraction uses a limited vocabulary. Review all source requirements and add unfamiliar skill names to compare.',
                         'Mixed required/preferred wording in one line is labelled unclear; review its importance manually.',
                         'Employment duration, degrees, certifications and location eligibility require manual review; they are not inferred.',
                         'Confirm listing metadata against its original source; comparison does not establish current availability or employer identity.'],
            'interview_plan': interview_plan(skills, minutes)}
