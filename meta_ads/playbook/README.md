# Meta Ads Playbook — how Movement Solutions runs Facebook & Instagram ads

Distilled from *The Facebook Ads Clinic* (Nick Boddington). The full lesson text and cleaned video transcripts are in `../course/`.
Every recommendation must cite a rule ID from these files. If no rule covers a situation, say so and label any suggestion "(not from course)".

**Two layers.** Files 01–06 are the **course layer**: what the course teaches, cited to `../course/` files with lesson title and timestamp. File 07 is the **clinic layer**: the practice's own policy, *not* course content. Wherever it changes a course rule, files 01–06 say so inline as **[Clinic adaptation]** with a `CL-` rule ID. **When a course rule and a CL rule conflict, the CL rule wins.**

| File | Covers | Rule prefixes |
|---|---|---|
| [01-account-setup-and-tracking.md](01-account-setup-and-tracking.md) | Business portfolio, page, ad account, pixel/dataset, events, CAPI, attribution, lead delivery, naming. Ends with **the clinic's actual tracking setup**. | R-SET, R-TRK, R-NAM |
| [02-structure-objectives-budget.md](02-structure-objectives-budget.md) | Campaign → ad set → ad, objective choice, simple vs funnel structure, Advantage+ settings, test vs master campaign, budgets, learning phase, scaling | R-STR, R-OBJ, R-BUD, R-SCL |
| [03-audiences-and-placements.md](03-audiences-and-placements.md) | Broad/Advantage+ audience, local radius & pins, custom audiences, lookalikes, retargeting windows, exclusions, placements | R-AUD, R-LOC, R-RTG, R-PLC |
| [04-lead-forms-pages-follow-up.md](04-lead-forms-pages-follow-up.md) | Offers, instant forms vs landing pages, form settings & questions, completion screen → IntakeQ booking, lead delivery to GoHighLevel, follow-up / no-show sequences | R-OFR, R-FRM, R-LP, R-FU |
| [05-creative-and-copy.md](05-creative-and-copy.md) | Hooks (with **policy-compliant rewrites**), video vs static, UGC/testimonials, local creative, formats, enhancements, copy formula, creative bank | R-HK, R-CR, R-CPY |
| [06-testing-metrics-optimization.md](06-testing-metrics-optimization.md) | One-variable testing, when to judge, moving winners, custom columns & **metrics table**, frequency, uneven spend, review routine | R-TST, R-MET, R-OPT |
| [07-clinic-layer.md](07-clinic-layer.md) | **Clinic adaptations (not course content):** KPIs, Meta's health restrictions, HIPAA, health ad policy, local audience | CL-KPI, CL-RES, CL-HIP, CL-POL, CL-LOC |

Each file follows the same layout: **Principles → Rules (When / Do / Don't / Numbers / Source / Clinic) → Open questions & contradictions** (which default this playbook picked, and why).

## Order of operations for an audit or a new launch

1. **Privacy and tracking first** (01 + 07 CL-HIP). Check the website pixel: which pages, automatic advanced matching, any CAPI, offline events, list uploads or "bypass" tools. Any HIPAA problem (CL-HIP-01…06) is fixed before anything else, even if it costs reported conversions.
2. **Restriction status** (07 CL-RES-01). Does Events Manager show health-and-wellness restrictions? Assume yes unless shown otherwise. Default build is the Leads objective → instant form → optimize for leads (02 R-OBJ-01).
3. **Outcome data path** (07 CL-KPI-03, 04 R-FU). Confirm leads arrive in GoHighLevel tagged with campaign/ad name, follow-up fires within minutes (CL-KPI-02), and booked/showed/new-patient status can be counted per ad. If not, fix this before judging any ad on more than CPL.
4. **Targets.** Set a cost per new patient, cost per booked evaluation and show-rate target (house policy below). No target, no optimization: ask the owner.
5. **Weekly pass** (06 R-OPT-07): spend/CPL/frequency per ad set (CL-LOC-01), then the outcome reconciliation (CL-KPI-03), then decide test winners and losers (06 R-TST-06/07), creative refreshes (05 R-CR-17) and budget steps (02 R-SCL-02).
6. **Monthly pass**: creative bank and the next concepts to test (05), audience/retargeting windows (03), offer and form review (04), funnel structure (02).

## House policy (resolves course contradictions — edit to taste)

| Question (course is inconsistent or silent) | Default used here | Where |
|---|---|---|
| What decides a winner | Cost per new patient → cost per booked evaluation → show rate. CPL is only the early proxy until ≥ 10 booked evaluations or 30 days | 07 CL-KPI-01, 06 R-MET-06 |
| Target cost per new patient / booked evaluation / show rate | **Not set — owner to provide** | 07 §3 |
| Objective & conversion location | Leads → instant form (On your ad) → optimize for leads. No website-event optimization | 02 R-OBJ-01/02, 07 CL-RES-01 |
| Instant form type | Start "More volume". Switch to "Higher intent" only if quality is poor *and* speed to lead is already fast | 04 R-FRM-03, 07 CL-KPI-02 |
| Form questions | Contact details + 1–2 non-clinical qualifiers. Clinical questions go in IntakeQ | 04 R-FRM-07, 07 CL-HIP-03 |
| Pixel | Generic marketing pages only (or none), PageView only, automatic advanced matching **off**, no CAPI patient data, website events off on instant-form ads | 01 clinic setup, 07 CL-HIP-01 |
| List uploads (custom audiences, lookalike seeds, exclusions) | Never | 03 R-AUD-08, 07 CL-HIP-02 |
| "Bypass" for health tracking restrictions | Never | 07 CL-RES-02 |
| Structure | 1 Leads campaign (cold) + 1 small retargeting campaign. A separate test campaign only above ~£/$50 a day | 02 R-STR-03/05/08 |
| Budget type | ABO when several ad sets are tested; otherwise either | 02 R-BUD-04 |
| Budget steps | 10–15% every 2–3 days, and only while results and frequency hold | 02 R-SCL-02, 07 CL-LOC-02 |
| Frequency | 7-day frequency > 2 → prepare new creative. Approaching 3 → rotate | 06 R-OPT-02, 07 CL-LOC-01 |
| Creative enhancements (Advantage+ creative) | All off, including text improvements | 05 R-CR-11 |
| Hooks | Call out the audience/place, never assert the viewer's condition | 05 R-HK-02, 07 CL-POL-01 |
| Testimonials | Only with signed HIPAA marketing authorization. Never write reviews yourself | 05 R-CR-04, 07 CL-HIP-05 |
| Lead routing | Meta → GoHighLevel directly, on a BAA-covered plan. No personal Zapier/Sheets/Gmail routes | 04 R-FU-02, 07 CL-HIP-04 |

## Course lessons the clinic must NOT follow

These are flagged inline as **"Do not follow for the clinic"**. Collected here for quick reference:

- **"Meta Restricts Health Business Tracking (Here's How We Bypass It)"** (`06-learn-with-us.md`). This lesson promises to "bypass" Meta's health-and-wellness restrictions and "feed real conversion data back into Meta". → CL-RES-02.
- **Automatic advanced matching ON** ("Set Up Your Pixel (The Right Way)" [5:04], `01-facebook-ads-masterclass-2026.md`) → CL-HIP-01.
- **Lead / Schedule / CompleteRegistration events on thank-you or booking pages, URL-based custom conversions, CAPI, offline events, CRM sync back to Meta** (Masterclass, Lead Gen and Learn With Us tracking lessons) → CL-HIP-01, CL-RES-01, CL-RES-03.
- **Customer-list custom audiences, lookalike seeds and purchaser exclusions** (Learn With Us audience lessons, eCommerce "Setting Up Audience Segments") → CL-HIP-02.
- **Zapier → Google Sheets / email lead delivery** (Local Businesses "Instantly Receive Your Leads by Email", Lead Gen "Building a Local Campaign") → CL-HIP-04 unless every tool is BAA-covered.
- **Hooks that call out the viewer's symptoms** (course clinic examples) → rewrite per CL-POL-01. **Self-written reviews** (eCommerce) → CL-HIP-05.

## Limits of the source

- **98 of 184 lessons pulled.** Ads Accelerator (33), Canva Starter Pack (20) and Group Q&A Calls (33) are locked for this membership.
- **Transcripts** are cleaned auto-captions from 80 Skool-hosted videos. Expect mis-heard words. Lessons hosted on YouTube have lesson text only. That includes several key ones: the Andromeda structure lessons, "What to do if Meta spends on ONE AD only", "Stop Using the Wrong 'Bait'" and the health-tracking lesson. Rules from those lessons are marked as thin.
- The course is UK-based (£ budgets) and mostly e-commerce / coaching / Skool examples. Its health-clinic examples (a US functional medicine clinic on a 40-mile radius) are the closest analogue.
- **This playbook is not legal advice.** The HIPAA and ad-policy rules in 07 are conservative operating defaults. Confirm them with the practice's compliance contact.
