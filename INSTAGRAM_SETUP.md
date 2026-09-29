# Instagram auto-publishing setup

The publishing code is ready, but credentials must never be committed to the repository.

Add these GitHub Actions repository secrets:

- IG_USER_ID — your Instagram professional account ID.
- IG_ACCESS_TOKEN — a Meta access token with the permissions required for Instagram content publishing.
- REEL_PUBLIC_URL — temporary test URL pointing directly to an MP4 that Meta can fetch over HTTPS.

Then run **Publish Meowcast Reel** manually once. After the test succeeds, merge publishing into the daily workflow and replace the temporary public URL with automated hosting of each generated Reel.

Never paste tokens into source files, issues, commits, or chat screenshots.


## Melbourne Meowcast

The Melbourne workflow is already wired to separate credentials so it cannot publish to the Taipei account accidentally.

Add these GitHub Actions repository secrets:

- `MELBOURNE_IG_USER_ID` — Instagram professional account ID for Melbourne Cat.
- `MELBOURNE_IG_ACCESS_TOKEN` — access token for the Melbourne Cat account with Instagram content publishing permission.
- `MELBOURNE_PRODUCTION_ENABLED` — keep unset/false until the connection test and one manual publish succeed; set to `true` only when automatic scheduling should go live.

The existing `MEDIA_REPO_TOKEN` can be reused.

Safety sequence:
1. Run **Check Melbourne Instagram Connection**. It only reads id/username and does not publish.
2. Run **Melbourne Meowcast** manually with `publish=true` for one production test.
3. Verify the workflow log contains `Meta status: FINISHED` and `Published: {'id': ...}`.
4. Only then set `MELBOURNE_PRODUCTION_ENABLED=true`.

Never paste access tokens into commits, issues, screenshots, or chat.
