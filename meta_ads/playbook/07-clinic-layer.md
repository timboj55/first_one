# 07 — Clinic Layer: Movement Solutions Adaptations

**Nothing in this file is course content.** It is the clinic's own policy, layered on top of *The Facebook Ads Clinic*. It covers what the course assumes and the practice can't do (purchase/booking optimization under Meta's health restrictions), what the course recommends and the practice must not do (send patient data to Meta), and how the practice judges results (booked and attended evaluations, not cost per lead).

Files 01–06 mark every place this layer changes a course rule with **[Clinic adaptation]** and a `CL-` rule ID. If a course rule and a CL rule conflict, **the CL rule wins**.

Context:
- Movement Solutions is a physical therapy clinic. It advertises to a local radius around the clinic.
- Lead follow-up runs in **GoHighLevel** (GHL). Scheduling runs in **IntakeQ / PracticeQ**.
- This is operating policy, not legal advice. HIPAA questions (BAAs, authorizations, what counts as PHI on a given page) go to the practice's compliance contact before anything changes.

---

## 1. Principles

1. **A lead is not a patient.** The course mostly scores campaigns on cost per lead (CPL), CTR, hook/hold rate and, for e-commerce, ROAS. The clinic scores them on **cost per booked evaluation**, **show rate** and **cost per new patient**. CPL is an early, cheap proxy, used only until enough bookings exist to judge.
2. **Meta never receives patient data.** No patient identifiers and nothing that reveals a condition goes to Meta through the Pixel, the Conversions API (CAPI), offline events, CRM integrations or audience uploads. Meta does not sign Business Associate Agreements. Where course advice would send such data, the playbook says **"Do not follow for the clinic."**
3. **Assume lower-funnel optimization is unavailable.** Since early 2025 Meta has restricted how health and wellness advertisers share and optimize on lower-funnel website events. The course itself says so (LWU "Meta Restricts Health Business Tracking", lesson text). It then promises a "bypass", which the clinic will not use.
4. **Native instant forms are the default conversion path.** The lead is captured on Facebook/Instagram, so no website pixel event is needed to optimize. This is also the course's own default for local businesses (LOCAL "How to create an Instant Form"; LG "Setting up a Meta Lead Form campaign").
5. **A local audience wears out fast.** A radius around one clinic is a few hundred thousand people at most. Frequency rises and creatives fatigue far sooner than in the national e-commerce accounts most course examples come from. The course says this too, about its own 40-mile-radius clinic client: "surely you're going to get through your audience quickly, well, you are" (MC "Inside the Meta Ecosystem" [8:32]).

---

## 2. Rules

### A. Measurement (CL-KPI)

### CL-KPI-01: Judge campaigns by cost per booked evaluation, show rate and cost per new patient
- When: Every review of a campaign, ad set or ad, including choosing test winners (file 06) and deciding whether to scale (file 02).
- Do: Rank in this order:
  1. **Cost per new patient** = spend ÷ new patients who attended their first visit. This is the deciding number once volume allows.
  2. **Cost per booked evaluation** = spend ÷ leads who booked an evaluation in IntakeQ.
  3. **Show rate** = attended evaluations ÷ booked evaluations.
  4. **Booking rate** = booked ÷ leads, and **contact rate** = leads reached ÷ leads.
  5. **CPL** = spend ÷ leads. This is a diagnostic only.
- Do: Until an ad or ad set has enough bookings to compare (default: **≥ 10 booked evaluations**, or 30 days, whichever comes first), use CPL plus lead-quality notes from the front desk as the provisional signal, and say the call is provisional.
- Don't: Call a winner, or scale, on CPL alone when the cheaper leads book or show worse. A cheap form that books nobody is the most expensive ad in the account.
- Course link: the course itself says CPL is not the whole story. "It's more than just collecting emails… lead quality and follow-up performance" (LG "What does success look like?", lesson text). Its winning-ad breakdown judges a new hook by calls already booked and the old ad by clients closed (5 of 27 leads), not by CPL alone (LWU "Breaking Down a Winning Ad" [2:52], [6:36]). The clinic example reports leads, calls and acquisition cost: "66 leads, 18 calls", "customer acquisition cost of 131 pounds" (MC "Inside the Meta Ecosystem" [8:32]). This rule makes that the default.
- Targets: set in the house-policy table in `README.md` (target cost per new patient, target show rate). Without a target there is no optimization: ask the owner.

### CL-KPI-02: Lead quality and speed to lead
- When: Every lead source; when setting up GHL workflows; when a campaign's booking rate drops.
- Do: Contact new leads fast. Target: **first contact within 5 minutes during clinic hours** (automated SMS/email from GHL immediately, plus a human call). Leads that arrive out of hours get an automated message and a call at opening.
- Do: Track in GHL, per lead source / campaign / ad: time to first contact, contact rate, booking rate. The front desk tags junk and unreachable leads so lead quality can be measured per ad.
- Do: If booking rate falls, check speed to lead and follow-up before blaming the ad.
- Don't: Switch an instant form to "Higher intent" or add qualifying questions before checking whether slow follow-up is the real cause.
- Course link: the course's own follow-up sequence (immediate confirmation, link at +3 min, reconfirmation at +60 min, emails at +1 and +2 days, no-show sequence) is mapped to GHL in file 04 (R-FU rules).

### CL-KPI-03: Data path and weekly reconciliation (outside Meta)
- When: Weekly review; monthly review.
- Do: Keep the attribution chain inside clinic systems:
  - **Meta instant form** → lead delivered to **GHL** (native integration or another HIPAA-eligible connector, CL-HIP-04), tagged with campaign / ad set / ad name.
  - GHL follow-up → evaluation booked in **IntakeQ/PracticeQ**.
  - Attended / no-show / new patient status recorded back in GHL.
- Do: Once a week, export counts by campaign and ad (leads, contacted, booked, attended, new patients) and join them to Meta spend by ad name. Use counts only. No patient names in the reporting sheet. This is why ad naming conventions matter (file 01, R-NAM).
- Don't: Send any of these outcomes back to Meta (see CL-RES-03, CL-HIP-01).
- Note: Ad names travel with the lead into GHL. Keep them free of anything condition-specific. "Knee-pain-hook-v2" is fine as an internal creative label, but don't put a patient-level detail in it.

### B. Meta's health and wellness restrictions (CL-RES)

### CL-RES-01: Assume lower-funnel website optimization and reporting are unavailable; default to Leads with instant forms
- When: Choosing objective and conversion location (file 02), and setting up tracking (file 01). Whenever course advice optimizes for Purchase, Schedule, CompleteRegistration, Add to Cart, a website Lead event or a URL-based custom conversion.
- What changed (general best practice, not from course): from early 2025, Meta classifies some advertisers as health and wellness. For them it restricts lower-funnel events (purchase-type and other "lower-funnel" standard events and custom conversions) from being shared, reported or used for optimization, and filters some URL and parameter data. The exact scope has changed several times. **Check the account's Events Manager and the campaign's optimization options rather than assuming.** The course describes the symptom: "Your campaigns deliver. People click. But Meta shows zero conversion data" (LWU "Meta Restricts Health Business Tracking", lesson text).
- Do: Default build = **Leads objective → Instant form (On your ad) → optimize for Leads**. The conversion happens on Meta, so it does not depend on the website pixel.
- Do: Where a course rule says "optimize for Purchase / website Lead / Schedule", translate it to the instant-form Leads equivalent. Judge the result with CL-KPI-01.
- Do: If a website landing page is ever tested, expect only upper-funnel optimization (e.g. landing page views or link clicks). Compare it to the instant form on cost per booked evaluation, not on Meta-reported results.
- Don't: Rely on course benchmarks built on website conversions (e.g. LP > Purchase %, Complete Registration rates, ROAS) as if they apply here.

### CL-RES-02: Never use a "bypass" for the health restriction
- When: Any time a course lesson, vendor, agency or plugin offers to "unlock", "restore" or "bypass" conversion tracking for health businesses.
- Do: Treat the restriction as a compliance boundary. Work within it with instant forms and CRM-side measurement (CL-RES-01, CL-KPI-03).
- Don't: Follow LWU "Meta Restricts Health Business Tracking (Here's How We Bypass It)". Its lesson text promises a tracking solution "to bypass these restrictions" and "feed real conversion data back into Meta". The tool isn't named in the text and the video is on YouTube (no transcript pulled). Whatever it is, it sends lower-funnel conversion data about people seeking health services to Meta, which conflicts with CL-HIP-01 and with Meta's own policy intent. **Do not adopt it.** If the owner wants it evaluated, that goes to compliance/legal first.

### CL-RES-03: No Conversion Leads / CRM-stage feedback to Meta without legal sign-off
- When: Course or Meta suggests "conversion leads" optimization, offline events, or CRM integrations that send lead stages (booked, showed, became a patient) back to Meta via CAPI.
- Do: Leave it off by default.
- Why: It tells Meta that an identifiable person, matched by lead ID, email or phone, became or tried to become a patient of a physical therapy clinic. That is exactly the data CL-HIP-01 keeps away from Meta.
- Revisit only if: compliance/legal reviews a specific design in writing (what fields, which stage names, whether a BAA-covered intermediary is involved) and approves it.

### C. HIPAA and patient data (CL-HIP)

### CL-HIP-01: Never send patient identifiers or condition-revealing data to Meta through the Pixel or CAPI
- When: Any pixel, dataset, CAPI, Events Manager, partner integration or website change.
- Do:
  - If the pixel runs at all, keep it to **generic marketing pages** (home, about, location, general services overview). Use standard PageView only.
  - **Automatic advanced matching: OFF.**
  - **Manual advanced matching: OFF.**
  - **No CAPI** carrying names, emails, phones, IPs + health context, lead IDs with stage names, or any other patient-level data.
- Don't:
  - Install the pixel on booking, intake, patient-portal, payment or "thank you for booking" pages, or on any page whose URL, title or content reveals a condition (e.g. `/back-pain-treatment`, `/pelvic-floor-booking-confirmed`).
  - Use event names or parameters that reveal a condition or appointment type.
  - Upload offline events.
- Course advice this overrides (do not follow for the clinic):
  - "Turn on all of the automatic advanced matching. This means that anything that's put into your website will get send the data back to meta" (MC "Set Up Your Pixel (The Right Way)" [5:04]).
  - Lead / Schedule / CompleteRegistration events on thank-you and booking pages (MC "Event Codes Made Simple"; LG landing-page lessons).
  - URL-based custom conversions and URL-contains audiences on condition pages.
  - CAPI and offline-event uploads.
- Background (general best practice, not from course): HHS has warned that tracking technologies on pages that relate to an individual's health care can disclose PHI. Courts have narrowed parts of that guidance for unauthenticated pages, but the clinic takes the conservative position because Meta will not sign a BAA.

### CL-HIP-02: No patient or customer list uploads to Meta
- Do: Build audiences from on-Meta signals only: video viewers, Page/Instagram engagers, instant-form openers (file 03).
- Don't: Upload patient or past-client lists (emails, phones) as custom audiences, lookalike seeds or exclusion lists. Even "exclude existing patients" discloses who the patients are.
- Course advice this overrides: customer-list custom audiences and lookalikes (LWU "How to create Custom Audiences", "Lookalike Audiences (LALs) 101"); purchaser exclusions and audience segments built from customer lists (ECOM "Setting Up Audience Segments"; MC audience lessons).

### CL-HIP-03: Instant form questions are contact details plus non-clinical qualifiers only
- Do: Ask for name, phone and email (the course requires email and phone, which is fine), plus non-clinical qualifiers such as preferred location, preferred contact time, or "Are you looking to book in the next 2 weeks?".
- Don't: Ask about diagnosis, injury, condition, symptoms, body part, surgery, medications, insurance details tied to a condition, or date of birth. Meta stores everything typed into an instant form.
- Do: Collect clinical information in **IntakeQ** after booking. That is where it belongs.
- Course advice this adapts: conditional-logic screening questions and longer "friction" forms (LOCAL "Create friction with longer forms"; LG "Instant form - More volume and higher intent"). These are fine in structure, but the questions must be non-clinical.

### CL-HIP-04: Lead routing tools must be HIPAA-eligible with a BAA, or not used
- When: Connecting instant forms to anything (course: Zapier → Google Sheets / email; GoHighLevel).
- Do: Route Meta leads **directly into GHL**, on a HIPAA-eligible GHL plan with a signed BAA (confirm the account's status). Any other tool in the path (Zapier, Google Workspace, email) needs its own BAA and HIPAA-eligible configuration.
- Don't: Use free/personal Zapier, personal Gmail notifications containing lead details, or shared Google Sheets of leads, as some course lessons show (LOCAL "Instantly Receive Your Leads by Email"; LG "Building a Local Campaign").

### CL-HIP-05: Patient testimonials need written HIPAA authorization
- Do: Before any patient's name, face, voice, story or review appears in an ad, get a signed HIPAA marketing authorization. Store it with the creative in the creative bank (file 05).
- Don't: Write reviews or testimonials yourself, or "seed" objection-answering reviews (the e-commerce lesson suggests this; ECOM notes). Don't reuse an organic post that features a patient without authorization.

### CL-HIP-06: Retargeting and website audiences only from generic pages
- Do: Retarget on-Meta engagement (video viewers, Page/IG engagers, form openers who didn't submit) as the default.
- Do: If website audiences are used at all, build them only from generic pages under CL-HIP-01.
- Don't: Build "URL contains" audiences from condition-specific or booking pages. Don't write retargeting copy that implies you know what they looked at ("Still thinking about your knee?"), which is also a CL-POL-01 problem.

### D. Meta ad policy for health (CL-POL)

### CL-POL-01: Call out the audience without asserting their condition
- Background (general best practice, not from course): Meta's personal-attributes policy bans ad text that asserts or implies the viewer has a health condition ("Your back pain…", "Are you suffering from sciatica?"). Detailed targeting by health condition interests has been largely removed, so creative and copy do the targeting.
- Do: Name the place, the activity or the situation, not "you have X". For example:
  - ✗ "Is your knee pain stopping you from running?"
  - ✓ "Runners in [Town]: get a full knee and running assessment with a physical therapist."
  - ✗ "Struggling with your back pain?"
  - ✓ "Back pain treatment in [Town]. Evaluations this week."
- Course link: the course's core hook rule ("call out your ideal customer in the first words", LWU / LG hooks lessons) still applies. It just has to be done in this compliant form. File 05 applies this to every hook and copy rule.

### E. Local audience (CL-LOC)

### CL-LOC-01: Watch frequency and creative fatigue weekly; refresh before results drop
- When: Weekly review of every live ad set.
- Do:
  - Check 7-day and 30-day **frequency** per ad set. Default triggers: **7-day frequency > 2.0** = prepare fresh creative, and **> 3.0**, or CTR down ≥ 30% from that ad's first 2 weeks with CPL rising, = rotate new creative in. The course itself turned an ad off when frequency "went above two" (TEST "Scaling rules" [8:33]), and called frequency of three "not good" (LWU "Paid vs Organic" [3:07]).
  - Keep a **creative bank** (file 05) so new concepts are ready before fatigue, not after.
  - Introduce new concepts (not just new colours) on a steady cadence: default **2–4 new ads per month** per live campaign.
- Don't: Read rising CPL in a local account as a targeting problem first. In a small radius it is usually fatigue.
- Course link: the 40-mile-radius clinic examples show different creative to the same people "because we don't know what it is that it's going to make someone convert" (MC "Inside the Meta Ecosystem" [8:32]). Map-pin openers worked for that client (TEST "How small wins compound over time" [0:57]).

### CL-LOC-02: Size budget to the local audience; scale more slowly than the course's e-commerce examples
- Do: Start inside the course's local range (£/$5–10 a day per local ad set per LOCAL/LG; the clinic case study used about $30 a day test ad sets). Raise budgets in 10–15% steps every 2–3 days, the low end of the course's 10–20% range (file 02, R-SCL-02). Stop raising when frequency rises faster than bookings.
- Do: Treat the radius as fixed by real travel time to the clinic, not stretched to find more audience. Leads who won't travel don't show (CL-KPI-01).
- Don't: Apply the course's scaling examples ($150/day e-commerce, $2,000+/week clinics) without checking audience size and frequency first.

---

## 3. Open questions for the owner

- **Targets:** what are the target cost per new patient, target cost per booked evaluation and acceptable show rate? (Needed for CL-KPI-01. Fill in `README.md`.)
- **GHL BAA:** is the GoHighLevel account on a HIPAA-eligible plan with a signed BAA? (CL-HIP-04.)
- **Current pixel:** is a Meta pixel already installed on the clinic website? If so, which pages, and is automatic advanced matching on? (CL-HIP-01. Audit before any Meta campaign launches.)
- **Health classification:** does Events Manager show the account as restricted (health and wellness)? (CL-RES-01.)
- **Testimonial authorizations:** is there a signed-authorization process for patient stories? (CL-HIP-05.)
