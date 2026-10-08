# Using JobMatch

JobMatch compares your résumé with a job you choose. It shows supporting evidence, requirements to review, and a one-week interview practice plan.

## Compare a real job

1. Open the local app at `http://127.0.0.1:8000/` and keep **Compare a job** selected.
2. Upload a PDF and click **Extract résumé**. Review skills, experience and education, then click **Confirm corrected profile**. If your profile is already confirmed, skip uploading it again. Use **Review or edit extracted information** for corrections.
3. Enter the job title and company, and paste the **full job description** from the listing. A source link alone does not import the description.
4. Click **Compare my résumé with this job**. Results appear below the form.

**Supported** means a confirmed skill entry provides evidence. **Not evidenced** means the confirmed profile does not support that requirement; check whether you should correct your profile or learn the skill. Requirements involving degrees, experience duration, eligibility or unclear wording need your review.

The interview section suggests practice questions, a mock-interview agenda and seven preparation days. Open **Optional preferences and preparation time** to change the default 90 minutes per day. It is a practice plan, not a prediction of the company's actual interview.

## Try the demonstration search

The separate **Try sample-job search** tab searches 12 fictional listings and shows the top five. It does not search Indeed, Google or other live job sites. Enter search terms or use a confirmed profile, then click **Search sample jobs**. Keyword mode starts fastest; model modes can take longer on the first request.

## If a button is disabled or something fails

- Confirm the résumé first. Editing its fields disables comparison until you save and confirm again.
- Supply a title, company and full description for job comparison.
- While a request runs, its button says **Working…**. Errors appear beside the relevant action.
- If the app cannot connect, start the local server using the README instructions and refresh the page.

The résumé is stored locally. **Delete stored résumé & profile** removes its stored copy and clears derived comparisons; your original PDF is unchanged.
