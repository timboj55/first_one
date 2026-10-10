# 01 — Account Setup, Pixel, Events & Tracking

Distilled from *The Facebook Ads Clinic* (Nick Boddington; course source in `../course/`). Primary sources:
- `01-facebook-ads-masterclass-2026.md` (MC): "What is Business Manager?", "Set Up Your Pixel (The Right Way)", "Event Codes Made Simple", "Skool Pixel Set-up", "Build an Ecomm Ad", "Build an Lead Gen Ad"
- `07-facebook-ads-for-local-businesses.md` (LOCAL): "Run proper ads and track real results", "Instantly Receive Your Leads by Email", "Setting Up Your Local Lead Campaign (Step-by-Step)"
- `04-lead-gen-facebook-ads.md` (LG): "Landing pages vs Lead Forms", "Setting up a Meta Lead Form campaign", "Setting up a Meta Landing page campaign", "Importance of lead magnets, forms, booking flows", "Instant form - More volume and higher intent", "Building a Local Campaign"
- `06-learn-with-us.md` (LWU): "Campaign Naming Tips", "Meta Restricts Health Business Tracking", "Unlock Facebooks's Hidden Ad Feature", "How to create Custom Audiences", "Use Product Catalogues the Right Way", "Winning Placements in Ads Manager" (transcript is actually lead-gen columns)
- `03-ecommerce-facebook-ads.md` (ECOM): "Catalog Sales vs Manual Campaigns", "Importance of product pages, reviews, UGC"
- `05-testing-and-continued-success.md` (TEST): "Custom columns - Ecomm", "One variable at a time", "What to test: Hook, Creative, Audience"
- `00-welcome-start-here.md` (WELCOME): "Go High Level - CRM on STEROIDS!"

**How to read this file**
- Everything is from the course unless tagged.
- Clinic adaptations are marked **[Clinic adaptation]** and point to a CL- rule in `07-clinic-layer.md`.
- Anything else not from the course is tagged **(general best practice, not from course)**.
- Transcripts are auto-captions, so quoted wording may contain mis-hearings ("data set stroke pixel" = dataset/pixel, "Rents Manager" = Events Manager, "Zapia" = Zapier).
- This file carries the most HIPAA risk in the playbook. The course teaches tracking for businesses with no health-privacy duties. Every course step that would send patient identifiers or condition-revealing data to Meta is marked **"Do not follow for the clinic"** with the CL-HIP rule. Read the summary at the end of section 2 ("Clinic tracking setup") before touching Events Manager.

---

## 1. Principles

1. **Ads Manager is the way in; Business Manager is the container.** "It's actually ads manager, but it's all run inside business manager." (MC "What is Business Manager?" [0:47]). Get the portfolio's assets in order before you build anything.
2. **Set the irreversible things right the first time.** Ad account currency and time zone cannot be changed later: "you can't go back. There is nowhere in your setting is that you can go back and change your currency." (MC "What is Business Manager?" [4:20]).
3. **The course treats the pixel as essential.** "everything has to be tracked on a data set and a pixel" (MC "Set Up Your Pixel" [0:00]). It also says that without a dataset "you will not be able to use a lead objective" (MC "What is Business Manager?" [6:03]). That second claim is contradicted by the course's own instant-form builds, which need no pixel (LOCAL "Setting Up Your Local Lead Campaign" [0:00]-[0:49]). See section 3.
4. **Count the real action, not the first click.** The Lead event should fire after someone has given their details or booked, ideally on the confirmation URL: "this is actually probably more accurate than I had before, which is someone's click the button. That could be an accidental press" (MC "Event Codes Made Simple" [10:07]).
5. **Check tracking is actually working.** Pixel Helper should show "green. We don't want this to be amber." (MC "Event Codes Made Simple" [3:28]). Ad-level "Website events" must be on for landing-page ads: "100% make sure that your website's events in tracking is triggered on" (LG "Setting up a Meta Landing page campaign" [13:50]).
6. **Don't change the attribution default.** 7-day click, 1-day engaged-view, 1-day view "is the right attributes in settings. You don't need to go on and change that." (ECOM "Catalog Sales vs Manual Campaigns" [9:42]).
7. **Leads must reach a person fast and automatically.** Don't download CSVs each morning ("all the data is going to download is going to come very scruffy"); automate delivery to inbox/CRM (LG "Setting up a Meta Lead Form campaign" [18:54]).
8. **Name things so you can read the account without clicking in.** "the idea of the naming conventions is that we're not going into having to go into every add and see what we've got" (LG "Setting up a Meta Lead Form campaign" [1:24]).
9. **Health & wellness advertisers lose conversion signals.** "When your business falls into the 'health and wellness' category, Meta actively restricts how your conversion signals flow back into Ads Manager." and "Why rewriting copy or changing creatives won't fix this" (LWU "Meta Restricts Health Business Tracking", lesson text). The course's answer is a "bypass"; this playbook does not adopt it (R-TRK-14, CL-RES-02).

---

## 2. Rules

### R-SET-01: Set up the business portfolio with the minimum assets first
- When: before running any ad, or when taking over an account.
- Do: In Ads Manager, open Business settings from the left-hand menu. Make sure the portfolio holds: People, Partners (if an agency/consultant is used), the Facebook Page, an ad account, the Instagram account, and a dataset (pixel). Run on both Facebook and Instagram. One portfolio can hold several pages and ad accounts.
- Don't: Don't treat Business Manager and Ads Manager as separate places to run ads. Don't connect WhatsApp unless you want ads to open WhatsApp conversations instead of Messenger and can staff them (needs a WhatsApp Business account).
- Source: MC "What is Business Manager?" [0:47]-[1:47], [3:02], [5:13], [8:58] ("you'll need your Instagram account if you're running on Instagram and Facebook, which I do advise, and you will need a data set and pixel"); LOCAL "Run proper ads and track real results" [0:00]-[8:58].
- Clinic: **[Clinic adaptation]** Create the dataset so it exists and is owned by the clinic's portfolio, but installing it is optional and limited (R-TRK-02, CL-HIP-01). Instant-form lead campaigns run without it (CL-RES-01).

### R-SET-02: Add people by their Facebook email; give outside help Partner access
- When: adding staff, an agency or a consultant.
- Do: Add a person with the email tied to their Facebook login (they may need to look it up in Facebook). Add an agency as a Partner and assign it only the assets it needs.
- Don't: Don't share your own login.
- Source: MC "What is Business Manager?" [1:47]-[3:02]; LOCAL "Run proper ads and track real results" [1:47]-[3:02].
- Clinic: **[Clinic adaptation]** Anyone given Lead access (R-SET-06) can see lead contact details. Keep that list short (general best practice, not from course).

### R-SET-03: Bring in the Facebook Page first, then confirm Instagram came with it
- When: setting up a new portfolio.
- Do: Pages > Add > "Add an existing Facebook page" (other options: request shared access, create new). Approve, then assign yourself to the Page if it doesn't happen automatically. Instagram usually comes in with the Page; check it did. At ad set level, check the right Page and Instagram account are selected, especially with several pages.
- Source: MC "What is Business Manager?" [3:02], [5:13] ("First thing you need to do is bring in your Facebook page."); LG "Setting up a Meta Landing page campaign" [4:24], [10:26].

### R-SET-04: Set the ad account's time zone and currency correctly before you confirm
- When: creating an ad account.
- Do: Create the ad account yourself (it may not exist automatically). Check business name, time zone and currency on the creation screen, then confirm ownership.
- Don't: Don't accept Meta's guesses. In the course demo Meta picked the UK time zone but US dollars.
- Numbers: currency and time zone are permanent ("you can't go back").
- Source: MC "What is Business Manager?" [3:02]-[4:20]; LOCAL "Run proper ads and track real results" [4:20].
- Clinic: **[Clinic adaptation]** US clinic: USD and the clinic's local US time zone, so daily budgets and reports line up with the clinic's day (general best practice, not from course).

### R-SET-05: Set up billing before you try to run an ad
- When: right after the ad account is created.
- Do: Complete the billing and payment section in the ad account.
- Source: MC "What is Business Manager?" [4:20]; LOCAL "Run proper ads and track real results" [4:20].
- Clinic: **[Clinic adaptation]** Tim enters payment details himself; Claude never does (owner's standing instruction).

### R-SET-06: Grant Lead access, and full Page control, to whoever retrieves instant-form leads
- When: before launching instant-form campaigns, and whenever a lead integration keeps switching itself off.
- Do: In Business settings, give yourself (and any agency) Lead access. If a Zapier/CRM lead integration keeps turning off, go to Business Suite > Pages > your Page, make sure you have full control with everything on, including leads access, then switch the integration back on.
- Source: MC "What is Business Manager?" [7:57] ("for them to have access to your leads, they need that lead access"); LOCAL "Instantly Receive Your Leads by Email" [13:03]-[14:10] ("Everything needs to be on").

### R-SET-07: Treat Meta Verified as optional; domain verification is not required
- When: deciding on account extras.
- Do: Buy Meta Verified only if you want the support/recovery route. The course is split: MC says support is "not really" quicker or better; LWU says it got the speaker back in after a 3-day lockout.
- Numbers: "$9.99 a month" (MC); "10 pounds a month" (LWU).
- Source: MC "What is Business Manager?" [7:57] ("you used to have to verify your domain, you don't have to do that anymore"); LWU "Unlock Facebooks's Hidden Ad Feature" [1:43]; LOCAL "Run proper ads and track real results" [7:57].

### R-SET-08: Check every new ad for an auto-attached product catalog
- When: creating an ad, and after every creative re-upload.
- Do: In the ad's Creative setup, set any catalog to "not connected" unless you deliberately run catalog ads. Meta can attach your own unwanted catalog or another client's. Re-check creative "optimizations", which also reset to on after re-upload.
- Numbers: demo showed "catalog items 397" attached by default.
- Source: LWU "Use Product Catalogues the Right Way" [1:16], [2:32]-[3:44].
- Clinic: **[Clinic adaptation]** The clinic has no catalog; this is a hygiene check only. Catalog/sales campaigns are e-commerce (not applicable to the clinic).

### R-TRK-01: Create one dataset (pixel), connect it to the ad account, and keep stale pixels out of the way
- When: once, at setup.
- Do: Business settings > Data sources > create a new dataset (a dataset and a pixel are the same thing). Then connect it to the ad account under Connected assets "Rather than having the dataset set up and then just sitting on its own". Optionally assign a partner. When building anything that asks for a pixel later, pick the correct one; old or agency pixels can appear in the list.
- Source: MC "What is Business Manager?" [6:03]; MC "Set Up Your Pixel" [1:43]-[2:31]; LWU "How to create Custom Audiences" [1:25].
- Clinic: **[Clinic adaptation]** Creating and connecting the dataset is safe on its own; nothing is sent until code is installed. Name it neutrally (e.g. "Movement Solutions website"), not after a condition (CL-HIP-01).

### R-TRK-02: Install the base code in the website header (or via the platform's Meta integration)
- When: after creating the dataset, if the site will host ad landing pages.
- Do: Events Manager > dataset > Overview > Manage integrations > Meta Pixel > Install pixel on website > Install code manually > copy the base code. Paste the whole code into the site header ("same area you would put like Google Analytics"). If a platform asks only for a "pixel ID" or "dataset ID", paste just the number. Use the platform's integration where one exists (WordPress Meta app, Shopify, GoHighLevel tracking settings, Skool plugin), or send the code to a developer.
- Source: MC "Set Up Your Pixel" [0:00]-[0:51], [4:10]-[6:54]; MC "Event Codes Made Simple" [4:20]; MC "Skool Pixel Set-up" [0:54] (Skool-specific).
- Clinic: **[Clinic adaptation] Do not follow for the clinic as a site-wide install.** A site-wide header pixel sends every page URL and title to Meta, which reveals conditions (e.g. /low-back-pain) and appointment intent (CL-HIP-01). If the pixel is installed at all, put it only on generic marketing pages (home, about, a neutral offer page). Never on condition-specific pages, booking, intake, patient-portal or thank-you/confirmation pages (CL-HIP-01, CL-HIP-06). In GoHighLevel, add it only to the specific generic funnel pages, not the account-wide tracking setting. Get the placement reviewed before it goes live.

### R-TRK-03: Automatic advanced matching — course says turn it all on
- When: during base-code setup in Events Manager.
- Do (course): "I want you to turn on all of the automatic advanced matching. This means that anything that's put into your website will get send the data back to meta".
- Source: MC "Set Up Your Pixel" [5:04].
- Clinic: **[Clinic adaptation] Do not follow for the clinic. Leave automatic advanced matching OFF** (CL-HIP-01). It hashes and sends what visitors type into site forms (email, phone, name and similar) to Meta, tying a named person to the clinic pages they visited. Check the setting after any change to the dataset or website platform, since integrations can switch it on.

### R-TRK-04: Test the pixel with Meta Pixel Helper until it shows green
- When: after installing the pixel or changing events.
- Do: Install the Meta Pixel Helper extension in Chrome (not Safari). Load your page; the pixel should show green with PageView. Amber means checks or a developer fix are needed. An ad blocker can cause a false warning: disable it and refresh. Then walk the funnel and confirm each event fires. Events Manager also has a "test events" feature (mentioned, not demonstrated).
- Source: MC "Event Codes Made Simple" [0:00]-[4:20], [8:23]-[10:07]; MC "Set Up Your Pixel" [4:10].
- Clinic: **[Clinic adaptation]** Test only on the generic pages where the pixel is allowed, and confirm it does NOT appear on booking, intake or condition pages. **Do not follow** the course's end-to-end test of booking a real appointment through the funnel with events firing; never test with real patient details (CL-HIP-01).

### R-TRK-05: Set up events with the Event Setup Tool and name them for the action
- When: after the base code is live, for website-conversion campaigns.
- Do (course): Events Manager > dataset > Manage integrations > Meta Pixel > "Open event setup tool" > enter your URL > "Track new button" or "Track a URL" > pick the event that matches the action (e.g. Schedule for a booking button, Lead for a completed enquiry) > Confirm > Finish.
- Source: MC "Event Codes Made Simple" [5:56]-[10:57] ("you need to put in the ones that kind of match").
- Clinic: **[Clinic adaptation] Do not follow for the clinic on booking, intake or condition pages** (CL-HIP-01). A Schedule or Lead event on the booking flow tells Meta that an identifiable visitor booked a clinical appointment. These lower-funnel events are also likely unavailable for optimization under the health restriction (CL-RES-01). If the pixel is on generic pages, PageView is enough.

### R-TRK-06: Fire the Lead event after the details are submitted, on the confirmation URL
- When: building website-lead tracking.
- Do (course): Fire Lead only after the person has given their information or booked, not on the first button click and not on page load. Prefer "Track a URL" on the thank-you/confirmation page over button tracking, because a button press "could be an accidental press".
- Source: MC "Event Codes Made Simple" [5:09], [10:07]; LG "Importance of lead magnets, forms, booking flows" [5:09] ("your lead event activates after someone has given you this information"); LG "Landing pages vs Lead Forms" [3:27] ("once they book that call, it will then activate as a lead").
- Clinic: **[Clinic adaptation] Do not follow for the clinic.** A Lead event on a booking-confirmation or thank-you page reveals an appointment, and the URL can reveal the condition (CL-HIP-01). The clinic's conversion is the native instant-form lead, which Meta records on-platform without a pixel (CL-RES-01). The logic (count the completed action, not the click) still applies to how we count bookings in GoHighLevel/IntakeQ (CL-KPI-03).

### R-TRK-07: Pixel on every funnel page to see drop-off
- When: building a landing-page funnel.
- Do (course): Put the pixel on every funnel page (landing page, booking/calendar page, thank-you page). Use PageView on the landing page, a "start" event, and a Lead event, so you can see where people drop off.
- Numbers: example of "100 people a day" on the landing page.
- Source: MC "Event Codes Made Simple" [4:20]-[5:09].
- Clinic: **[Clinic adaptation] Do not follow for the clinic** (CL-HIP-01, CL-HIP-06). Measure funnel drop-off outside Meta instead: instant-form leads → contacted → booked → showed in GoHighLevel/IntakeQ (CL-KPI-02, CL-KPI-03).

### R-TRK-08: Conversions API (server-to-server) alongside the pixel
- When: course presents it as part of a full setup.
- Do (course): Use the Conversions API so your server talks to Meta's server as well as the browser pixel. "It's something you'll need to get a programmer to set up." The course does not teach the setup.
- Source: MC "Set Up Your Pixel" [3:19]-[4:10].
- Clinic: **[Clinic adaptation] Do not follow for the clinic.** No CAPI events carrying patient data: no names, emails, phones, IP/user agent tied to booking or intake, no appointment or patient-status events (CL-HIP-01). Sending CRM stages ("booked", "became a patient") via CAPI or Meta's "Conversion Leads" is not used unless legal review approves (CL-RES-03). Note: GoHighLevel and other platforms may offer one-click CAPI; leave it off.

### R-TRK-09: Custom conversions from URL rules
- When: the course says "advanced" and points to later courses; it never fully teaches it.
- Do (course): In Events Manager > Custom conversions, define a conversion by URL rule and name it how you like. Button-based conversions need Google Tag Manager.
- Source: MC "What is Business Manager?" [6:57]; MC "Set Up Your Pixel" [3:19]; MC "Event Codes Made Simple" [6:43]; LOCAL "Run proper ads and track real results" [6:57].
- Clinic: **[Clinic adaptation] Do not follow for the clinic.** URL-based conversions on clinic pages reveal conditions or appointments in the URL and the conversion name (e.g. /back-pain-thank-you) (CL-HIP-01). Custom conversions are also among the events restricted for health advertisers (CL-RES-01).

### R-TRK-10: Offline events and CRM sync back to Meta
- When: course suggests it for leads that convert off-site (on the phone, in the CRM).
- Do (course): Send off-site outcomes back to Meta as offline events "so you're not just relying on people hitting your website". Separately, LWU uploads a monthly customer list (name, email, phone) to feed Meta "more" than the pixel sees. LG says to ignore Meta's new in-ad "CRM integration" for now because it needs your whole funnel mapped and probably a developer.
- Source: MC "What is Business Manager?" [6:57]; LOCAL "Run proper ads and track real results" [6:57]; LWU "Unlock Facebooks's Hidden Ad Feature" [7:58]-[8:50]; LG "Setting up a Meta Lead Form campaign" [3:47] ("I would just leave this, ignore it there until we know more about it").
- Clinic: **[Clinic adaptation] Do not follow for the clinic.** No offline event uploads, no CRM/GoHighLevel → Meta sync, no patient-list uploads (CL-HIP-01, CL-HIP-02). Keep ignoring the Meta CRM integration and Conversion Leads unless legal review approves (CL-RES-03). Data flows one way only: Meta → GoHighLevel. Booked/showed/new-patient outcomes stay in GoHighLevel/IntakeQ (CL-KPI-03).

### R-TRK-11: Set ad-level "Website events" deliberately for each ad
- When: at ad level, under Tracking, before publishing.
- Do (course): On landing-page ads, Website events must be on with the correct dataset; it is sometimes off by default and "you will not get any of that tracking working". On instant-form ads the course turns it on "out of habit", while saying there is "not really that much need". App events and offline events are not needed unless used.
- Source: LG "Setting up a Meta Landing page campaign" [13:50]-[14:43]; LG "Setting up a Meta Lead Form campaign" [17:23]; ECOM "Catalog Sales vs Manual Campaigns" [19:30], [21:56] ("We always, always, always have this turned on"); MC "Build an Lead Gen Ad" [11:46]; MC "Build an Ecomm Ad" [13:53].
- Clinic: **[Clinic adaptation]** On instant-form ads, leave Website events **off**; it adds a pixel data flow for no benefit (CL-HIP-01). Turn it on only for an ad that sends people to a generic, reviewed landing page that carries the pixel (R-TRK-02). Check after every duplicate, since settings carry over.

### R-TRK-12: Know where each lead type is reported, and show total leads in columns
- When: reading results.
- Do: Instant-form leads show as "Meta lead"; landing-page leads show as "website lead". In the lead-gen column preset, add Leads and Cost per lead; untick the Meta / website / offline lead breakdowns if you want one total. Untick in-app and offline purchase columns that you haven't set up.
- Source: LG "Landing pages vs Lead Forms" [3:27] ("when it's an instant format, it will show meta lead. If it's landing page, it will show website lead"); LWU "Winning Placements in Ads Manager" (lead-gen columns transcript); TEST "Custom columns - Ecomm" [5:46].
- Clinic: **[Clinic adaptation]** For the clinic, the in-Meta result is the instant-form lead. Cost per lead is diagnostic only; judge on cost per booked evaluation, show rate and cost per new patient from GoHighLevel/IntakeQ (CL-KPI-01, CL-KPI-03). Column presets themselves are covered in the metrics file.

### R-TRK-13: Keep Meta's default attribution setting and expect late conversions to show elsewhere
- When: at ad set level (Show more settings > Attribution setting) and when comparing Meta to other sources.
- Do: Leave it at 7-day click, 1-day engaged-view, 1-day view. Expect actions after the window to be credited elsewhere (e.g. Google). The window used to be 28 days.
- Don't: Don't change the attribution setting.
- Numbers: 7-day click / 1-day engaged-view / 1-day view; formerly 28 days.
- Source: ECOM "Catalog Sales vs Manual Campaigns" [9:42]; ECOM "Importance of product pages, reviews, UGC" [10:13]-[11:04] ("if they buy on the eighth day, it doesn't attribute to the ad. You'll probably attribute to Google. It used to be 28 days."); TEST "Custom columns - Ecomm" [5:46] ("always seven days").
- Clinic: **[Clinic adaptation]** Meta's attribution only covers the instant-form lead. Whether that lead booked or showed (often days later, by phone) is attributed outside Meta by weekly reconciliation per campaign/ad (CL-KPI-03).

### R-TRK-14: If conversion columns go blank as a health advertiser, don't "bypass" the restriction
- When: website conversion events stop reporting or can't be selected for optimization.
- Do (course): Recognise it is a category-level restriction, not a campaign problem: "Why rewriting copy or changing creatives won't fix this". The lesson then promises "The tracking solution we're using to bypass these restrictions" and to "feed real conversion data back into Meta". The mechanism is never named in the course file (video only, no transcript).
- Source: LWU "Meta Restricts Health Business Tracking" (lesson text). It lists "Functional medicine? Blocked." and "And many more....". Physical therapy is not named.
- Clinic: **[Clinic adaptation]** Accept the diagnosis; reject the remedy. **Do not follow** the bypass in any form (CL-RES-02, CL-HIP-01). Default to the Leads objective with native instant forms (CL-RES-01) and measure outcomes in GoHighLevel/IntakeQ (CL-KPI-03).

### R-TRK-15: Deliver instant-form leads automatically to the CRM; never by morning CSV download
- When: before the first instant-form campaign goes live.
- Do (course): Connect the form so each lead arrives instantly. Two routes are taught: (a) Zapier: Facebook Lead Ads "New Lead" (choose Page + form) → Google Sheets "Create spreadsheet row" → Gmail "Send email" to the owner; Facebook Lead Ads is a premium Zapier app, so a paid tier is needed. (b) GoHighLevel: Integrations > "Facebook form fields mapping" > select the form > map first name, surname, phone, email and custom questions > toggle on; leads land in Contacts. Use the form's tracking parameters to route leads cleanly into the CRM. Set up the follow-up system before launching ads.
- Don't: Don't rely on downloading the leads CSV from Ads Manager each morning.
- Source: LG "Setting up a Meta Lead Form campaign" [18:54]; LG "Instant form - More volume and higher intent" [10:46]-[11:38]; LOCAL "Instantly Receive Your Leads by Email" [0:00]-[13:03]; WELCOME "Go High Level - CRM on STEROIDS!" [0:00]-[1:41], [3:28].
- Clinic: **[Clinic adaptation]** Use the direct Meta → GoHighLevel connection; GoHighLevel must be on a HIPAA-eligible plan with a BAA (CL-HIP-04). **Do not follow** the Zapier → Google Sheets → Gmail route unless every tool is HIPAA-eligible with a BAA in place (CL-HIP-04). Tracking parameters and form/field names must not encode a condition or service line tied to the lead (e.g. no "back-pain-campaign") (CL-HIP-01). Flow is one-way: nothing from GoHighLevel goes back to Meta (CL-HIP-01, CL-RES-03). Form content rules are in file 04 (CL-HIP-03).

### R-TRK-16: UTMs and GA4 are optional for Meta delivery
- When: deciding whether to add UTM parameters.
- Do (course): UTMs/GA4 are an "advanced" extra. "It is not going to make any difference to your advertising."
- Source: MC "Build an Ecomm Ad" [13:53].
- Clinic: **[Clinic adaptation]** Instant-form leads don't need UTMs. If an ad links to the website, neutral UTMs (campaign/ad IDs, no condition words) are fine and help reconciliation (general best practice, not from course; CL-HIP-01, CL-KPI-03).

### R-NAM-01: Name campaigns by funnel stage, objective and destination (plus area for local)
- When: creating or duplicating a campaign.
- Do: Put the funnel stage, objective and destination in the campaign name, and the area for local campaigns. Examples: "TOF - Lead - Instant form", "TOF - Lead - Landing page", "TOF - Lead generation - Wadebridge", "Top of funnel leads campaign", "retargeting".
- Source: LG "Setting up a Meta Lead Form campaign" [1:24]; LG "Setting up a Meta Landing page campaign" [1:45]; LOCAL "Setting Up Your Local Lead Campaign" [0:00]; LWU "Campaign Naming Tips" [0:00]-[2:41]; MC "Build an Lead Gen Ad" [0:51].

### R-NAM-02: Name ad sets by what is actually set: audience or location + radius, plus test type and date
- When: creating or duplicating an ad set.
- Do: Name only settings you actually changed (e.g. "Advantage+", "digital marketing", "Wadebridge 40km", "28-60"). Don't list defaults such as "male and female". For test ad sets, add the test type and date, e.g. "Advantage+ | Hook test | 18 Jul 25". Use separate, clearly named ad sets when testing radii or towns.
- Source: LWU "Campaign Naming Tips" [0:00]-[2:41] ("I'm only putting in here what's actually in the audience"); LG "Setting up a Meta Landing page campaign" [3:37]; LG "Building a Local Campaign" [0:00]; LOCAL "Setting Up Your Local Lead Campaign" [2:26]; TEST "What to test: Hook, Creative, Audience" [9:26]; TEST "One variable at a time" [4:57]-[5:59].

### R-NAM-03: Name ads after the creative file or the variable being tested
- When: creating or duplicating an ad.
- Do: Give the ad the same name as the video/static file in your asset folder. Or name it by format/offer ("Video", "DC", "free valuation") or by the variable ("Video 2 | Hook 3 | Copy 1"); you can put the hook text itself in the ad name. Remove Meta's automatic " - Copy" suffix when duplicating.
- Source: LWU "Campaign Naming Tips" [1:50] ("whatever you have your videos or static ... save to in your actual folder, name them the same things"); TEST "One variable at a time" [4:57]-[5:59]; LG "Building a Local Campaign" [4:04]; MC "Build an Ecomm Ad" [1:43].
- Clinic: **[Clinic adaptation]** Use the same ad names in the creative bank and in the weekly GoHighLevel/IntakeQ reconciliation sheet so booked/showed counts map to ads (CL-KPI-03, CL-LOC-01).

### R-NAM-04: Name audiences and data objects plainly — and keep condition words out of anything tied to a person
- When: naming custom audiences, datasets, events, custom conversions, form fields and tracking parameters.
- Do (course): Name audiences so you can find them later, e.g. "30 day website add to carts excluding purchases", "Submitted lead form"; name custom conversions "how you want them to be named".
- Source: LWU "How to create Custom Audiences" [1:25], [7:39]; MC "Audience Types Explained" [13:42]; MC "What is Business Manager?" [6:57].
- Clinic: **[Clinic adaptation]** Campaign, ad set and ad names are internal account labels and may name a service line (e.g. "TOF - Lead - Instant form - Knee") (general best practice, not from course). Anything attached to an individual's data must stay neutral: dataset name, event names, URLs/slugs where the pixel runs, audience names and rules, form names, field names and tracking parameters. No conditions, injuries or "patient" labels (CL-HIP-01, CL-HIP-06).

### Clinic tracking setup (what we actually do) [Clinic adaptation]
This summarises the safe configuration. It overrides any course step above that conflicts with it.
- **Primary conversion = native instant-form lead.** Leads objective, conversion location Instant forms (CL-RES-01). No pixel is needed for this.
- **Pixel: only on generic marketing pages, if at all.** Never on condition-specific pages, booking, intake, patient-portal or thank-you pages. PageView only; no Lead, Schedule, CompleteRegistration or custom conversions (CL-HIP-01, CL-HIP-06, CL-RES-01).
- **Automatic advanced matching: OFF.** Manual advanced matching: not used (CL-HIP-01).
- **Conversions API: no patient data.** No CAPI events with identifiers or booking/patient status; no Conversion Leads/CRM-stage feedback without legal approval (CL-HIP-01, CL-RES-03).
- **No offline events, no CRM → Meta sync, no customer/patient list uploads** (CL-HIP-01, CL-HIP-02).
- **No "bypass" tools for the health restriction** (CL-RES-02).
- **Website events toggle: off on instant-form ads**; on only for an ad pointing at a reviewed generic page with the pixel (R-TRK-11).
- **Lead delivery: Meta → GoHighLevel, one way**, on a HIPAA-eligible plan with a BAA; no Zapier/Sheets/Gmail unless each has a BAA (CL-HIP-04). Instant-form questions stay non-clinical (CL-HIP-03; file 04).
- **Attribution setting: Meta default.** Meta reports leads only.
- **Outcomes are measured outside Meta.** Meta lead → GoHighLevel (contact, booking) → IntakeQ/PracticeQ (booked, showed, new patient), reconciled weekly per campaign/ad. This is the source of truth for cost per booked evaluation, show rate and cost per new patient (CL-KPI-01, CL-KPI-02, CL-KPI-03).
- **Neutral names** for everything tied to a person (R-NAM-04).

---

## 3. Open questions / contradictions in the course

1. **Is a pixel required for the Leads objective?** MC "What is Business Manager?" [6:03] says without a dataset "you will not be able to use a lead objective". The course's own instant-form builds (LOCAL "Setting Up Your Local Lead Campaign"; LG "Setting up a Meta Lead Form campaign") run on-platform with no pixel, and LG [17:23] says there is "not really that much need" for tracking on them. **Default:** the pixel is not required; the clinic runs instant forms without relying on it (CL-RES-01).
2. **Feed Meta more data vs. Meta blocking health signals.** MC/LOCAL push CAPI, offline events and AAM "on"; LWU uploads customer lists monthly. LWU "Meta Restricts Health Business Tracking" says health conversion signals are blocked and offers an unnamed "bypass". **Default:** send Meta the least data possible; no bypass, no CAPI patient data, no offline uploads (CL-HIP-01, CL-RES-02, CL-RES-03). For a covered clinic, privacy duties outrank optimization.
3. **Where the Lead event fires.** MC "Event Codes Made Simple" first puts Lead on a button before the calendar ("I've had 12 leads in, but no one's filled in my calendar"), then moves it to the confirmation URL. **Default (non-clinic):** confirmation URL. **Clinic:** no website Lead event at all (R-TRK-06).
4. **Website events on instant-form ads.** LG [17:23] turns it on "out of habit"; the garbled recap in LG "Setting up a Meta Landing page campaign" [13:50] ("I turn this off as a nice turn this on as a nice to have") is ambiguous; ECOM [19:30] says "always, always, always" on (e-commerce; not applicable to the clinic). **Default for the clinic:** off on instant-form ads (R-TRK-11).
5. **Is the ad account created automatically?** MC [3:02] "you will get one when you first started" vs [4:20] "It wouldn't be created automatically". **Default:** check; create it if it's missing, with the right currency and time zone (R-SET-04).
6. **Meta Verified.** MC: optional, support "not really" better ($9.99/month). LWU: worth it after a 3-day lockout (£10/month). **Default:** optional; Tim decides (R-SET-07).
7. **Ad set naming formula differs by lesson:** audience + age (MC), location + radius (LG/LOCAL), audience | test | date (TEST), "only what's actually in the audience" (LWU). **Default:** combine them: name only what is set, add test type and date for tests (R-NAM-02).
8. **Course is thin on several items in this file's scope.** Custom conversions are deferred to "advanced courses" and never taught; CAPI setup is "not something I can teach you"; the test-events tool is only mentioned; the health-restriction video has no transcript; the Andromeda-era structure lessons are YouTube-only. Nothing here should be read as a full CAPI or custom-conversion procedure.
9. **Attribution wording.** ECOM [10:13] says "the algorithm is working on a seven-day attribution" for view-through behaviour, while the setting shown is 7-day click / 1-day engaged-view / 1-day view. It's loose wording, not a real conflict. **Default:** leave Meta's default (R-TRK-13).
10. **Domain verification.** The course says it is "no longer required" (MC [7:57]). This file does not add a step for it. If Meta asks for it later for a specific feature, treat that as a new decision.
