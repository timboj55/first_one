# Google Group email in Apple Mail with shared delete, for the whole team

## What you asked for

1. Receive Google Group email in Apple Mail.
2. When one team member deletes a group email, it disappears from everyone's Apple Mail.
3. Works for several team members.

## Short answer

A Google Group cannot do #2, no matter how it is configured. Use a **shared Google Workspace
mailbox** instead (one extra user account, e.g. `team@movementsolutions-sc.com`), point the
group address at it, and have every team member sign that account into Apple Mail alongside
their own. Apple Mail then talks to one server-side mailbox, so delete, archive, read/unread and
flags are the same for everyone within seconds. Cost: one Workspace seat.

## Why the Group alone cannot do it

| Approach | #1 in Apple Mail | #2 shared delete | Verdict |
|---|---|---|---|
| Google Group delivers to each member's own Gmail, each member reads their own account in Apple Mail | yes | **no**: every member gets a private copy; deleting yours does nothing to anyone else's | current state, does not meet #2 |
| Google Group as Collaborative Inbox (groups.google.com) | **no**: Groups has no IMAP, Apple Mail cannot connect to it | only inside the Groups web UI; deleting a conversation there removes it from the group archive, not from members' inboxes | web only |
| Gmail delegation (delegate the shared account to each person) | **no**: delegation works only in a browser, not in Apple Mail or iOS Mail | yes (in browser) | web only |
| **Shared Workspace mailbox, each person signs into it directly in Apple Mail** | yes | **yes**: one server mailbox, IMAP state is shared | **recommended** |

## How it behaves once set up

| Action in Apple Mail (any Mac/iPhone) | What everyone else sees |
|---|---|
| Delete | message moves to the shared account's Trash on the server; gone from everyone's Inbox within the next sync (seconds to a couple of minutes). Gmail empties Trash after 30 days. |
| Archive | leaves Inbox, stays in All Mail, for everyone |
| Read / unread, flag | synced for everyone |
| Move to a mailbox (folder) | folders are Gmail labels on the server; synced for everyone |
| Reply / send | goes out as `team@...`; the sent copy is in the shared Sent for everyone |
| Draft | saved in the shared Drafts; visible to everyone (start drafts in your own account if that is not wanted) |

## Setup (about 30 minutes, Workspace super admin needed for steps 1 to 3)

### 1. Create the shared mailbox
Admin console > Directory > Users > Add new user. Suggested name `Team Inbox`, address
`team@movementsolutions-sc.com` (or reuse the group's current address, see step 3). Assign a
license. Set a strong password and store it in the team password manager (shared vault), not in
chat or email.

### 2. Make sure the account can use Apple Mail
- Admin console > Apps > Google Workspace > Gmail > End User Access: **POP and IMAP access**
  must be enabled for the organizational unit the shared user is in. Workspace admins still
  control this even though consumer Gmail removed the toggle in 2025.
- Apple Mail signs in with Google OAuth ("Sign in with Google"), which is required since Google
  stopped accepting plain passwords for Workspace in May 2025. Nothing to configure; just use the
  **Google** account type in Apple Mail, never "Other Mail Account".
- 2-Step Verification: if your Workspace enforces 2SV, the shared account needs a second factor
  that the team can share. Put its authenticator (TOTP) secret in the same shared password-manager
  vault (1Password, Bitwarden etc. can generate the codes). Do not exempt the account from 2SV;
  a shared inbox is a high-value target.
- Optional, in the shared account's Gmail settings (sign in once in a browser):
  Settings > See all settings > Forwarding and POP/IMAP: keep **Auto-Expunge on** and
  **"Move the message to the Trash"** (defaults). These make an Apple Mail delete a real
  server-side delete. Under Labels, you can uncheck "Show in IMAP" for Spam, Important and Starred
  to keep Apple Mail's sidebar tidy.

### 3. Route the group's mail into the shared mailbox
Pick one:

- **A. Keep the Google Group (simplest, keeps the address and the web archive).**
  Groups > your group > Members: add `team@...` as a member. Then for every human member set
  Subscription to **No email** (or remove them). Mail to the group now lands only in the shared
  mailbox; the group archive still exists at groups.google.com. Members stop getting private
  copies, which is what makes #2 possible.
- **B. Turn the group address into the shared mailbox's address.** Delete the group, then add its
  address as an **alternate email (alias)** on the shared user (Admin console > Users > user >
  User information > Alternate emails). Mail to the old address now goes straight to the shared
  mailbox. You lose the Groups web archive; existing group mail is not migrated.

If the group address is what patients and vendors already use, choose A; nothing changes for
senders.

### 4. Add the shared account on each team member's Mac
Mail > Settings (or System Settings) > Internet Accounts > Add Account > **Google** > sign in as
`team@...` with the shared credentials (and the shared 2SV code) > tick **Mail only** (untick
Contacts, Calendars, Notes). Repeat on iPhone/iPad: Settings > Mail > Accounts > Add Account >
Google.

Recommended Apple Mail tweaks per person:
- Mail > Settings > Composing > "Send new messages from": leave as **Account of selected
  mailbox**, so replies from the Team Inbox go out as `team@` and replies from your own inbox
  go out as you.
- Enable **Mail > Settings > Viewing > Show most recent message at top** is personal taste;
  nothing else is needed for sync.

### 5. Try it
Send a test email to the group address. It should appear in the Team Inbox on every device.
Delete it on one Mac; within a minute it should leave every other Inbox and sit in the Team
Inbox's Trash.

## Sizing for a 4-person team

Gmail allows 15 IMAP connections to the shared account at once. Rough budget:

| Device | Connections it holds while Mail is open |
|---|---|
| Apple Mail on a Mac | 2 to 5 (one per mailbox being synced, more during a big fetch) |
| iOS Mail on iPhone/iPad (Fetch) | 1 to 2, only while fetching |
| iOS Mail set to Push or Manual | 2 to 3, held longer |

Plan that works for 4 people:
- **All 4 Macs** on the shared account: about 8 to 10 connections at peak. Fine.
- **Phones for all 4 are workable** if every phone is set to Fetch every 15 minutes
  (Settings > Mail > Accounts > Fetch New Data), which adds roughly 4 to 6 short-lived
  connections. Push or Manual on the phones is what tips a team this size over the limit.
- Do not add the shared account to Gmail web on a sixth device permanently, and do not connect
  any other IMAP tool (backup apps, CRM mail sync) to it.

If the team grows past 5, or phones are left on Push, you will start to see
"Too many simultaneous connections". At that point the fix is to trim devices or move to a
shared-inbox product; Gmail does not let you raise the limit.

## Limits to know about

- **15 simultaneous IMAP connections per Gmail account.** Apple Mail on a Mac holds several
  connections per account, and iOS Mail adds more. In practice the shared mailbox works
  comfortably for **about 4 to 5 people on Macs, with phones for one or two of them** (see the sizing section above). Beyond that you will see
  "Too many simultaneous connections" and the account intermittently stops syncing. Mitigations:
  add the shared account only on the devices that need it, and on iPhone set Settings > Mail >
  Accounts > Fetch New Data > Team Inbox to **Fetch** every 15 or 30 minutes rather than
  Push/Manual polling loops.
- **No "who is handling this" state.** Apple Mail has no assignment. Convention that works:
  flag (colour) a message when you take it, archive when done. If assignment matters, the
  Collaborative Inbox in a browser or a shared-inbox product (Missive, Front, Hiver) does it, but
  none of those is Apple Mail.
- **Shared password.** Rotate it when someone leaves the team, and re-sign-in on the remaining
  devices. Admin console can also sign the account out of all sessions immediately.
- **Search and storage** are the shared account's, not each person's. Deleted mail is gone for
  everyone after 30 days in Trash; use Archive rather than Delete for anything you might need.

## What this costs

One Google Workspace license for the shared user. No other software.

## Sources checked (Sept 2026)

- Gmail Help, "Delegate & collaborate on email": delegated accounts cannot be used in the Gmail
  or Mail apps, browser only. https://support.google.com/mail/answer/138350
- Google Workspace Learning Center, "Use a group as a Collaborative Inbox": collaborative
  features work only at groups.google.com; deleting a conversation removes it from the group.
  https://support.google.com/a/users/answer/167430
- Google Workspace Admin Help, "Turn POP & IMAP on or off for users".
  https://support.google.com/a/answer/105694
- Gmail IMAP connection limit of 15 and the "Too many simultaneous connections" error.
  https://workspaceforensics.com/gmail-deliverability/gmail-sync-connection/imap-too-many-simultaneous-connections-15/
