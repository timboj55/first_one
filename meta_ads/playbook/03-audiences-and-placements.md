# 03 — Audiences, Location Targeting & Placements

Distilled from *The Facebook Ads Clinic* (Nick Boddington; course source in `../course/`). Primary sources:
- `01-facebook-ads-masterclass-2026.md` (MC): "Inside the Meta Ecosystem", "Audience Types Explained", "TOF, MOF, BOF: Funnel Explained", "Build an Ecomm Ad", "Build an Lead Gen Ad"
- `04-lead-gen-facebook-ads.md` (LG): "Setting up a Meta Lead Form campaign", "Setting up a Meta Landing page campaign", "What does success look like?", "Building a Local Campaign"
- `07-facebook-ads-for-local-businesses.md` (LOCAL): "Setting Up Your Local Lead Campaign (Step-by-Step)", "Writing Ads That Get Clicks (and Bookings)", "Run proper ads and track real results"
- `06-learn-with-us.md` (LWU): "How to create Custom Audiences", "Lookalike Audiences (LALs) 101", "Unlock Facebooks's Hidden Ad Feature" (Audience Segments), "Breaking Down a Winning Ad", "Budget Basics: Spend Smart", "Campaign Naming Tips", "Paid vs Organic: Key Differences", "Winning Placements in Ads Manager", "Canva Tutorial: Test Hooks That Work", "Creating Thumbnails for Video Ads"
- `05-testing-and-continued-success.md` (TEST): "Why most ads fail", "What to test: Hook, Creative, Audience", "How small wins compound over time", "Scaling rules"
- `03-ecommerce-facebook-ads.md` (ECOM): "Typical eCom funnel structure", "Setting Up Audience Segments", "Catalog Sales vs Manual Campaigns"

**How to read this file**
- Everything is from the course unless tagged.
- Clinic adaptations are marked **[Clinic adaptation]** and point to a CL- rule in `07-clinic-layer.md`.
- Anything else not from the course is tagged **(general best practice, not from course)**.
- Transcripts are auto-captions, so quoted wording may contain mis-hearings ("Vantage Plus" = Advantage+, "ask clinic" = Ads Clinic, "school" = Skool). Mis-hearings are marked [sic].
- Most course demos are national (UK) Skool or consultancy funnels. The closest case to the clinic is a US functional medicine clinic on a 40-mile radius (MC, TEST). Audience-size numbers from national demos do not transfer to a local radius.

---

## 1. Principles

1. **Creative does the targeting now, not the audience.** "How you create the ad now is about how you create an audience." Meta reads the ad, the URL, the landing page and the pixel to decide who sees it (MC "Audience Types Explained" [10:25]). Creative is "the most important thing, not your audience" (MC "Audience Types Explained" [25:53]). "It is all down to copy and creative now rather than the audience level" (LWU "Add Site Links to Your Ads" [1:50]).
2. **Start broad and don't overthink it.** "Just get one going, and if it's the easiest one to do to get going as a Vantage Plus [sic], just get going with the Vantage Plus" (MC "Audience Types Explained" [11:13]). "I find that great results come from just using an open broad audience" (LG "Setting up a Meta Landing page campaign" [3:37]). "We're going broad and we're testing creative and not the audiences" (TEST "Why most ads fail" [1:07]).
3. **Keep audiences big.** Meta has moved broad. An audience that was 2.3M two years ago "would now be 28M" (MC "Inside the Meta Ecosystem" [1:26]). Hyper-targeting and interest stacking "doesn't really work anymore" (ECOM "Understanding product/market fit" [9:51]).
4. **Most small businesses need two campaigns: cold and retargeting.** "I would just actually start thinking about top of funnel, cold outreach and retargeting. That'll be enough for most of you" (MC "TOF, MOF, BOF: Funnel Explained" [3:28]).
5. **A lookalike is a cold audience, not retargeting.** "A look alike is a cold audience... It's not [retargeting]" (MC "Inside the Meta Ecosystem" [5:11]; "Audience Types Explained" [17:45]).
6. **Local geo-targeting still works, but a small radius saturates.** The answer to saturation is more creative variety, not a new audience: "that's why we have to now show the people in the audience different things" (MC "Inside the Meta Ecosystem" [8:32]).
7. **Leave placements open.** "I like to keep it all ticked, guys. The reason why is because I want Facebook to find me leads anywhere" (MC "Build an Lead Gen Ad" [3:27]). "Keep auto placements on, you will get more bang for buck" (LG "Setting up a Meta Lead Form campaign" [8:02]).
8. **Watch frequency.** "We don't want our frequency to go to free [three] because it means that the same people are seeing our ads more and more and more" (LWU "Paid vs Organic" [3:07]).
9. **[Clinic adaptation] Never send patient data to Meta to build audiences.** The course often says "give Meta more data" (customer lists, pixel events, monthly list refreshes). For the clinic, audiences are built only from on-platform engagement and generic website pages. See CL-HIP-01, CL-HIP-02, CL-HIP-06.

---

## 2. Rules

### R-AUD-01: Start cold campaigns on Advantage+ audience (broad)
- When: Any new cold (top-of-funnel) ad set.
- Do: Use Advantage+ audience with no interests, no lookalikes and no exclusions. Add only the location and, if you know it, an age suggestion (see R-AUD-04). Spend your time on creative instead.
- Don't: Spend hours choosing interests. Don't assume a better audience will rescue a weak ad.
- Numbers: None set. A client spending £30-60k/month runs every audience type at once and "all of them get around the same cost of result" (MC "Audience Types Explained" [12:03]).
- Source: MC "Audience Types Explained" [11:13], [12:03]; LG "Setting up a Meta Lead Form campaign" [8:02]; LG "Setting up a Meta Landing page campaign" [3:37]; LWU "Breaking Down a Winning Ad" [3:58]; TEST "Why most ads fail" [1:07]-[2:00]
- Clinic: **[Clinic adaptation]** For the clinic, "broad" means broad *inside the radius*: location + age floor + all genders, no interests. This matches the course's clinic case: "broad audience 30 plus age group men and women, 40 mile radius" (TEST "How small wins compound over time" [0:57]). See R-LOC-01.

### R-AUD-02: Keep audiences large; don't stack interests
- When: Building or editing any cold audience.
- Do: Keep the audience as large as the market allows. If you see a very small estimated size, treat it as a warning sign and widen it.
- Don't: Stack interests with "Define further" (an AND condition), use job titles ("it's not like LinkedIn"), or target celebrity/page-like interests from the pre-2022 era.
- Numbers: In a national UK demo, a stack fell from 30M to 10M to 46,000. Under about 1M was called "weird" ("not even a million, that seems weird"). Preferred national interest audience: 6-7M. Lookalike target size today: 2-5M, versus about 500k "back in the day" (MC "Audience Types Explained" [5:11]-[6:04]; MC "TOF, MOF, BOF" [10:15]; LWU "Lookalike Audiences (LALs) 101" [1:41]).
- Source: MC "Inside the Meta Ecosystem" [1:26]; MC "Audience Types Explained" [2:32]-[6:04]; ECOM "Typical eCom funnel structure" [5:59]; ECOM "Understanding product/market fit" [9:51]
- Clinic: **[Clinic adaptation]** The national size numbers (1M, 2-5M) cannot apply to a single-clinic radius. The whole adult population inside the radius is the ceiling. Don't narrow it further with interests. The size problem in a local radius shows up as frequency and fatigue, not as a small-audience warning (see R-LOC-06, CL-LOC-01).

### R-AUD-03: Use detailed (interest) targeting only as a controlled test
- When: You already have a working broad ad set and want to see whether an interest audience is cheaper.
- Do: Duplicate the winning ad set. Switch to original audience options and add the interest. Keep the same creative and the same budget. After a few days (he waits until after the weekend), keep the cheaper ad set and turn the other off. Use the "relevance" and "size" sorting when picking interests.
- Don't: Change the creative and the audience at the same time. Don't add an audience-test ad set unless you accept the extra spend (2 × £30 = £60/day in his example).
- Numbers: Test ad sets at about £/$30/day each (TEST "What to test" [6:54], [11:09]).
- Source: TEST "What to test: Hook, Creative, Audience" [10:17]-[12:03]; LWU "Campaign Naming Tips" [1:50]-[3:37]; LWU "Budget Basics: Spend Smart" [6:02]-[8:35]; MC "Audience Types Explained" [1:40]-[2:32]
- Clinic: **[Clinic adaptation]** Do not target health-condition interests (for example "back pain", "arthritis", "sciatica"). Meta has largely removed health-interest targeting, and building an audience around a condition conflicts with the personal-attributes policy. If you test interests at all, use lifestyle interests (for example running, golf, gardening). See CL-POL-01.

### R-AUD-04: Set only a plausible age floor; keep the top and gender open
- When: Setting demographics on any ad set.
- Do: Add a minimum age only if you know your buyers. Keep the upper limit open if any customers are older. Keep both genders. In Advantage+ audience, enter the age as a suggestion. Put the age in the ad set name.
- Don't: Cap the top age because you "doubt" older people buy. In the lead build he set 28-60, then reversed it: "I'm gonna go 65. Yeah, I'm just gonna keep it open" (MC "Build an Lead Gen Ad" [2:36]).
- Numbers: Examples: 28-65 (MC lead build), 28-60 (LG landing page build), 30+ (MC e-com build), 30+ men and women (clinic case, TEST).
- Source: MC "Build an Lead Gen Ad" [2:36]; MC "Build an Ecomm Ad" [3:43]; LG "Setting up a Meta Landing page campaign" [3:37]; LOCAL "Setting Up Your Local Lead Campaign" [2:26]; TEST "How small wins compound over time" [0:57]
- Clinic: **[Clinic adaptation]** Default: age 25+ (or the clinic's real patient floor), no upper limit, all genders. Health/PT is not a Special Ad Category, so age is not forced to 18+ (LG "Setting up a Meta Lead Form campaign" [2:19]). The 25+ floor is a clinic choice, not a course number.

### R-AUD-05: Let the creative's call-out pick the audience
- When: Writing hooks for a broad audience.
- Do: Name who the ad is for in the first words, so the right people self-select. "Meta isn't learning from you calling out your ideal customer" (LWU "Breaking Down a Winning Ad" [0:00]). If lead cost is high or quality is poor, check whether the call-out is too niche; broaden it slightly (LWU "Breaking Down a Winning Ad" [8:54]).
- Don't: Rely on targeting settings to do what the hook should do.
- Numbers: Changing "Ex-pats parents" to "Parents" cut cost per lead from 14.99 to £6 (LWU "Breaking Down a Winning Ad" [5:48]-[6:36]).
- Source: LWU "Breaking Down a Winning Ad" [0:00], [5:48]-[8:54]; ECOM "Typical eCom funnel structure" [5:59]-[6:51]; LWU "Paid vs Organic" [5:38]
- Clinic: **[Clinic adaptation]** Call out the audience without asserting the viewer's condition. "Runners in South Portland who want to get back to race day" is fine. "Your back pain..." or "Do you have arthritis?" is not. See CL-POL-01. Creative detail lives in the creative playbook file.

### R-AUD-06: Build warm custom audiences from Meta-native engagement first
- When: Building audiences for retargeting, exclusion or lookalike seeds.
- Do: Create custom audiences from on-platform sources: video viewers, Facebook page engagers, Instagram engagers (anyone who engaged, engaged with an ad, or saved), and lead-form openers or submitters. Name each audience plainly so you can find it in the ad set (for example "Video 3s 90d", "Lead form opened not submitted 90d"). Pick the correct page and the correct pixel; old or agency assets can appear in the list.
- Don't: Panic when a new audience shows "fewer than 1,000". It can take up to about 24 hours to fill.
- Numbers: Video threshold: 3-second viewers or 25-50% viewers, so you don't lose fence-sitters. Retention 30/60/90 days. Video audiences can go to 365 days (LWU "How to create Custom Audiences" [3:57]-[5:47]; MC "Audience Types Explained" [14:30], [20:55]).
- Source: LWU "How to create Custom Audiences" [0:00]-[7:39]; MC "Audience Types Explained" [13:42]-[14:30], [20:55]
- Clinic: **[Clinic adaptation]** These are the preferred audience sources for the clinic because no patient data leaves the clinic. Two limits: lead-form audiences reveal interest in whatever the form is about, so keep forms and ad names condition-neutral (CL-HIP-03); and treat these as Meta-side data only, never merged with CRM or patient data (CL-HIP-01).

### R-AUD-07: Build website custom audiences only from generic pages
- When: You want to retarget or exclude website visitors.
- Do (course): Audiences > Create custom audience > Website > choose pixel > "All website visitors" or "People who visited specific web pages" > URL **contains** (more reliable than "equals") > retention > name it.
- Don't: Build the audience with exclusions baked in; keep it clean so it can be reused, and do exclusions at ad set level (MC "TOF, MOF, BOF" [14:14]).
- Numbers: Retention 1-180 days. 30-90 days "works really well, mainly because they're still in that buying cycle" (LWU "How to create Custom Audiences" [1:25]). MC demo used 180 days, "but really... last 30" (MC "TOF, MOF, BOF" [13:24]-[14:14]).
- Source: MC "TOF, MOF, BOF: Funnel Explained" [13:24]-[15:05]; LWU "How to create Custom Audiences" [1:25]
- Clinic: **[Clinic adaptation]** Pixel-based audience: CL-HIP-06 and CL-HIP-01 apply. Only build from generic pages (home, about, team, location, general pricing). Never from condition-specific pages (for example /sciatica, /pelvic-floor), booking, intake or thank-you pages. The course's event-based versions (add-to-cart, SubmitApplication, CompleteRegistration, "started booking but didn't book") are **not to be followed for the clinic**: they are either condition/booking-revealing (CL-HIP-06) or rely on lower-funnel events that may be restricted (CL-RES-01). Do not use any "bypass" to restore them (CL-RES-02).

### R-AUD-08: Do not upload customer lists
- When: The course suggests uploading a CSV of customers (email, first name, last name, phone) to exclude members, seed lookalikes, or fill Audience Segments, and refreshing it monthly.
- Do (course): Audiences > Create audience > Custom audience > Customer list > upload CSV > map columns. Refresh monthly with "any new business".
- Don't: N/A in the course.
- Source: MC "TOF, MOF, BOF: Funnel Explained" [15:05]-[17:27]; LWU "Unlock Facebooks's Hidden Ad Feature" [7:58]-[8:50]; LWU "How to create Custom Audiences" (lesson text: "email lists")
- Clinic: **[Clinic adaptation]** **Do not follow for the clinic.** Uploading patient or lead lists to Meta discloses who is a patient. No list uploads for custom audiences, lookalike seeds or exclusions. See CL-HIP-02. Use on-platform lead-form audiences instead (R-AUD-06, R-AUD-12).

### R-AUD-09: Treat lookalikes as cold audiences built from a strong seed
- When: You have enough source events (the course says about 300-400) and want another cold audience to test against broad.
- Do: Build the custom audience first; every lookalike needs one. Seed from your best signal: lead-form **submitters**, not openers, with the longest available retention. Create the lookalike from the custom audience's panel (there is a bug where the source isn't pre-selected; search it by name). If you build one, use 5%. With more budget you can build up to 6 bands at once and split-test them. Remove the seed audience from the ad set's inclusions so you go cold. Leaving "Advantage+ lookalike" (expand beyond lookalike) on is fine; test it.
- Don't: Use a lookalike as retargeting. Don't layer interests onto it ("I want to keep my audience large").
- Numbers: Seed 300-400 users or events. Size 1-10%. 1% was the old standard; "5% is really good. 6% is all really good now"; he has also seen "really good results on 10%". UK lookalike steps are about 550k per 1%. New accounts can seed from page views or link clicks.
- Source: MC "Inside the Meta Ecosystem" [5:11]-[6:13]; MC "Audience Types Explained" [12:03]-[21:42]; LWU "Lookalike Audiences (LALs) 101" [0:00]-[3:19]
- Clinic: **[Clinic adaptation]** Seed only from on-platform lead-form submitters (R-AUD-06). Never from an uploaded patient or CRM list (CL-HIP-02) and never from pixel audiences of booking or condition pages (CL-HIP-06). Inside a 40-mile radius, a lookalike is just a slice of the same local population, so expect little gain over broad; it is a low-priority test. Meta may also limit lookalike options for some health advertisers; check what the account allows **(general best practice, not from course)**.

### R-AUD-10: Audience Segments: use lead-form data only, or skip
- When: The course recommends filling Advertising settings > Audience segments ("Engaged audience" and "Existing customers"), even for lead gen, and then using Breakdown > Audience segments to see how much spend reaches new vs existing people.
- Do (course): Engaged = leads, SubmitApplication and CompleteRegistration website audiences at 180 days. Existing customers = buyers (from an uploaded list) or leads.
- Don't: N/A in the course.
- Numbers: 180-day website audiences; monthly list refresh. His claimed improvement is anecdotal (spend was cut from about 250 to 100/day at the same time).
- Source: LWU "Unlock Facebooks's Hidden Ad Feature" [2:30]-[8:50]; ECOM "Setting Up Audience Segments" [0:00]-[2:41]
- Clinic: **[Clinic adaptation]** **Do not follow the list-upload or website-event parts for the clinic** (CL-HIP-02, CL-HIP-06, CL-RES-01). If you want the reporting breakdown, the only acceptable input is an on-platform lead-form submitters audience as "Engaged audience". Leave "Existing customers" empty. Measure whether ads reach existing patients outside Meta (CL-KPI-03).

### R-AUD-11: Test audiences one variable at a time
- When: Comparing any two audiences.
- Do: Duplicate the ad set and change only the audience. Same creative, same copy, same budget, same destination. Name each ad set after the audience actually set (not defaults like "male and female").
- Don't: Change several things at once: "I've got three different things that have changed and there would just be no point" (LG "What does success look like?" [1:30]).
- Source: LG "What does success look like?" [1:30]; LWU "Campaign Naming Tips" [0:00]-[3:37]; TEST "One variable at a time" [0:00]
- Clinic: **[Clinic adaptation]** Judge the winner on cost per booked evaluation and show rate, not CPL alone (CL-KPI-01). Local audience tests need longer to read because volumes are small.

### R-AUD-12: Exclude people who already converted, at ad set level
- When: Cold campaigns and retargeting campaigns.
- Do: Exclude converters at the ad set (switch to original audience options > Add exclusions > custom audience). Cold ad sets can also exclude recent website visitors.
- Don't: Bake exclusions into the source audience; keep it clean for reuse.
- Numbers: TOF exclusion window stated as "108 days" [sic, likely 180] (MC "TOF, MOF, BOF" [0:45]). ECOM excludes "Purchase 180 days".
- Source: MC "TOF, MOF, BOF: Funnel Explained" [0:45], [14:14]-[17:27]; ECOM "Setting Up Audience Segments" [1:37]-[2:41]
- Clinic: **[Clinic adaptation]** Exclude converters with the on-platform "lead form submitted" audience only. Do not exclude with an uploaded patient list (CL-HIP-02) or a booking/thank-you page pixel audience (CL-HIP-06). Some overlap with existing patients is accepted.

### R-LOC-01: Replace the country with the clinic's town or postcode and a radius
- When: Every local ad set.
- Do: Audience controls > Locations > Edit. Remove the default country. Type the postcode, county or town and set the radius. Press Return after setting the radius: "If you don't press return, it doesn't set it" (MC "Audience Types Explained" [23:18]).
- Don't: Leave the whole country on for a local business.
- Numbers: A typed location defaults to 40 km and allows 17-80 km (LOCAL "Setting Up Your Local Lead Campaign" [1:38]). Course intro: local businesses typically reach a "20, 40 mile radius" (LOCAL "Writing Ads That Get Clicks" [0:00]). The clinic examples run a 40-mile radius (MC "Audience Types Explained" [22:31]; TEST "How small wins compound over time" [0:57]).
- Source: LOCAL "Setting Up Your Local Lead Campaign" [1:38]-[2:26]; LG "Building a Local Campaign" [1:38]-[2:26]; MC "Audience Types Explained" [22:31]-[23:18]
- Clinic: **[Clinic adaptation]** Set the radius to how far patients will actually drive for repeat visits, not the widest possible. Mind that 80 km is about 50 miles, so a 40-mile radius is close to the top of the UI range.

### R-LOC-02: Use Drop Pin for a tighter radius or when typing fails
- When: You need less than 17 km, or the town search doesn't find the place.
- Do: Zoom the map to the area first, click Drop pin, place it, then set the radius.
- Numbers: Pin radius 1-80 km. Example 10 km (LOCAL "Setting Up Your Local Lead Campaign" [2:26]-[3:15]).
- Source: LOCAL "Setting Up Your Local Lead Campaign" [2:26]-[3:15]; MC "Audience Types Explained" [23:18]
- Clinic: Pin the clinic's street address so the radius is centred on the building.

### R-LOC-03: Exclude areas you can't serve or that don't match the hook
- When: Part of the radius is out of reach (across water, a long drive) or your creative names a town that doesn't fit.
- Do: Switch "Include" to "Exclude", then type a location or drop a pin (it shows red). You can add several includes and excludes.
- Numbers: About 20 pins or locations per ad set ("I believe") (LOCAL "Setting Up Your Local Lead Campaign" [3:15]-[4:04]).
- Source: LOCAL "Setting Up Your Local Lead Campaign" [3:15]-[4:04]

### R-LOC-04: One ad set per radius or town; name it by location and radius
- When: Testing different radii or towns.
- Do: Put each in its own clearly named ad set (for example "Wadebridge 40km"). Name the campaign with stage + goal + area (for example "TOF - Lead generation - Wadebridge").
- Source: LOCAL "Setting Up Your Local Lead Campaign" [0:00], [2:26]; LG "Building a Local Campaign" [0:00]
- Clinic: **[Clinic adaptation]** With a small budget, do not split the radius into many ad sets; each one needs enough spend to learn. Size budget to the local audience (CL-LOC-02).

### R-LOC-05: Keep local budgets small and fight saturation with creative, not audience changes
- When: Setting and scaling budget for a local radius.
- Do: Start small so you don't burn through a small audience. When spend grows, show the same people many different creatives, hooks and offers.
- Don't: Change the audience to escape saturation.
- Numbers: £5-10/day per local ad set: "you don't want to go too high and saturate your audience too quickly" (LOCAL "Setting Up Your Local Lead Campaign" [0:49]). The 40-mile clinic spent about $2,000/week: "surely you're going to get through your audience quickly, well, you are" (MC "Inside the Meta Ecosystem" [8:32]).
- Source: LOCAL "Setting Up Your Local Lead Campaign" [0:49]; LG "Building a Local Campaign" [0:49]; MC "Inside the Meta Ecosystem" [6:13], [8:32]
- Clinic: **[Clinic adaptation]** Scale slower than e-commerce advice and size budget to the radius (CL-LOC-02). Keep a creative bank and refresh on fatigue signals (CL-LOC-01).

### R-LOC-06: Watch frequency weekly in a local radius
- When: Every weekly review of local cold and retargeting ad sets.
- Do: Add Frequency, Reach and Impressions columns (frequency = impressions ÷ reach). When frequency climbs, rotate in new creative. He turned an ad off "because my frequency went above two" (TEST "Scaling rules" [8:33]).
- Don't: Let frequency reach 3: "we don't want our frequency to go to free [three]... if they're not biting now, when are they going to buy it if ever? So your results are going to go increased in price" (LWU "Paid vs Organic" [3:07]-[4:35]).
- Numbers: Act above 2; 3 is too high. Example: $30/day, after about 2 weeks, 10k reach and 30k impressions = frequency 3. The course gives no time window for the frequency figure.
- Source: TEST "Scaling rules" [8:33]; LWU "Paid vs Organic" [3:07]-[4:35]; TEST "Custom columns - Ecomm" [1:31]
- Clinic: **[Clinic adaptation]** A 40-mile radius hits these levels faster than the national demos. Check frequency together with CTR and cost per booked evaluation every week, and treat a rising frequency plus falling CTR as the fatigue signal to refresh creative (CL-LOC-01).

### R-LOC-07: Name the location in the creative
- When: Any local ad.
- Do: Call out the town in the first 2-3 seconds of video, in statics and in the copy. A map-pin opening "works really, really well" (TEST "How small wins compound over time" [3:56]). Viewers in "South Portland, Maine" feel the ad "is halfway to being for me" (MC "Audience Types Explained" [23:18]).
- Numbers: Location on screen for 2-3 seconds (LOCAL "Visual is what stops the scroll!" [0:00]-[1:02]).
- Source: MC "Audience Types Explained" [23:18]; TEST "How small wins compound over time" [3:56]; LG "Local Creative that converts" [0:00]-[3:00]; LOCAL "Visual is what stops the scroll!" [1:02]
- Clinic: If you exclude a town (R-LOC-03), don't name it in the creative.

### R-RTG-01: Run one cold campaign and one retargeting campaign; both on the Leads objective
- When: Account structure for a small business.
- Do: Cold (TOF) campaign plus a retargeting campaign. The retargeting campaign still uses the conversion objective (Leads), not Awareness or Traffic. Full TOF/MOF/BOF is only for big budgets or high site traffic.
- Source: MC "TOF, MOF, BOF: Funnel Explained" [1:43]-[3:28], [11:51]-[12:38]; MC "Why you don't always need TOF-MOF-BOF" (lesson text); ECOM "Typical eCom funnel structure" [12:04]-[12:54]; TEST "How small wins compound over time" [9:06]-[10:20]
- Clinic: **[Clinic adaptation]** Retargeting should use the Leads objective with an instant form, not a website conversion event, because lower-funnel website events may be unavailable (CL-RES-01). Retargeting may not be worth running until warm pools are big enough; see R-RTG-03.

### R-RTG-02: Build retargeting from engagement audiences, using a 7-day stack
- When: Setting the retargeting audience.
- Do: Combine audiences of people who took a meaningful action in the last 7 days ("seven day stack"): video viewers, Facebook/Instagram engagers, lead-form openers who didn't submit, and website visitors. Retarget them while they're warm. The clinic case ran a "middle of funnel, seven day stack" with about 5 videos and statics per ad set.
- Numbers: 7-day window; video viewers at 50%+ in the ECOM stack. Clinic case: MOF stack at 100/day; best retargeting ad at $14 per lead; account about $17 CPL (TEST "How small wins compound over time" [9:06]-[10:20]).
- Source: ECOM "Typical eCom funnel structure" [9:29]-[10:22]; TEST "How small wins compound over time" [9:06]-[10:20]; LWU "How to create Custom Audiences" [5:47]
- Clinic: **[Clinic adaptation]** Build the stack from on-platform audiences only (video, page, Instagram, lead-form opened-not-submitted). Add website visitors only from generic pages (CL-HIP-06). Leave out any add-to-cart, booking-start or condition-page audiences (CL-HIP-06, CL-RES-01).

### R-RTG-03: Choose retention windows by source and pool size
- When: Setting retention on retargeting audiences.
- Do: Use 30-90 days for website audiences and 30/60/90 days for video audiences. Use 7 days for the warm stack. Widen the window when the pool is too small, or frequency will explode.
- Numbers: Website: 1-180 days possible; 30-90 recommended (LWU "How to create Custom Audiences" [1:25]). Video: 30/60/90 (LWU [4:50]); up to 365 possible (MC "Audience Types Explained" [14:30]). Lead form: the default changed from 180 to 90 (MC "Audience Types Explained" [14:30]). MC retargeting demo: 180 days, "really... last 30" (MC "TOF, MOF, BOF" [14:14]). ECOM catalog retargeting widened to 60 days for volume (ECOM "Catalog Sales vs Manual Campaigns" [10:33]-[12:30], e-commerce).
- Source: as listed
- Clinic: **[Clinic adaptation]** Default: 7-day stack for engagement plus a 30-day video/page/lead-form audience; widen to 60-90 days if the pool is too small to spend the budget without frequency going above 2 (R-LOC-06, CL-LOC-01). Website windows only on generic pages (CL-HIP-06).

### R-RTG-04: Keep retargeting budgets small to control frequency
- When: Setting the retargeting budget.
- Do: Start retargeting at a low daily budget while the audience builds.
- Numbers: "Like a fiver" (about £5/day) (MC "TOF, MOF, BOF" [12:38]). "I did retargeting five... if I was to put it more, it means that my retargeting would go into a higher frequency and not work as well" (LWU "Budget Basics: Spend Smart" [3:34]). The clinic case later ran its MOF stack at 100/day on a much larger account (TEST "How small wins compound over time" [10:20]).
- Source: MC "TOF, MOF, BOF: Funnel Explained" [12:38]; LWU "Budget Basics: Spend Smart" [0:00], [3:34]; TEST "How small wins compound over time" [10:20]
- Clinic: **[Clinic adaptation]** Start at the low end and raise only while retargeting frequency stays under 2 (R-LOC-06, CL-LOC-01). Judge retargeting by booked evaluations, not CPL (CL-KPI-01).

### R-RTG-05: Retargeting creative reminds; it does not say "we saw you"
- When: Writing retargeting ads.
- Do: Remind fence-sitters of the value, and use social proof, reviews and availability ("hey, you were on the fence...") (MC "TOF, MOF, BOF" [11:04]; ECOM "Typical eCom funnel structure" [11:14]).
- Don't: Personalise with "Hey, we saw you looking at [product]" for the clinic (ECOM "Catalog Sales vs Manual Campaigns" [16:40]-[18:40] is e-commerce).
- Clinic: **[Clinic adaptation]** "We saw you looking at [condition] treatment" implies knowledge of a health interest and breaks the personal-attributes policy (CL-POL-01). Testimonials need written HIPAA authorization (CL-HIP-05).

### R-RTG-06: Exclude people who already converted from retargeting
- When: Every retargeting ad set.
- Do: Exclude converters at ad set level so you don't pay to re-reach them.
- Source: MC "TOF, MOF, BOF: Funnel Explained" [15:05]-[17:27]
- Clinic: **[Clinic adaptation]** The course does this with an uploaded member list: **do not follow for the clinic** (CL-HIP-02). Exclude the on-platform "lead form submitted" audience instead (R-AUD-12).

### R-PLC-01: Keep Advantage+ (automatic) placements on Facebook and Instagram
- When: Every ad set.
- Do: Leave Advantage+ placements on, covering Facebook and Instagram. Leave the inventory filter on "expanded". Manual placements are under More options > Advanced placements if you ever need them.
- Don't: Trim placements by habit. "If someone's in marketplace looking at a new car, and Facebook thinks..." they're a lead, let it show the ad there (MC "Build an Lead Gen Ad" [3:27]-[4:19]).
- Source: MC "Build an Lead Gen Ad" [3:27]-[4:19]; MC "Build an Ecomm Ad" [4:36]; MC "Inside the Meta Ecosystem" [1:26]; LG "Setting up a Meta Lead Form campaign" [8:02]; LG "Setting up a Meta Landing page campaign" [9:29]; ECOM "Catalog Sales vs Manual Campaigns" [12:30]; LOCAL "Run proper ads and track real results" [8:58]
- Clinic: Applies as written.

### R-PLC-02: Make creative fit all placements; restrict only when it can't
- When: Building creative and checking the ad before publishing.
- Do: Keep key text inside safe zones so it isn't cut off in vertical (Stories/Reels) or square feed crops. Keep media in original aspect ratios. Check the preview in each placement. When setting a custom video thumbnail, edit each placement group so the first frame matches.
- Don't: Restrict placements unless the creative can't be adapted. Then, for example, limit a vertical video with text too high or low to Reels and Stories (LG "Setting up a Meta Lead Form campaign" [8:02]).
- Source: LG "Setting up a Meta Lead Form campaign" [8:02]; MC "Build an Ecomm Ad" [7:44], [12:27]; LWU "Canva Tutorial: Test Hooks That Work" [0:00]; LWU "Creating Thumbnails for Video Ads" [0:00]; WELCOME "Canva - Design all you ads in here!" [0:00]-[2:43]
- Clinic: Applies as written. The course is thin on placements: the "Winning Placements in Ads Manager" lesson text promises a Stories/Reels/Feed breakdown, but its transcript is a custom-columns walkthrough with no placement advice. If you want to check placement results, use Breakdown > By Delivery > Placement and judge on downstream bookings **(general best practice, not from course)**.

---

## 3. Open questions / contradictions in the course

1. **Creative or audience: which is "make or break"?** MC "Objectives" [0:00] says the objective choice decides success; MC "Audience Types" [25:53] says creative is "the most important thing, not your audience"; several LWU lessons invest heavily in custom audiences, lookalikes and segments. **Default:** broad audience, effort on creative (R-AUD-01, R-AUD-05).
2. **Interest targeting: dead or still used?** ECOM says hyper-targeting "doesn't really work anymore" but "I still use it in lots of various accounts" ([5:59]). TEST's lesson is titled "Hook, Creative, Audience" and demos an interest test, while the video says "I forget about the audiences." **Default:** broad first; interest only as a single-variable test, never health conditions (R-AUD-03, CL-POL-01).
3. **Advantage+ audience vs original audience options.** LG and LWU "Breaking Down a Winning Ad" use Advantage+; MC "Audience Types" [20:07] and MC "TOF, MOF, BOF" prefer "switch to original"; LWU "Custom Audiences" [6:41] says to ignore the Advantage+ prompt. **Default:** Advantage+ for cold; original options only when you must add a custom audience or exclusion.
4. **Lookalike size.** 1% was the standard; "really good results on 10%"; built at 5%; "5% is really good. 6% is all really good now"; 1% "doesn't work as well now" and "still works well" in the same breath. Target size 2-5M is a national benchmark. **Default:** one 5% lookalike from lead-form submitters, low priority for a local radius (R-AUD-09).
5. **Retention windows.** MC: "all the way back to 180 days", then "it's now 90"; retargeting at 180 "but really... last 30"; LWU: website 30-90 recommended, yet Audience Segments built at 180; ECOM: 7-day stack. **Default:** 7-day stack plus 30-day engagement audiences, widened to 60-90 for small pools (R-RTG-03).
6. **Frequency threshold.** TEST turned an ad off above 2; LWU says don't let it reach 3. No time window is given for either. **Default:** review and refresh creative above 2; treat 3 as a hard limit (R-LOC-06).
7. **Radius.** LOCAL intro says "20, 40 mile radius"; the LOCAL demo uses 40 km (about 25 miles); the clinic cases use 40 miles (about 64 km), close to the 80 km UI maximum. **Default:** the clinic's realistic repeat-visit drive time (R-LOC-01).
8. **Retargeting budget.** "Like a fiver" and "£5 is a little bit too little" (for prospecting) vs the clinic case's MOF stack at 100/day; MC's summary "running at 20 a day" refers to TOF. **Default:** start retargeting low and scale only while frequency stays under 2 (R-RTG-04).
9. **"Feed Meta more data" vs clinic privacy.** LWU Audience Segments and MC retargeting rely on customer-list uploads, monthly refreshes and pixel events (Lead, SubmitApplication, CompleteRegistration). LWU's final lesson says these signals are blocked for health advertisers and offers an unnamed "bypass." **Default:** no list uploads (CL-HIP-02), pixel audiences only from generic pages (CL-HIP-06), no bypass (CL-RES-02).
10. **Keep audiences large vs narrowing demos.** MC says keep audiences broad, then demos stacking down to 46,000 and layering interests onto a lookalike before reversing ("I want to keep my audience large"). **Default:** don't narrow (R-AUD-02).
11. **Age.** LWU "Campaign Naming Tips" [2:41] treats Advantage+ as "minimum 18" with no age limits; other lessons add 28-60, 28-65 or 30+. **Default:** a plausible floor, open top (R-AUD-04).
12. **TOF exclusion window** is captioned "108 days" (MC "TOF, MOF, BOF" [0:45]); probably 180. Not used as a number here.
13. **Clinic case location.** TEST "How small wins compound" calls the 40-mile clinic US-based at [0:57] and "a clinic in Australia" at [10:20]. Likely a mis-speak; treat its figures as illustrative only.
14. **Placements coverage is thin.** The only placement-specific lesson has a mismatched transcript. The course's placement advice is "leave it on automatic" plus safe-zone design (R-PLC-01, R-PLC-02).
