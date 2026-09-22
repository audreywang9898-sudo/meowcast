# Instagram auto-publishing setup

The publishing code is ready, but credentials must never be committed to the repository.

Add these GitHub Actions repository secrets:

- IG_USER_ID — your Instagram professional account ID.
- IG_ACCESS_TOKEN — a Meta access token with the permissions required for Instagram content publishing.
- REEL_PUBLIC_URL — temporary test URL pointing directly to an MP4 that Meta can fetch over HTTPS.

Then run **Publish Meowcast Reel** manually once. After the test succeeds, merge publishing into the daily workflow and replace the temporary public URL with automated hosting of each generated Reel.

Never paste tokens into source files, issues, commits, or chat screenshots.
