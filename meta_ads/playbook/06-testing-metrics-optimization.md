# 06 — Testing, Metrics, Custom Columns & Optimization

Distilled from *The Facebook Ads Clinic* (Nick Boddington; course source in `../course/`). Primary sources:
- `05-testing-and-continued-success.md` (TEST): the core of this file
- `06-learn-with-us.md` (LWU): budget basics, custom columns, hook & hold rate, uneven spend, frequency, flexible ads, Canva hook tests
- `04-lead-gen-facebook-ads.md` (LG): "What does success look like?", "Key Metrics to Watch", hooks, local creative
- `01-facebook-ads-masterclass-2026.md` (MC): local saturation, metrics list, creative volume
- `03-ecommerce-facebook-ads.md` (ECOM): CTR benchmark, link clicks vs all clicks, attribution (e-commerce metrics noted only)
- `07-facebook-ads-for-local-businesses.md` (LOCAL) and `00-welcome-start-here.md` (WELCOME): local budgets, funnel diagnosis

**How to read this file**
- Everything is from the course unless tagged.
- Clinic adaptations are marked **[Clinic adaptation]** and point to a CL- rule in `07-clinic-layer.md`.
- Anything else not from the course is tagged **(general best practice, not from course)**.
- Transcripts are auto-captions, so quoted wording may contain mis-hearings. "[sic]" marks obvious caption errors. The course switches between £ and $ for the same figures; treat money benchmarks as approximate.
- The course judges tests by cost per lead (CPL), CTR and cost per result. For the clinic, CPL is only the early proxy. Final decisions use cost per booked evaluation, show rate and cost per new patient (CL-KPI-01, CL-KPI-03). Read every CPL threshold below with that in mind.

---

## 1. Principles

1. **Creative is the main lever. Test creative, not audiences.** "when it comes down to testing now, I forget about the audiences... we're going broad and we're testing creative and not the audiences" (TEST "Why most ads fail" [1:07]-[2:00]). "creative is the key" (TEST "How small wins compound over time" [10:20]).
2. **One variable at a time.** "we only test one variable at a time. Really, really important." (TEST "One variable at a time" [0:00]).
3. **Small daily budgets plus constant testing compound.** A US functional medicine clinic in a 40-mile radius grew from "a few ads at like $20 a day" to about $18k/month, keeping CPL under $30 (TEST "How small wins compound over time" [0:57], [10:20]-[11:37]).
4. **Be unemotional about losers. Keep winners running.** "It's no good campaign goes off. Okay, that's literally how cut throat we are." (TEST "How small wins compound over time" [2:52]). "Because it's a test doesn't mean you have to switch it off. It's working and pulling your results." (TEST "One variable at a time" [5:59]).
5. **Cost per result beats click metrics.** "the one that's actually got the better metrics isn't actually the winner" (LG "Key Metrics to Watch" [6:48]). The course also says to judge lead gen on more than CPL: lead quality, booking rate, show rate, close rate and client lifetime (LG "What does success look like?" [1:30]).
6. **Iterate, don't reinvent.** "You can get one video or one static and we can find so many different iterations" (TEST "Why most ads fail" [3:59]).
7. **Local audiences saturate.** "it's spending $2,000 a week, surely you're going to get through your audience quickly, well, you are. But that's why we have to now show the people in the audience different things" (MC "Inside the Meta Ecosystem" [8:32]).
8. **Ads fail for reasons outside the ad.** Weak hooks, wrong audience, poor creative or the wrong offer (TEST "Why most ads fail", lesson text). Slow sign-up processes and "red tape" after the lead can make social fail whatever the creative (TEST "Why most ads fail" [2:00]-[3:10]). "It's not just about getting an ad creative and an ad that works, it's about what happens after you've got the click." (WELCOME "Step 1 - Welcome to The Ads Clinic" [0:50]).

**[Clinic adaptation]** Principle 5 is the one this playbook leans on hardest. Meta only sees the lead. Whether the lead booked, showed and became a patient is reconciled weekly outside Meta (GoHighLevel → IntakeQ/PracticeQ). Those outcomes decide winners once there is enough volume (CL-KPI-01, CL-KPI-03).

---

## 2. Rules

### Testing (R-TST)

### R-TST-01: Test creative inside a broad audience; don't test audiences by default
- When: setting up any new test.
- Do: keep the audience broad (Advantage+ audience, or the local radius with only age as a floor). Put the effort into hooks and creative. If you have an interest group that has always worked for you, you may keep using it.
- Don't: build tests around audience splits, or try to "fix" a weak ad with targeting.
- Source: (TEST "Why most ads fail" [1:07]-[2:00]); (TEST "What to test: Hook, Creative, Audience" [8:31]); (LWU "Breaking Down a Winning Ad" [3:58]).
- Clinic: **[Clinic adaptation]** "Broad" for the clinic means broad inside the local radius. Health-condition interest targeting is largely removed, so don't plan interest tests around conditions (CL-POL-01). The clinic case study used "broad, 30+, men and women, 40-mile radius" (TEST "How small wins compound over time" [0:57]). Size budget to that local audience (CL-LOC-02).

### R-TST-02: Change only one variable per test
- When: every test (ads, copy, landing pages, forms).
- Do: keep one primary text and one headline the same across all ads in a hook or video test. Change only the variable under test. When duplicating an ad to swap creative, use "Change media/video" rather than deleting and re-uploading, so the other settings stay intact. Check that the extra text options and Advantage+ creative enhancements are unticked.
- Don't: test a video with different hooks *and* different copy at the same time. Don't change the header, button text and testimonials of a landing page in one go.
- Source: (TEST "One variable at a time" [0:00]-[2:24], [6:50]): "make sure they're not all ticked because if they're all ticked, we're not doing a singular test". (TEST "How to structure a basic testing campaign" [6:11], [8:52]): "Touch of improvements. Everything's off" [sic: creative enhancements]. (LG "What does success look like?" [1:30]): "I've got three different things that have changed and there would just be no point".

### R-TST-03: Test in a fixed order: hook, then video, then copy
- When: building a test plan from one piece of creative.
- Do:
  1. One video × 3 text-overlay hooks.
  2. The winning hook across 3 videos.
  3. The winning video + hook × 3 primary-text variants.
  - If starting from scratch, one video with 5 text-overlay hooks also works. If you are in a rush and already have several creatives, test the creatives directly.
- Don't: run more variants than the budget can feed.
- Numbers: "if you haven't got loads of budgets, I would just test three". Hook overlays can be built in Canva: same video, 5 variants (1 current + 4 new).
- Source: (TEST "One variable at a time" [0:47]-[5:59]); (TEST "What to test: Hook, Creative, Audience" [8:31]-[9:26]); (LWU "Canva Tutorial: Test Hooks That Work" [0:00]).
- Clinic: **[Clinic adaptation]** Hooks must call out the audience without asserting the viewer's condition (no "Your back pain..."). The course's own clinic hooks ("still feeling awful", "Doctor said your labs are fine, but you don't feel fine"; TEST "How small wins compound over time" [2:52]-[5:51], LG "Attention-grabbing Hooks" [3:22]) are second-person health statements; reword them before testing (CL-POL-01).

### R-TST-04: Run tests as new, duplicated ad sets inside one campaign, with names that encode the test
- When: launching each new test.
- Do: keep one main campaign per goal. Duplicate an existing ad set for each new test instead of rebuilding. Name the ad set with audience, test type and date (e.g. "Advantage+ | Hook test | 18 Jul 25"). Name ads by variable (e.g. "Video 2 | Hook 3 | Copy 1"), or put the hook text in the ad name so you can read it without clicking in. Remove the automatic " - Copy" suffix.
- Don't: leave ads named "Copy of Copy" or generic names you have to open to understand.
- Numbers: typical test ad set about £/$30 a day. After "three weeks or three months" the campaign could hold many ad sets at "30, 40, 50, 100 a day".
- Source: (TEST "How to structure a basic testing campaign" [0:54], [3:29]); (TEST "What to test: Hook, Creative, Audience" [9:26], [12:54]); (TEST "One variable at a time" [4:08]-[5:59]); (LWU "Campaign Naming Tips" [0:00]-[2:41]).
- Clinic: **[Clinic adaptation]** Use names that GoHighLevel can carry through to the weekly reconciliation (campaign / ad set / ad), so booked and showed counts can be matched to each test (CL-KPI-03). Never put a condition in a name or tracking parameter that reaches Meta or a URL (CL-HIP-01).

### R-TST-05: Give each test creative its own ad when you need to know the winner
- When: choosing between separate ads, dynamic creative and flexible format.
- Do: when you need creative-level learnings, put each creative in its own ad (a "creative split"). Dynamic creative (up to 10 media, 5 headlines, 5 primary texts) still shows per-asset results where the account has it. Flexible format can run 3-5 creatives on small budgets but hides which one won.
- Don't: use flexible ads for a hook or video test you need to read.
- Numbers: flexible: "between three and five creatives" under about £50 a day.
- Source: (TEST "What to test: Hook, Creative, Audience" [0:48]-[2:31], [5:04]-[5:53]); (LWU "Building a Flexible Ad" [0:48], [1:42]): "meta has removed that functionality to seeing which creative has performed best".

### R-TST-06: Wait a few days before judging, then decide on cost per result against target
- When: deciding whether a test ad or ad set lives or dies.
- Do: look every couple of days and again after a weekend. Judge each ad on cost per result against your target.
- Don't: judge on the first day or two. "We do think we're only two days into these ads" (LG "Key Metrics to Watch" [5:03]).
- Numbers: the course gives no fixed spend threshold. Its decisions, as stated:
  - Clinic example: $30/day ad set, 3-4 leads in total, CPLs of $68 and $46 against a target under $30 → turned off (TEST "How small wins compound over time" [2:52]).
  - A winner that drifted to $37 CPL after about $1,000 and 28 leads → turned off (same lesson [5:51]).
  - Iteration test: turn off older ad sets running at "double the price, if not treble" the new one (TEST "When to test again" [3:23]).
  - Review "after the weekend" / "on Monday" (TEST "What to test: Hook, Creative, Audience" [11:09]-[12:03]).
- Source: as listed; (TEST "How small wins compound over time" [9:06]): "Every couple of days, I'll have a look."
- Clinic: **[Clinic adaptation]** Two-stage judging (CL-KPI-01, CL-KPI-03):
  - *Early (Meta data only):* use CPL as the proxy. Default kill rule (general best practice, not from course): turn an ad off if it has spent about 2× the target CPL with no lead, or has 3+ leads at 1.5-2× target CPL. This matches the course's examples.
  - *Once volume exists:* decide winners on cost per booked evaluation, show rate and cost per new patient from the weekly reconciliation. As a working threshold (general best practice, not from course), switch to these once an ad or ad set has about 20+ leads or about 5+ booked evaluations. A higher-CPL ad that books and shows better is the winner. Also check contact and booking rates before blaming the ad (CL-KPI-02).

### R-TST-07: Turn off losers but keep a winning test ad running
- When: a test has a clear winner.
- Do: switch off the losing ads. Leave the winning ad running in its test ad set and raise its budget a little every couple of days while results hold. Give a proven winner its own ad set so it gets its own budget.
- Don't: switch a working ad off just because it started as a test.
- Numbers: clinic winners at $19-22 CPL after about $1,800-3,000 spend (TEST "How small wins compound over time" [4:56]-[7:48]). Raise budget e.g. 30 → "35, 40 a day" (TEST "What to test: Hook, Creative, Audience" [12:03]).
- Source: (TEST "One variable at a time" [5:59]); (TEST "How small wins compound over time" [4:56]-[5:51]).
- Clinic: **[Clinic adaptation]** "Winner" means best on cost per booked evaluation once there is volume, not lowest CPL alone (CL-KPI-01). Raise budget slowly; the local audience is small (CL-LOC-02).

### R-TST-08: Don't permanently scrap a creative after one failed test
- When: a creative loses.
- Do: record it in the creative tracker and keep it available. The same video can lose in one set-up and win in another.
- Don't: "your first video doesn't work, but then you scrap it and say that doesn't work and never use it again" (warned against).
- Source: (TEST "What to test: Hook, Creative, Audience" [5:53]-[6:54]).

### R-TST-09: After a winner, run an iterations test next to it
- When: you have a winning hook/video and want more ads like it.
- Do: duplicate the winning ad set. Name it e.g. "[hook] | iterations test". Load 4-5 styling iterations of the same video and hook (coloured highlight, arrow, coloured words). Run it alongside the original. When the new ad set matches or beats the old ones, turn off ad sets running at 2-3× its cost per result and scale the survivors.
- Numbers: kill at "double the price, if not treble"; scale survivors toward about £50/day each (about £100/day in the account), budget permitting.
- Source: (TEST "When to test again" [0:51]-[4:13]); (TEST "What to test: Hook, Creative, Audience" [7:43]).
- Clinic: **[Clinic adaptation]** Compare the iterations on downstream cost once the reconciliation has enough rows (CL-KPI-01). At clinic budgets, £50/day per ad set may saturate the radius; scale slower (CL-LOC-02).

### R-TST-10: Test an audience only as a deliberate, equal-budget split
- When: you want to check an interest or other audience against broad.
- Do: duplicate the winning ad set, switch to "original audience options", add the audience, keep the same creative and the same budget. Use ad set budgets (turn off Advantage campaign budget) so Meta doesn't push all spend to one side. After a few days, keep the cheaper ad set and turn the other off.
- Don't: run an audience test you can't afford. Two £30 ad sets is £60/day.
- Source: (TEST "What to test: Hook, Creative, Audience" [10:17]-[12:03]); (LWU "Budget Basics: Spend Smart" [6:02]-[8:35]).
- Clinic: **[Clinic adaptation]** No condition-based interests (CL-POL-01). No patient-list or lead-list custom audiences or lookalike seeds (CL-HIP-02). Website audiences only from generic pages (CL-HIP-06). In practice the clinic's "audience test" is a radius or age-floor test.

### R-TST-11: Move a winning test ad into the master campaign by post ID
- When: a test winner should run in the main (master) campaign and keep its likes and comments.
- Do:
  1. Open two Ads Manager tabs: the test campaign at ad level and the master campaign.
  2. In the test campaign, select the winning ad > Preview > preview settings > "Facebook post with comments". Copy the string of numbers at the end of the URL (the post ID).
  3. In the master campaign's new ad, under Ad setup, switch "Create ad" to "Use existing post". Under Ad creative, choose Enter post ID, paste, tick.
  4. You can change only the CTA and the destination (URL or lead form). The primary text is locked. Publish.
  5. For more winners, duplicate that ad at ad level and swap in the next post ID.
- Source: (TEST "Move WINNING Test Ad into Master Campaign", lesson text + [0:00]): "this keeps all previous ad social proof!"
- Clinic: **[Clinic adaptation]** Carried-over comments may include people describing their conditions. Moderate them and never reply in a way that confirms someone is a patient (general best practice, not from course; see also CL-HIP-05 for any patient content). Keep the destination an instant form (CL-RES-01).

### R-TST-12: Keep a creative tracker and revive old winners by duplicating
- When: from the first test onward.
- Do: keep a tracker with: creative name, hook text, format (video/static), date created, destination (landing page / instant form), status, launch date, lead cost, hook rate, hold rate, leads, CTR, link to the asset folder. Sort winners to the top, then losers, then "to be tested", "hooks that work" and "new filming ideas". After a couple of months, bring back an old winner by duplicating the original ad, not by switching the old ad back on.
- Source: (TEST "Building a "top performers" creative bank" [0:00]-[0:47]): "most of the time it will start up where it left off".
- Clinic: **[Clinic adaptation]** Add columns for booked evaluations, show rate and cost per booked evaluation from the weekly reconciliation (CL-KPI-03). The tracker is also the creative bank used for fatigue refreshes (CL-LOC-01).

### R-TST-13: Test the lead path one element at a time too
- When: testing destination, form type or landing page.
- Do: start with a "More volume" instant form. If lead quality is poor, duplicate the form and ad, switch to "Higher intent", and test. On landing pages, change one element at a time.
- Source: (LG "Instant form - More volume and higher intent" [0:49], [12:30]-[13:20]); (LOCAL "How to create an Instant Form" [0:49]); (TEST "One variable at a time" [6:50]).
- Clinic: **[Clinic adaptation]** Judge form tests on booking and show rate, not lead count (CL-KPI-01, CL-KPI-02). Form questions stay non-clinical (CL-HIP-03). Default destination is the native instant form (CL-RES-01).

### R-TST-14: Try the "organic text post" static as a cheap creative test
- When: you need new static creative fast.
- Do: start a Facebook post with a coloured background (don't publish it), type a hook and short CTA within the background-text character limit, wait for the blinking cursor to disappear, screenshot it. Make several colour/text variants and test them.
- Numbers: course results "CTRs 2.2%+" and "CPMs decreased by 19%". Works for lead gen; not yet tested for e-commerce.
- Source: (TEST "Static FB Text Creative", lesson text + [0:00]-[1:03]).
- Clinic: **[Clinic adaptation]** Same hook rules apply (CL-POL-01).

### Metrics (R-MET)

### R-MET-01: Build and save a lead-gen column preset
- When: before reading any results.
- Do: Columns > "Performance and clicks", then Customize. Remove what you don't need (Ends, Schedule). Order: delivery, budget, amount spent, results, cost per result, reach, impressions (next to reach), frequency, CPM, link clicks, CPC (cost per link click), CTR (link), CTR (all), Leads and Cost per lead (Standard events), video plays (3-second, 25/50/100%), then the custom metrics in R-MET-02 and R-MET-03. Click "Save as column preset" and name it (e.g. "Lead gen").
- Don't: forget to re-tick "save as preset" after every later edit. "if you don't have it ticked, nothing saves" (LWU "Lead Gen: Custom Tracking Columns" [4:54]).
- Source: (TEST "Custom columns - Lead Gen" [0:00]-[2:06]); (LWU "Lead Gen: Custom Tracking Columns" [0:00]-[5:43]); (LWU "Winning Placements in Ads Manager" transcript, which is actually a lead-gen columns walkthrough [2:03]-[7:18]); (TEST "Custom columns - Ecomm" [4:51]): "This must be done. Otherwise, it will save, but it won't save properly."
- Clinic: **[Clinic adaptation]** Results should be instant-form leads ("Meta leads"). The course's own lead-gen example optimises a website event ("submit application"), which may be unavailable for a health advertiser (CL-RES-01). Booked, showed and new-patient columns don't exist in Meta for the clinic; they live in the reconciliation sheet (CL-KPI-03, CL-RES-03).

### R-MET-02: Add the "LC > Lead" custom metric
- When: setting up the preset.
- Do: Columns > Customize > Custom > Create custom metric. Formula: Leads ÷ Link clicks. Name "LC > Lead Conversion". Format: Percentage. Share with yourself or everyone in the business. Create. If it doesn't appear, search its name in custom columns and tick it.
- Numbers: formula Lead ÷ Link Clicks (%). The course gives no benchmark for it.
- Source: (TEST "Custom columns - Lead Gen", lesson text + [0:55]-[2:06]); Skool variant "LC > Complete Reg" = Complete Registrations ÷ Link Clicks (TEST "Custom columns - Skool", lesson text).
- Clinic: **[Clinic adaptation]** Use it with instant-form leads only. Don't build it on a website Lead pixel event on clinic pages (CL-RES-01, CL-HIP-01).

### R-MET-03: Track hook rate and hold rate on video ads
- When: any video creative.
- Do: create two custom metrics, both formatted as percentages:
  - Hook rate = 3-second video plays ÷ impressions.
  - Hold rate = ThruPlays ÷ impressions.
  Add both to the preset. Ignore them for statics and carousels; the numbers are skewed.
- Numbers: hook rate "25% or over as a really good marker" (lower "doesn't mean it's very bad"). Hold rate "around sort of like 10% ish"; videos under about 30 s may get 15-20%; 60 s+ may get 5-10%, "which is equally okay".
- Source: (LWU "Tracking Video Success: Hook & Hold Rate" [0:00]-[1:54]).
- Note: the lesson describes hold rate as people who "watched the full thing", but a ThruPlay counts 15 seconds or completion, whichever comes first. For videos over 15 s it is not a full-view rate.
- Clinic: **[Clinic adaptation]** A falling hook rate on a running ad is one of the weekly fatigue signals (CL-LOC-01).

### R-MET-04: Use link CTR as the click metric; read CTR (all) as engagement
- When: reading click data.
- Do: judge clicks on CTR (link). Compare it with CTR (all). If CTR (all) is well above link CTR, people are interacting with the ad (engaging). If they are about equal, the ad isn't very engaging.
- Don't: use "clicks (all)" as your click count; it includes "see more" and other clicks.
- Numbers: link CTR "Maybe this should be a 1% and above" (LWU "Lead Gen: Custom Tracking Columns" [1:39]). Examples: 0.69% link vs 1.66% all (engaging); 1% link vs 4% all = "engaging well" (TEST "Custom columns - Ecomm" [1:31]); 0.71% vs 1.58% ([6:34]).
- Source: as listed; (LG "Key Metrics to Watch" [3:20]-[4:15]); (ECOM "Key metrics: ROAS, AOV, Cost per Purchase" [1:44]).

### R-MET-05: Know the base metrics and read them together
- When: diagnosing an ad.
- Do: CPM = cost per 1,000 impressions ("which we want as low as possible"). Reach = people. Impressions = times shown. Frequency = impressions ÷ reach. CPC = cost per link click. When results are poor, walk the chain (reach, CPM, CPC/CTR, landing page actions, form submissions) to find the weak stage.
- Source: (TEST "Custom columns - Ecomm" [1:31], [5:46]); (LG "Key Metrics to Watch" [2:29]); (WELCOME "Step 1 - Welcome to The Ads Clinic" [0:00]).
- Clinic: **[Clinic adaptation]** Extend the chain past Meta: lead → contacted → booked evaluation → showed → new patient (CL-KPI-02, CL-KPI-03).

### R-MET-06: Cost per result decides, not click metrics
- When: two ads disagree (one has better CTR/CPC, the other better cost per result).
- Do: keep the ad with the better cost per result even if its CTR and CPC look worse. Turn off ads that miss the KPI.
- Source: (LG "Key Metrics to Watch" [6:48]-[7:39]).
- Clinic: **[Clinic adaptation]** For the clinic, "result" is a booked evaluation that shows, not a lead. Early on, CPL stands in. Once the reconciliation has volume, an ad with lower CPL but poor booking or show rate loses to an ad with higher CPL and better downstream cost (CL-KPI-01, CL-KPI-03).

### R-MET-07: Find winning copy with the dynamic-creative breakdown, where it still exists
- When: running dynamic creative and wanting to know which text, headline or media won.
- Do: Ads Manager > select the ad(s) > Breakdown > "By Dynamic Creative Asset" > Text or Headline (or Image/Video). Compare CTR, CPC and conversions, not impressions. If there is no Results column, judge on clicks and other metrics.
- Numbers: course example: one hook drove 61 of the account's registrations (TEST "What to test: Hook, Creative, Audience" [2:31]); 84 registrations in a similar LG example (LG "What creative type should you use?" [6:39]-[10:07]).
- Source: (TEST "How to find out your winning ad copy", lesson text + [0:00]-[0:54]): "The one with the highest ROI, CTR and best cost per result is your winner." Meta is phasing this out; "it'll just be potluck if you still got that option". Flexible format does not show it.
- Clinic: **[Clinic adaptation]** There is no in-platform ROI for clinic leads. Use cost per result in Meta, then confirm on booked/showed outcomes per ad (CL-KPI-01).

### R-MET-08: Leave attribution at 7 days; treat ranking columns with caution
- When: setting columns and reading results.
- Do: keep the default 7-day attribution setting. Keep the quality, engagement-rate and conversion rankings if you like, but don't rely on them.
- Source: (TEST "Custom columns - Ecomm" [1:31]): "I take a bit of notice to them, but I think the metrics are a bit flaky"; ([5:46]): "attributes in settings always seven days" [sic]; (ECOM "Catalog Sales vs Manual Campaigns" [9:42]).
- Clinic: **[Clinic adaptation]** Meta's 7-day window doesn't cover bookings or visits that happen later. Count those in the reconciliation, by the ad that produced the lead (CL-KPI-03).

### R-MET-09: Judge lead gen on what happens after the lead
- When: deciding whether a campaign or ad is "working".
- Do: track lead quality, booking rate, show rate, close rate and client lifetime alongside CPL. A higher CPL can be fine if leads close and stay.
- Numbers: £15.60 CPL called good because clients stay about 4 months (LG "What does success look like?" [1:30]). An old ad: 27 leads at about £/$14.99, 5 closed. A new hook: 5 form fills at about £6, 3 already booked within a day (LWU "Breaking Down a Winning Ad" [2:52], [6:36]). Example funnel: 26 leads, 16 calls (61%), 6 sales (MC "Inside the Meta Ecosystem" [7:21]).
- Source: as listed.
- Clinic: **[Clinic adaptation]** This is the course's own support for CL-KPI-01. Collect these outcomes in GoHighLevel and IntakeQ/PracticeQ and never send them back to Meta (CL-RES-03, CL-HIP-01).

### Optimization (R-OPT)

### R-OPT-01: Expect uneven spend across ads; act on it, don't fight it
- When: Meta puts most of an ad set's budget on one ad.
- Do: accept that delivery is uneven by design. If one ad takes nearly all the spend and the others get almost none, turn the starved ones off and test them, or new creative, in a duplicated ad set. If you need an even split between audiences, use separate ad sets with equal ad set budgets.
- Don't: assume a starved ad has "lost"; it was never tested.
- Source: (LWU "Budget Basics: Spend Smart" [5:14]): "If this one wins, this ad will get most of the budget. It doesn't matter."; (TEST "What to test: Hook, Creative, Audience" [6:54]-[7:43]); (LWU "What to do if Meta spends on ONE AD only", lesson text only; the video has no transcript, so the course's full fix is not captured).
- Clinic: **[Clinic adaptation]** A starved ad with no leads tells you nothing; log it in the tracker as "untested", not "loser" (CL-LOC-01 creative bank).

### R-OPT-02: Watch frequency and rotate creative before it climbs
- When: every review, and weekly at minimum for the clinic.
- Do: check frequency (impressions ÷ reach). The course turned an ad off when frequency went above 2, and says frequency heading toward 3 means the same people keep seeing the ad and results get more expensive. Keep retargeting budgets small so frequency stays down.
- Numbers: "it got turned off because my frequency went above two" (TEST "Scaling rules (don't touch too fast!)" [8:33]). "we don't want our frequency to go to free [three]"; example $30/day, after about 2 weeks 10k reach and 30k impressions = frequency 3 (LWU "Paid vs Organic: Key Differences" [3:07]-[4:35]). Retargeting at about £5/day "otherwise my retargeting would go into a higher frequency" (LWU "Budget Basics: Spend Smart" [3:34]).
- Source: as listed; (MC "Inside the Meta Ecosystem" [6:13], [8:32]).
- Clinic: **[Clinic adaptation]** The clinic's radius audience is small, so frequency rises faster than in the course's national examples (CL-LOC-01, CL-LOC-02). Weekly:
  - Check 7-day frequency per prospecting ad set. Treat > 2 as a fatigue warning and act when it comes with a fatigue signal: CPL up, link CTR down, or hook rate down versus that ad's first weeks. Don't wait for 3.
  - Refresh from the creative bank (new hook on a proven video first, R-TST-09), rather than raising budget or changing the audience.
  - Retargeting ad sets will run at higher frequency by nature; keep their budgets small.
  - The 7-day window and the "fatigue signal" pairing are general best practice, not from course; the course doesn't say which date range its frequency figures use.

### R-OPT-03: Judge on results, not on "Learning" or "Learning limited"
- When: an ad set shows Learning or Learning limited.
- Do: if cost per result is on target, leave it. Check every couple of days.
- Don't: chase Meta's formula budget (cost per result × 50 ÷ 7) just to exit learning. Don't make big budget jumps on a working ad set; they reset learning.
- Numbers: Meta "wants to get 50 in a seven days to exit learning". The course shows ad sets that exited with 23 and with 10 conversions in 7 days. "Most of my clients live in learning phase and still get really good results."
- Source: (TEST "How small wins compound over time" [7:48]-[9:06]): "I don't always ignore these, but I do take them with a pinch of salt"; (LWU "Budget Basics: Spend Smart" [0:53]-[3:34]); (TEST "Scaling rules (don't touch too fast!)" [5:52]-[7:40]).
- Clinic: **[Clinic adaptation]** At clinic lead volumes most ad sets will stay "Learning limited". That is expected. Judge on the downstream numbers (CL-KPI-01).

### R-OPT-04: Scale winners slowly and only as fast as operations can handle
- When: a winner is holding its cost.
- Do: raise the daily budget in small steps every 2-3 days while results hold. Scale only as fast as staff can call and book the leads.
- Numbers: "not going up more than 15% of your daily budget every three, two to three days" (TEST "Scaling rules (don't touch too fast!)" [2:39]). Elsewhere 15-20% (LG "Setting up a Meta Lead Form campaign" [5:35]). His own examples are bigger (see section 3).
- Source: as listed; (TEST "Scaling rules (don't touch too fast!)" [0:48]-[1:44]).
- Clinic: **[Clinic adaptation]** Scale on cost per booked evaluation, not CPL, and only while speed-to-lead holds (CL-KPI-01, CL-KPI-02). Scale slower than the course in a local radius (CL-LOC-02).

### R-OPT-05: Retest on a schedule and on fatigue signals
- When: deciding when to start the next test.
- Do: always have a next test ready. Start an iterations test as soon as a winner is found (R-TST-09). Make new creative or iterations "every couple of weeks". Before fatigue sets in, test new hooks on the strong video. Revive a past winner after a couple of months by duplicating it (R-TST-12). The "When to test again" lesson text lists the triggers as "new data, fresh creative, or a changed offer".
- Don't: "build one ad, press live and leave it" (paraphrase of WELCOME "Step 5 - Where are you from?").
- Source: (TEST "When to test again", lesson text + [0:00]-[4:13]); (MC "Inside the Meta Ecosystem" [1:26]); (LWU "Canva Tutorial: Test Hooks That Work" [0:00]): "we want to change it before we get creative fatigue"; (TEST "Building a "top performers" creative bank" [0:47]).
- Clinic: **[Clinic adaptation]** In a local radius, the weekly frequency and fatigue check (R-OPT-02) is the main retest trigger (CL-LOC-01).

### R-OPT-06: Before blaming the ad, check the offer and what happens after the lead
- When: costs are high or leads don't turn into bookings.
- Do: check the offer, the destination, the follow-up speed and the booking process. If lead cost is high or quality poor, check whether the call-out is too niche or aimed at the wrong group, and broaden it slightly.
- Source: (TEST "Why most ads fail" [2:00]-[3:10]); (WELCOME "Step 1 - Welcome to The Ads Clinic" [0:50], [4:30]); (LWU "Breaking Down a Winning Ad" [8:54]).
- Clinic: **[Clinic adaptation]** Check contact rate, time to first contact and booking rate in GoHighLevel first (CL-KPI-02).

### R-OPT-07: Follow a fixed review routine
- When: always.
- Do:
  - **Daily (course):** glance at the account. No end dates, so a winner can't switch off unnoticed (LG "Setting up a Meta Lead Form campaign" [5:35]).
  - **Every couple of days (course):** check tests against target, turn off clear losers (R-TST-06), nudge winners up (R-OPT-04) (TEST "How small wins compound over time" [9:06]; TEST "One variable at a time" [5:59]).
  - **After a weekend (course):** make test decisions on Monday rather than mid-weekend (TEST "What to test: Hook, Creative, Audience" [11:09]-[12:03]).
  - **Every couple of weeks (course):** new creative or iterations in (MC "Inside the Meta Ecosystem" [1:26]).
- Source: as listed. The course has no written weekly or monthly routine; the items below fill that gap.
- Clinic: **[Clinic adaptation]**
  - **Weekly:** (1) reconcile leads → booked → showed → new patients per campaign/ad set/ad, outside Meta (CL-KPI-03); (2) update the creative tracker with those numbers; (3) frequency and fatigue check, refresh from the bank (CL-LOC-01); (4) speed-to-lead and booking-rate check (CL-KPI-02); (5) pick the next test.
  - **Monthly (general best practice, not from course):** rank ads and ad sets by cost per booked evaluation and cost per new patient over the month; retire what fails on those numbers even if its CPL looks fine (CL-KPI-01); review whether budget still matches the local audience and clinic capacity (CL-LOC-02); plan filming for the next month's creative.

---

## Metrics table

Formulas are Meta definitions or the course's custom metrics. "Course benchmark" is exactly what the course says, with its context. Clinic rows at the bottom have no course benchmark.

| Metric | Formula | Course benchmark | Clinic note |
|---|---|---|---|
| Cost per lead (CPL) / cost per result | Amount spent ÷ leads | Clinic case target "under $30", account $26-30, winners $19-22, best retargeting ad $14 (TEST "How small wins compound over time" [0:57], [4:56], [10:20]). Consultancy £15.60 (LG "What does success look like?" [1:30]). Local roof cleaner £5-7 best, others under £15 (LG "Local Creative that converts"). | Early proxy only (CL-KPI-01). Set the clinic's own target from cost per new patient, not from these. |
| CTR (link) | Link clicks ÷ impressions | "1% is like an average" (LG "What does success look like?" [1:30]); "Maybe this should be a 1% and above" (LWU "Lead Gen: Custom Tracking Columns" [1:39]); "average of about 1.5", 3.33% "brilliant" (LG "Key Metrics to Watch" [3:20]); text-post statics "2.2%+" (TEST "Static FB Text Creative"). | Instant-form ads: a link click opens the form. Use for diagnosis, not to pick winners. |
| CTR (all) | All clicks ÷ impressions | No target. Well above link CTR = engaging (1% vs 4%; 0.69% vs 1.66%). | Engagement check only. |
| CPC (link) | Amount spent ÷ link clicks | Examples only: £1.39 winner vs £2.29-£3.90 (LG "Key Metrics to Watch" [3:20]). | Diagnostic. |
| CPM | Amount spent ÷ impressions × 1,000 | "want as low as possible". Examples: about £20 (UK), A$40 average, range 23-56 (LG "Key Metrics to Watch" [2:29]). Text-post statics cut CPM 19%. | Local radius CPM rises as frequency rises; watch the trend, not the level. |
| Frequency | Impressions ÷ reach | Off "above two" (TEST "Scaling rules" [8:33]); don't let it reach 3 (LWU "Paid vs Organic" [3:07]). | Weekly check, 7-day window, > 2 plus a fatigue signal → refresh (CL-LOC-01). |
| Hook rate | 3-second video plays ÷ impressions | 25%+ "a really good marker" (LWU "Tracking Video Success" [1:54]). | Video only. A drop vs the ad's own early weeks is a fatigue signal. |
| Hold rate | ThruPlays ÷ impressions | About 10%; 15-20% for videos under ~30 s; 5-10% for 60 s+ (same lesson). | Video only. ThruPlay = 15 s or completion. |
| LC > Lead | Leads ÷ link clicks | No benchmark given (TEST "Custom columns - Lead Gen"). | Instant-form leads only (CL-RES-01). Tracks form completion. |
| Lead → booked rate | Booked evaluations ÷ leads | Examples only: 16 of 26 (61%) (MC "Inside the Meta Ecosystem" [7:21]); about 1 in 3 book from the form end screen (LG "What does success look like?" [1:30]). | From GoHighLevel/IntakeQ, weekly (CL-KPI-02, CL-KPI-03). |
| Cost per booked evaluation | Amount spent ÷ booked evaluations | None in the course. | Primary winner metric once volume exists (CL-KPI-01). |
| Show rate | Evaluations attended ÷ booked | None in the course (named as a measure in LG "What does success look like?"). | CL-KPI-01. |
| Cost per new patient | Amount spent ÷ new patients | None in the course. Course logic: judge against lifetime value (LG "What does success look like?"; ECOM "What does success looks like?"). | CL-KPI-01; reconciled outside Meta (CL-KPI-03). |

E-commerce columns (add to cart, initiate checkout, purchases, ROAS) and e-commerce funnel benchmarks are in TEST "Custom columns - Ecomm" and WELCOME "Step 2" (e-commerce; not applicable to the clinic).

---

## 3. Open questions / contradictions in the course

1. **How much spend before judging.** The course never gives a fixed spend or lead threshold. It decides after "a few days", "after the weekend", or after 3-4 leads at about 1.5-2× target CPL. **Default here:** R-TST-06's two-stage rule (CPL proxy kill rule early, downstream metrics once about 20+ leads or 5+ booked evaluations). The thresholds are general best practice, not from the course.
2. **What decides a winner.** The copy-breakdown lesson says "highest ROI, CTR and best cost per result". "Key Metrics to Watch" says cost per result beats CTR/CPC. "What does success look like?" says look past CPL to booking, show and close rates. **Default:** cost per result in Meta early; cost per booked evaluation, show rate and cost per new patient once there is volume (CL-KPI-01). ROI is not available in Meta for clinic leads.
3. **Average CTR.** "1% is like an average" (LG "What does success look like?"; ECOM) vs "average of about 1.5" (LG "Key Metrics to Watch"). **Default:** treat about 1% link CTR as the floor and 1.5%+ as good. Diagnostic only.
4. **Frequency threshold.** Off "above two" (TEST "Scaling rules") vs "don't want our frequency to go to three" (LWU "Paid vs Organic"). The date range isn't stated. **Default:** 7-day frequency > 2 is the warning level for the clinic's local radius, acted on with a fatigue signal (CL-LOC-01).
5. **Test audiences or not.** The lesson title says "Hook, Creative, Audience" and demos an interest test. The same module says "I forget about the audiences". **Default:** creative tests only; audience tests rarely, as equal-budget splits, and never on health conditions (CL-POL-01).
6. **Kill fast vs don't scrap.** "cut throat" killing after 3-4 expensive leads vs "don't scrap a video after one failed test". **Default:** both. Turn the ad off fast, but keep the creative in the tracker for a later re-test in a different set-up.
7. **Number of variants.** "just test three" on a low budget vs "one video with five hooks", 5×5×5 dynamic creative, and 3-5 creatives in a flexible ad. **Default:** 3 variants per test at clinic budgets.
8. **Dynamic/flexible vs single-variable testing.** Dynamic creative is "disappearing" but "you might still get away with this way"; flexible ads hide the winner. Mixing 5 headlines × 5 texts × 5 media also breaks the one-variable rule. **Default:** separate ads, one creative each, for tests (R-TST-05).
9. **Scaling increment.** "not more than 15% every 2-3 days", but his own example moves £20 → £25 (25%) and he says jumping 20 → 40 "does all right". LG says 15-20%. **Default:** about 15-20% steps every 2-3 days, slower in the local radius (CL-LOC-02).
10. **Learning phase.** Warned that big jumps reset learning, yet "Learning limited" is ignored when CPL is fine, and ad sets exited learning with 10 and 23 conversions. **Default:** judge on results; avoid big jumps (R-OPT-03).
11. **CPL that counts as a winner.** In the clinic case, a winner was turned off at about $37, while an ad at about $42 (9 leads) is described as having done "particularly well" [sic, possibly a caption error]. **Default:** compare ads on downstream cost, which settles this kind of ambiguity.
12. **Hold rate definition.** Described as watching "the full thing", but the formula uses ThruPlays (15 s or completion). **Default:** use the formula and read it as "15 seconds or completion".
13. **Uneven spend.** One lesson calls it "frustrating"; Budget Basics calls it intended. The detailed fix is in a YouTube video with no transcript. **Default:** accept it and re-test starved ads in a new ad set (R-OPT-01). The course is thin here.
14. **Column set details.** The lead-gen columns lesson refers to a slide or sheet that is not in the source; only some columns are named. The LWU lead-gen example optimises a website event ("submit application"), not an instant form. **Default:** the preset in R-MET-01, with instant-form leads as results (CL-RES-01).
15. **Weekly and monthly routine.** The course gives "daily", "every couple of days", "after the weekend" and "every couple of weeks", but no weekly or monthly review. **Default:** the clinic routine in R-OPT-07, built around the weekly reconciliation (CL-KPI-03).
