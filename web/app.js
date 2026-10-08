const $ = id => document.getElementById(id);
let profileId = null;
function el(tag, text, className) { const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; return node; }
async function api(path, options = {}) { const response = await fetch(path, options); const data = await response.json(); if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)); return data; }
function jsonOptions(method, body) { return {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}; }
function showProfile(profile) { $('target-results').replaceChildren(); $('profile-status').textContent = profile.reviewed ? 'Profile confirmed. Click Find matches to see ranked jobs.' : 'PDF extracted. Review the fields below, then click Confirm corrected profile.'; profileId = profile.id; sessionStorage.setItem('jobmatch-profile', profileId); $('editor').hidden = false; for (const field of ['skills','experience','education']) $(field).value = [...new Set(profile[field].map(item => item.value))].join('\n'); $('source').textContent = profile.pages.map(page => `Page ${page.page}\n${page.text}`).join('\n\n'); }
async function action(button, operation) { button.disabled = true; try { await operation(); } catch (error) { $('status').textContent = error.message; $('profile-status').textContent = error.message; if (button.id === 'compare-target') $('target-status').textContent = error.message; } finally { button.disabled = false; } }
$('upload').onclick = () => action($('upload'), async () => { if (profileId) throw new Error('Delete the current stored profile before importing a replacement.'); const file = $('pdf').files[0]; if (!file) throw new Error('Choose a PDF first.'); if (file.size > 10*1024*1024) throw new Error('PDF exceeds 10 MiB.'); $('profile-status').textContent = 'Extracting your PDF…'; showProfile(await api('/profiles',{method:'POST',headers:{'Content-Type':'application/pdf'},body:file})); $('status').textContent = 'Draft extracted. Correct all fields, then confirm the profile.'; });
$('save').onclick = () => action($('save'), async () => { const corrections = {}; for (const field of ['skills','experience','education']) corrections[field] = $(field).value.split('\n').map(v=>v.trim()).filter(Boolean); showProfile(await api(`/profiles/${profileId}`, jsonOptions('PUT',corrections))); $('status').textContent = 'Profile confirmed. Your edits are saved locally.'; });
$('delete').onclick = () => action($('delete'), async () => { await api(`/profiles/${profileId}`,{method:'DELETE'}); profileId = null; sessionStorage.removeItem('jobmatch-profile'); $('editor').hidden = true; $('source').textContent = ''; for (const field of ['skills','experience','education']) $(field).value = ''; $('pdf').value = ''; $('matches').replaceChildren(); $('target-results').replaceChildren(); $('target-status').textContent = 'Confirm a profile before comparing a job.'; $('count').textContent = 'Ready when you are'; $('status').textContent = 'Stored résumé and profile deleted. Your original file is unchanged.'; });
$('search').onclick = () => action($('search'), async () => { $('status').textContent = 'Searching… first model use may take time to download.'; const context = {}; if ($('years').value !== '') context.experience_years = Number($('years').value); if ($('locations').value.trim()) context.locations = $('locations').value.split(',').map(v=>v.trim()).filter(Boolean); if ($('mode').value) context.work_modes = [$('mode').value]; const data = await api('/search',jsonOptions('POST',{query:$('query').value,profile_id:profileId,approach:$('approach').value,context})); $('matches').replaceChildren(); $('count').textContent = `${data.results.length} matches`; $('status').textContent = data.score_notice; for (const row of data.results) renderMatch(row); });
function renderMatch(row) { const card = el('article','', 'match'); card.append(el('h3',row.job.title),el('p',`${row.job.location} · ${row.job.work_mode}`, 'meta'),el('p',`Ranking signal: ${row.score.toFixed(4)}`, 'score')); for (const conflict of row.assessment.conflicts) card.append(el('p',conflict.message,'conflict')); for (const kind of ['required','preferred']) { card.append(el('h4',`${kind === 'required' ? 'Required' : 'Preferred'} skills`)); const tags=el('div','','tags'); for (const item of row.assessment[kind]) tags.append(el('span',`${item.skill} · ${item.status.replace('_',' ')}`,`pill ${item.status}`)); card.append(tags); }
if (row.assessment.learning_priorities.length) {card.append(el('h4','Focused learning priorities')); const list=el('ul'); for (const item of row.assessment.learning_priorities) list.append(el('li',item.action)); card.append(list);}
const detail=el('details'); detail.append(el('summary','View source evidence')); for(const item of [...row.assessment.required,...row.assessment.preferred]) { detail.append(el('p',`${item.skill} · job quotation`),el('blockquote',item.evidence.quote)); for (const proof of item.resume_evidence || []) detail.append(el('blockquote',proof.evidence ? `Résumé page ${proof.evidence.page}: ${proof.evidence.quote}` : `User-confirmed statement: ${proof.value}`)); } detail.append(el('h4','Full job description'),el('p',row.job.description)); card.append(detail); $('matches').append(card); }
const previousId = sessionStorage.getItem('jobmatch-profile');
if (previousId) api(`/profiles/${previousId}`).then(showProfile).catch(() => sessionStorage.removeItem('jobmatch-profile'));
api('/health').then(health => {
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
  if (!profileId) throw new Error('Upload and confirm your résumé before comparing a job.');
  const listing = {title: $('target-title').value.trim(), company: $('target-company').value.trim(),
    source_url: $('target-url').value.trim(), description: $('target-description').value,
    location: $('target-location').value.trim(), work_mode: $('target-mode').value};
  if (!listing.title || !listing.company || !listing.description.trim()) throw new Error('Enter the job title, company and full job description.');
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
    const link = el('a', 'Source listing · supplied by you'); link.href = data.listing.source_url;
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
