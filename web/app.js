const $ = id => document.getElementById(id);
let profileId = null;
let profileReviewed = false;
let rewriteReady = false;
let integrations = {google_jobs: false, nvidia: false};
function el(tag, text, className) { const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; return node; }
async function api(path, options = {}) { const response = await fetch(path, options); const data = await response.json(); if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)); return data; }
function jsonOptions(method, body) { return {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}; }
function showProfile(profile) { document.querySelectorAll('.ai-evidence').forEach(node => node.remove()); $('ai-consent').checked = false; $('ats-panel').hidden = false; $('ats-status').textContent = 'Checking résumé text readiness…'; loadReadiness(profile.id); $('rewrite-editor').hidden = true; rewriteReady = false; profileReviewed = profile.reviewed; $('profile-fields').open = !profile.reviewed; $('target-results').replaceChildren(); $('target-status').textContent = profile.reviewed ? 'Profile confirmed. Add your target listing and compare.' : 'Review and confirm the profile before comparing a target job.'; $('profile-status').textContent = profile.reviewed ? 'Résumé confirmed. Paste your job description in step 2 below.' : 'PDF extracted. Review the fields below, then click Confirm corrected profile.'; profileId = profile.id; sessionStorage.setItem('jobmatch-profile', profileId); $('editor').hidden = false; for (const field of ['skills','experience','education']) $(field).value = [...new Set(profile[field].map(item => item.value))].join('\n'); $('source').textContent = profile.pages.map(page => `Page ${page.page}\n${page.text}`).join('\n\n'); updateReadiness(); }
async function action(button, operation) {
  const label = button.textContent; button.disabled = true; button.textContent = 'Working…';
  try { await operation(); }
  catch (error) {
    const status = button.id === 'configure-services' ? 'setup-status' : button.id === 'compare-target' ? 'target-status' : button.id === 'discover-jobs' ? 'discovery-status' : ['prepare-rewrite','prepare-ai','download-rewrite'].includes(button.id) ? 'rewrite-status' : button.id === 'search' ? 'status' : 'profile-status';
    $(status).textContent = error.message;
  } finally { button.textContent = label; button.disabled = false; updateReadiness(); }
}
function updateReadiness() {
  $('pdf').disabled = Boolean(profileId);
  $('upload').disabled = Boolean(profileId);
  $('prepare-rewrite').disabled = !profileReviewed;
  $('prepare-ai').disabled = !profileReviewed || !integrations.nvidia || !$('ai-consent').checked;
  $('download-rewrite').disabled = !profileReviewed || !rewriteReady || !$('rewrite-reviewed').checked;
  $('compare-target').disabled = !profileReviewed;
  $('search').disabled = profileId ? !profileReviewed : !$('query').value.trim();
}
function selectFlow(name) {
  $('target-flow').hidden = name !== 'target'; $('demo-flow').hidden = name !== 'demo';
  for (const mode of ['target', 'demo']) { const active = mode === name; $('mode-' + mode).classList.toggle('active', active); $('mode-' + mode).setAttribute('aria-pressed', String(active)); }
}
$('mode-target').onclick = () => selectFlow('target');
$('mode-demo').onclick = () => selectFlow('demo');
$('query').addEventListener('input', updateReadiness);
for (const name of ['skills', 'experience', 'education']) $(name).addEventListener('input', () => {
  profileReviewed = false; $('profile-status').textContent = 'You have unsaved edits. Click Confirm corrected profile before comparing.'; updateReadiness();
});
updateReadiness();
$('upload').onclick = () => action($('upload'), async () => { if (profileId) throw new Error('Delete the current stored profile before importing a replacement.'); const file = $('pdf').files[0]; if (!file) throw new Error('Choose a PDF first.'); if (file.size > 10*1024*1024) throw new Error('PDF exceeds 10 MiB.'); $('profile-status').textContent = 'Extracting your PDF…'; showProfile(await api('/profiles',{method:'POST',headers:{'Content-Type':'application/pdf'},body:file})); $('status').textContent = 'Draft extracted. Correct all fields, then confirm the profile.'; });
$('save').onclick = () => action($('save'), async () => { const corrections = {}; for (const field of ['skills','experience','education']) corrections[field] = $(field).value.split('\n').map(v=>v.trim()).filter(Boolean); showProfile(await api(`/profiles/${profileId}`, jsonOptions('PUT',corrections))); $('status').textContent = 'Profile confirmed. Your edits are saved locally.'; });
$('delete').onclick = () => action($('delete'), async () => { await api(`/profiles/${profileId}`,{method:'DELETE'}); profileId = null; profileReviewed = false; sessionStorage.removeItem('jobmatch-profile'); $('editor').hidden = true; $('source').textContent = ''; for (const field of ['skills','experience','education']) $(field).value = ''; $('pdf').value = ''; $('matches').replaceChildren(); $('target-results').replaceChildren(); $('ats-panel').hidden = true; $('ats-results').replaceChildren(); $('rewrite-text').value = ''; $('rewrite-editor').hidden = true; rewriteReady = false; $('target-status').textContent = 'Confirm a profile before comparing a job.'; $('count').textContent = 'Ready when you are'; $('profile-status').textContent = 'Stored résumé and profile deleted. Your original file is unchanged.'; });
$('search').onclick = () => action($('search'), async () => { $('status').textContent = 'Searching the 12 fictional sample jobs… model startup may take up to a minute.'; const context = {}; if ($('years').value !== '') context.experience_years = Number($('years').value); if ($('locations').value.trim()) context.locations = $('locations').value.split(',').map(v=>v.trim()).filter(Boolean); if ($('mode').value) context.work_modes = [$('mode').value]; const data = await api('/search',jsonOptions('POST',{query:$('query').value,profile_id:profileId,approach:$('approach').value,context})); $('matches').replaceChildren(); $('count').textContent = `${data.results.length} matches`; $('status').textContent = 'These are sample-catalog results. Use Compare a job to check a real listing.'; for (const row of data.results) renderMatch(row); });
function renderMatch(row) { const card = el('article','', 'match'); card.append(el('h3',row.job.title),el('p',`${row.job.location} · ${row.job.work_mode}`, 'meta'),el('p',`Ranking signal: ${row.score.toFixed(4)}`, 'score')); for (const conflict of row.assessment.conflicts) card.append(el('p',conflict.message,'conflict')); for (const kind of ['required','preferred']) { card.append(el('h4',`${kind === 'required' ? 'Required' : 'Preferred'} skills`)); const tags=el('div','','tags'); for (const item of row.assessment[kind]) tags.append(el('span',`${item.skill} · ${item.status.replace('_',' ')}`,`pill ${item.status}`)); card.append(tags); }
if (row.assessment.learning_priorities.length) {card.append(el('h4','Focused learning priorities')); const list=el('ul'); for (const item of row.assessment.learning_priorities) list.append(el('li',item.action)); card.append(list);}
const detail=el('details'); detail.append(el('summary','View source evidence')); for(const item of [...row.assessment.required,...row.assessment.preferred]) { detail.append(el('p',`${item.skill} · job quotation`),el('blockquote',item.evidence.quote)); for (const proof of item.resume_evidence || []) detail.append(el('blockquote',proof.evidence ? `Résumé page ${proof.evidence.page}: ${proof.evidence.quote}` : `User-confirmed statement: ${proof.value}`)); } detail.append(el('h4','Full job description'),el('p',row.job.description)); card.append(detail); $('matches').append(card); }
const previousId = sessionStorage.getItem('jobmatch-profile');
if (previousId) api(`/profiles/${previousId}`).then(showProfile).catch(() => sessionStorage.removeItem('jobmatch-profile'));
api('/health').then(health => {
  showIntegrations(health.integrations);
  for (const option of $('approach').options) {
    if (health.search_modes[option.value] === false) {
      option.disabled = true;
      option.textContent += ' · setup required';
    }
  }
}).catch(() => { $('status').textContent = 'Unable to check search availability. Check the local server connection.'; });

function preferences() {
  const context = {};
  if ($('years').value !== '') context.experience_years = Number($('years').value);
  if ($('locations').value.trim()) context.locations = $('locations').value.split(',').map(v => v.trim()).filter(Boolean);
  if ($('mode').value) context.work_modes = [$('mode').value];
  return context;
}
$('compare-target').onclick = () => action($('compare-target'), async () => {
  if (!profileId || !profileReviewed) throw new Error('Complete step 1: review and confirm your résumé.');
  const listing = {title: $('target-title').value.trim(), company: $('target-company').value.trim() || 'Not specified',
    source_url: $('target-url').value.trim(), description: $('target-description').value,
    location: $('target-location').value.trim(), work_mode: $('target-mode').value};
  if (!listing.title) throw new Error('Enter the job role you want.');
  if (!listing.description.trim()) { $('target-status').textContent = 'Finding listings for your role. Choose a result to inspect evidence and your preparation week.'; $('discover-jobs').click(); return; }
  $('target-results').replaceChildren();
  $('target-status').textContent = 'Comparing the pasted listing with your confirmed résumé…';
  const data = await api('/compare-target', jsonOptions('POST', {profile_id: profileId, listing,
    additional_skills: $('target-skills').value.split('\n').map(v => v.trim()).filter(Boolean),
    context: preferences(), minutes_per_day: Number($('target-minutes').value)}));
  renderTarget(data);
  $('target-status').textContent = 'Comparison ready. Review evidence and use the seven-day practice timetable below.';
});
function renderTarget(data) {
  const card = el('article', '', 'match target-comparison');
  card.append(el('h3', `${data.listing.company} · ${data.listing.title}`));
  if (data.listing.source_url) {
    const link = el('a', 'Open original listing'); link.href = data.listing.source_url;
    link.target = '_blank'; link.rel = 'noopener noreferrer'; card.append(link);
  }
  card.append(el('p', `${data.required_skills_supported}/${data.recognized_required_skills} recognized required skills evidenced. This is not a hiring probability.`, 'note'));
  for (const kind of ['required', 'preferred', 'mentioned']) {
    card.append(el('h4', kind === 'mentioned' ? 'Mentioned skills · importance unclear' : `${kind === 'required' ? 'Required' : 'Preferred'} skills`));
    const items = data.skills.filter(item => item.kind === kind);
    if (!items.length) card.append(el('p', 'No recognized skills in this category. Review the full listing.', 'note'));
    for (const item of items) {
      const proof = el('details', '', 'skill-proof');
      proof.append(el('summary', `${item.skill} · ${item.status.replace('_', ' ')}`), el('blockquote', `Job: ${item.evidence.quote}`));
      for (const entry of item.resume_evidence) proof.append(el('blockquote', entry.evidence ? `Résumé page ${entry.evidence.page}: ${entry.evidence.quote}` : `User-confirmed statement: ${entry.value}`));
      if (!item.resume_evidence.length) proof.append(el('p', 'No confirmed skill entry supports this requirement. Correct the profile if you have evidence.', 'note'));
      card.append(proof);
    }
  }
  if (data.other_requirements_to_review.length) {
    card.append(el('h4', 'Experience, education and eligibility · review manually'));
    for (const item of data.other_requirements_to_review) card.append(el('blockquote', item.evidence.quote));
  }
  for (const note of data.preference_notes) card.append(el('p', note, 'conflict'));
  const source = el('details'); source.append(el('summary', 'Review all requirement statements and full job text'));
  for (const item of data.requirement_statements) source.append(el('p', `${item.kind} · needs review`), el('blockquote', item.evidence.quote));
  source.append(el('pre', data.listing.description)); card.append(source);
  for (const warning of data.warnings) card.append(el('p', warning, 'note'));
  $('target-results').append(card);
  const plan = data.interview_plan, preparation = el('section', '', 'panel interview-plan');
  preparation.append(el('h3', 'Your one-week interview preparation'), el('p', plan.notice, 'note'));
  if (plan.priorities.length) {
    preparation.append(el('h4', 'Focused practice priorities'));
    for (const item of plan.priorities) preparation.append(el('p', `${item.skill} · ${item.kind} · ${item.status.replace('_', ' ')}`), el('blockquote', item.evidence.quote));
  }
  preparation.append(el('h4', 'Suggested interview questions'));
  if (!plan.questions.length) preparation.append(el('p', 'Add unfamiliar skill names from the listing to generate more specific practice questions.', 'note'));
  for (const question of plan.questions) {
    const detail = el('details'); detail.append(el('summary', `${question.topic}: ${question.question}`), el('p', question.check), el('blockquote', `Why practice this: ${question.evidence.quote}`)); preparation.append(detail);
  }
  preparation.append(el('h4', 'Suggested mock interview format'));
  const agenda = el('ol');
  for (const stage of plan.mock_interview) agenda.append(el('li', `${stage.minutes} min · ${stage.stage}: ${stage.action}`));
  preparation.append(agenda, el('h4', 'Seven-day timetable'));
  const week = el('div', '', 'week-grid');
  for (const day of plan.days) {
    const section = el('section', '', 'day-card'); section.append(el('h4', `Day ${day.day} · ${day.total_minutes} minutes`), el('p', day.focus));
    const tasks = el('ol'); for (const task of day.tasks) tasks.append(el('li', `${task.minutes} min — ${task.action}`)); section.append(tasks); week.append(section);
  }
  preparation.append(week); $('target-results').append(preparation);
}

async function loadReadiness(id) {
  try {
    const data = await api(`/profiles/${id}/ats-check`);
    if (profileId !== id) return;
    $('ats-status').textContent = data.label;
    $('ats-results').replaceChildren(el('p', `${data.score}/100`, 'readiness-score'), el('p', data.notice, 'note'));
    const checks = el('details'); checks.append(el('summary', 'See how the score is calculated'));
    for (const item of data.checks) checks.append(el('h4', `${item.name} · ${item.points}/${item.maximum}`), el('p', item.detail));
    $('ats-results').append(checks);
    for (const item of data.limitations) $('ats-results').append(el('p', item, 'note'));
  } catch (error) { if (profileId === id) $('ats-status').textContent = `Readiness check unavailable: ${error.message}`; }
}
$('prepare-rewrite').onclick = () => action($('prepare-rewrite'), async () => {
  const draft = await api(`/profiles/${profileId}/rewrite`);
  document.querySelectorAll('.ai-evidence').forEach(node => node.remove());
  $('rewrite-text').value = draft.text; $('rewrite-reviewed').checked = false;
  $('rewrite-editor').hidden = false; rewriteReady = true;
  $('rewrite-status').textContent = `${draft.notice} ${draft.review_items.join(' ')}`;
});
$('rewrite-reviewed').addEventListener('change', updateReadiness);
$('rewrite-text').addEventListener('input', () => { $('rewrite-reviewed').checked = false; updateReadiness(); });
$('download-rewrite').onclick = () => action($('download-rewrite'), async () => {
  if (!$('rewrite-reviewed').checked) throw new Error('Review and confirm the draft before downloading.');
  const response = await fetch(`/profiles/${profileId}/rewrite-export`, jsonOptions('POST', {text: $('rewrite-text').value}));
  if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Export failed'); }
  const address = URL.createObjectURL(await response.blob()), link = el('a');
  link.href = address; link.download = 'ResumeDraft.docx'; document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(address), 30000);
  $('rewrite-status').textContent = 'Word draft downloaded. Review its layout and facts before submitting; ATS acceptance is not guaranteed.';
});
$('discover-jobs').onclick = () => action($('discover-jobs'), async () => {
  const role = $('target-title').value.trim();
  if (!role) throw new Error('Enter the role you want, such as Python Developer.');
  $('discovery-status').textContent = 'Checking permitted job providers… the first request may take up to a minute.';
  $('discovery-results').replaceChildren();
  const data = await api('/discover-jobs', jsonOptions('POST', {role, company: $('target-company').value.trim(),
    country: $('discovery-country').value.trim(), city: $('discovery-city').value.trim(),
    work_mode: $('discovery-mode').value, provider: $('discovery-provider').value, ...(profileReviewed ? {profile_id: profileId} : {})}));
  $('discovery-status').textContent = data.message;
  $('discovery-results').append(el('p', data.notice, 'note'));
  const indeed = el('a', data.google_url ? 'Open this search on Google' : 'Open this role/company/location search on Indeed'); indeed.href = data.google_url || data.indeed_url;
  indeed.target = '_blank'; indeed.rel = 'noopener noreferrer'; $('discovery-results').append(indeed);
  for (const source of data.sources) {
    const link = el('a', `Source: ${source.name} · ${source.status}`); link.href = source.home; link.target = '_blank'; link.rel = 'noopener noreferrer';
    const detail = el('details'); detail.append(el('summary', `${source.name}: ${source.records_checked} records checked`), link,
      el('p', source.coverage), el('p', source.message || `Fetched ${new Date(source.fetched_at * 1000).toLocaleString()}`));
    $('discovery-results').append(detail);
  }
  for (const job of data.jobs) {
    const card = el('article', '', 'discovered-job'); card.append(el('h4', `${job.company} · ${job.title}`),
      el('p', `${job.location || 'Location not specified'} · ${job.work_mode || 'Arrangement unknown'}`, 'note'));
    const source = el('a', `View listing on ${job.provider}`); source.href = job.source_url; source.target = '_blank'; source.rel = 'noopener noreferrer'; card.append(source);
    for (const note of job.notes) card.append(el('p', note, 'note'));
    if (job.match_preview) { card.append(el('p', `Résumé strengths: ${job.match_preview.supported.join(', ') || 'None recognized'}`), el('p', `Skills without résumé evidence: ${job.match_preview.not_evidenced.join(', ') || 'None recognized'}`), el('p', job.match_preview.notice, 'note')); }
    const choose = el('button', 'Use this listing and compare');
    choose.onclick = () => {
      for (const [field, value] of Object.entries({title: job.title, company: job.company, description: job.description,
        url: job.source_url, location: job.location, mode: job.work_mode})) $('target-' + field).value = value;
      $('manual-listing').open = true;
      $('target-results').replaceChildren();
      if (profileReviewed) $('compare-target').click();
      else $('target-status').textContent = 'Listing selected. Upload and confirm your résumé to compare it.';
    };
    card.append(choose); $('discovery-results').append(card);
  }
});

$('ai-consent').addEventListener('change', updateReadiness);
$('prepare-ai').onclick = () => action($('prepare-ai'), async () => {
  if (!$('ai-consent').checked) throw new Error('Confirm sending your résumé to NVIDIA first.');
  $('rewrite-status').textContent = 'Preparing AI suggestions… allow up to a minute.';
  const draft = await api(`/profiles/${profileId}/ai-rewrite`, jsonOptions('POST', {consent: true}));
  $('rewrite-text').value = draft.text; $('rewrite-reviewed').checked = false;
  $('rewrite-editor').hidden = false; rewriteReady = true;
  $('rewrite-status').textContent = `${draft.notice} ${draft.review_items.join(' ')}`;
  const evidence = el('details'); evidence.append(el('summary', 'Review AI paragraph source evidence'));
  for (const row of draft.evidence) evidence.append(el('p', row.text), el('blockquote', row.source_quote));
  document.querySelectorAll('.ai-evidence').forEach(node => node.remove());
  evidence.className = 'ai-evidence'; $('rewrite-editor').append(evidence);
});

function showIntegrations(value) {
  integrations = value || {google_jobs: false, nvidia: false};
  $('integration-status').textContent = `Job search: permitted providers ready. Google Jobs: ${integrations.google_jobs ? 'configured' : 'key needed; permitted-provider fallback available'}. AI writing: ${integrations.nvidia ? 'configured' : 'key needed; local draft available'}.`;
  updateReadiness();
}
$('configure-services').onclick = () => action($('configure-services'), async () => {
  try {
    const result = await api('/integrations', jsonOptions('POST', {nvidia_key: $('nvidia-key').value.trim(), search_key: $('search-key').value.trim()}));
    showIntegrations(result.integrations); $('setup-status').textContent = result.message;
  } finally { $('nvidia-key').value = ''; $('search-key').value = ''; }
});
