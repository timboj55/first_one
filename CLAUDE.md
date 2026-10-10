# Working with Tim (Movement Solutions)

## Standing instructions
- **Request API access for anything you could do for Tim.** Whenever a task involves a service where an API, connector
  or service account would let you do the work yourself instead of walking him through clicks, ask for that access
  (and say exactly how to set it up), rather than defaulting to click-by-click instructions.
- **Get the tools you need up front, and do as much as possible yourself.** At the start of a task, work out every
  connector, API, network domain, credential and browser capability it will need, and ask Tim for all of them in one
  go, so he isn't fixing access piecemeal halfway through.
- Tim handles account creation, payment, passwords and API keys himself. Tell him exactly where to click and what to
  enter. Never enter those yourself, and never ask him to paste a key into the chat.
- Ask before anything that submits, purchases, confirms or spends credits (e.g. a HeyGen render).
- When Tim needs to do something in a browser, give click-by-click steps one at a time and accept screenshots.

## Access checklist for video/ad work
- **HeyGen API**: key is injected by the proxy for api.heygen.com (v3 API). IDs are in `heygen_ids.txt`.
- **Google Drive**: Drive connector (search, copy, create, read docs); it cannot download large videos. For video, use
  the Drive API (`https://www.googleapis.com/drive/v3/files/{id}?alt=media`) as service account
  `claude-drive-reader@claude-drive-reader-511215.iam.gserviceaccount.com` (network secret for *.googleapis.com,
  injected automatically). It sees only folders Tim shares with it (Ad Footage Library). Google has a per-file
  download quota: don't bulk-download hundreds of clips at once (that blocked everything for ~24h in Oct 2026);
  download only the clips an edit needs.
- **Stock footage**: Pixabay (env var `PIXABAY_API_KEY`; key goes in the URL, so it must be an environment variable,
  not a header secret; allow pixabay.com and cdn.pixabay.com). Pexels has paused new API keys.
- **Transcription**: faster-whisper works once huggingface.co, us.aws.cdn.hf.co and cas-server.xethub.hf.co are allowed.
- **Browser control**: cloud sessions have no access to Tim's Chrome. For browser tasks (Google Cloud Console, Meta Ads
  Manager, HeyGen UI), suggest a local session on his Mac with the Claude in Chrome extension
  (https://code.claude.com/docs/en/chrome).
- New environment variables only load when a session starts; new allowed domains take effect immediately.

## Keep out of this repo
- Patient footage descriptions, transcripts and other patient details (keep those in Tim's Drive, not git).
- Rendered videos and other large media.
