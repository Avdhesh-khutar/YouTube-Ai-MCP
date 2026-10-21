# YouTube AI MCP

OAuth-protected Model Context Protocol (MCP) server for Claude, hosted on Cloudflare Workers.

## Current tools

- `youtube_video_research`: searches public YouTube videos by keyword, ordered by view count. Uses YouTube Data API v3.
- `youtube_training_video_outline`: creates a draft video outline, title ideas, and production checklist. Does not publish videos.
- `youtube_competitor_analysis`: compares public search results and available public video statistics (views, likes, comments), calculates simple engagement rates, and suggests content opportunities. It does not access private competitor analytics.
- `youtube_channel_analytics`: reads the authorized channel owner's private YouTube Analytics summary for a date range. Requires completing Google OAuth at `/google/connect`.
- `youtube_upload_video_from_url`: uploads a finished video file from a direct HTTPS URL as PRIVATE. Does not generate videos and requires the YouTube upload OAuth scope.

## Private YouTube video upload

- The `youtube_upload_video_from_url` tool uploads an already-rendered video from a direct public HTTPS URL to the connected owner's channel.
- It always sets `privacyStatus: private`; it never publishes or schedules a public video.
- The source URL must not redirect, must return a `video/*` content type, and must be no larger than 50 MB.
- Google OAuth now requests `https://www.googleapis.com/auth/youtube.upload` in addition to the existing read-only scopes. After this deploy, the owner must reconnect at `/google/connect` and approve the new permission. Do not share credentials in chat.
- Before retrying an upload after a network error, check YouTube Studio to avoid duplicate videos.

## Automated video creation limits and next step

This Worker does **not** generate a finished video, voiceover, captions, or thumbnail by itself. The free-budget workflow still needs a video-generation/rendering service or a local renderer that produces a direct HTTPS video file. The upload tool is the first publishing component; a daily unattended pipeline is not complete until a renderer, persistent job scheduler, failure notifications, and a secure source-file handoff are configured. Do not describe this as fully automatic until those parts have been tested.

## Validation and CI

- `npm test` runs unit tests for strict calendar-date validation, TypeScript type-checking, and a Wrangler deployment dry run.
- Analytics date inputs must be real calendar dates, ordered start-to-end, and must not end in the future.
- Google token refresh and Analytics API network failures are handled without returning credentials.

## YouTube API quota awareness

- YouTube Data API quota is separate from Cloudflare Workers usage.
- The search endpoint is quota-expensive compared with video statistics. Avoid repeatedly running research or competitor-analysis tools for the same query.
- Competitor analysis normally makes one `search.list` request and, when search results contain video IDs, one `videos.list` request for statistics. The statistics request batches the returned IDs.
- Use a small `maxResults` value (default 5) unless more results are genuinely needed.
- Public statistics can be unavailable or change after retrieval. Missing values are returned as `null`; they must not be interpreted as zero.
- `viewsPerDay` is a rough lifetime average since publication, not recent daily view velocity and not a forecast.
- Engagement rates are descriptive ratios only; they do not prove why a video performed well or predict future views.

## Cloudflare setup

The Worker uses a Cloudflare KV namespace bound as `OAUTH_KV`.

Configure these as Worker secrets in Cloudflare → Workers & Pages → `youtube-ai-mcp` → Settings → Variables and Secrets:

- `OAUTH_ADMIN_PASSWORD`: a long, unique password used only for the connector authorization page. Never use your Google password.
- `YOUTUBE_API_KEY`: a Google API key restricted to YouTube Data API v3.

The previous `MCP_ACCESS_TOKEN` is not used by this OAuth flow. Do not share secrets in chat or commit them to GitHub.

## Connect Claude

After a GitHub-triggered Cloudflare deployment succeeds:

1. Add or open the custom remote MCP connector.
2. Endpoint: `https://youtube-ai-mcp.mkkhutar2.workers.dev/mcp`
3. Use OAuth when Claude requests authorization.
4. Enter the `OAUTH_ADMIN_PASSWORD` only on the connector's authorization page, after verifying the client and redirect host.
5. Approve individual tool calls as appropriate.

## Health check

`https://youtube-ai-mcp.mkkhutar2.workers.dev/health`

## Connect your own YouTube channel (private Analytics)

The Worker now includes a separate Google OAuth flow for the channel owner and the `youtube_channel_analytics` tool. This is separate from Claude's MCP connector authorization.

1. In Google Cloud project `Youtube-Claude`, enable **YouTube Analytics API** (YouTube Data API v3 should remain enabled for public research tools).
2. Configure the OAuth consent screen. If the app is in Testing mode, add the Google account that owns/manages the channel as a test user.
3. Create an OAuth Client ID of type **Web application**.
4. Add this exact Authorized redirect URI:
   `https://youtube-ai-mcp.mkkhutar2.workers.dev/google/callback`
5. In Cloudflare → Workers & Pages → `youtube-ai-mcp` → Settings → Variables and Secrets, add these as secrets:
   - `GOOGLE_OAUTH_CLIENT_ID` — the OAuth client ID from Google Cloud.
   - `GOOGLE_OAUTH_CLIENT_SECRET` — the matching OAuth client secret.
   Keep the existing `OAUTH_ADMIN_PASSWORD` and `OAUTH_KV` binding configured.
6. Deploy the latest Worker. Open `https://youtube-ai-mcp.mkkhutar2.workers.dev/google/connect`, enter the **Worker admin password** (not your Google password), and then sign in on Google's own page to grant read-only access.
7. In Claude, call `youtube_channel_analytics` with `startDate` and `endDate` in `YYYY-MM-DD` format.

The tool reports channel-level views, estimated minutes watched, average view duration, subscribers gained, and subscribers lost for the requested date range. Access depends on the signed-in Google account's channel permissions and available Analytics data. The Google refresh token is stored in the configured Cloudflare KV namespace; never share it. Revoke access from your Google Account permissions page if you want to disconnect.

## Important limits

- This service does not guarantee views, automate uploads, or publish videos.
- Private channel analytics and private competitor analytics are not implemented.
- The tools use public YouTube metadata/statistics and can return incomplete results.
- A successful deployment does not by itself prove that every API request or edge case works; avoid unnecessary live tests because they consume quota.

## Security

- OAuth tokens are managed by Cloudflare Workers OAuth Provider and stored using `OAUTH_KV`.
- Keep `OAUTH_ADMIN_PASSWORD` strong and unique; never paste it into chat.
- Restrict the YouTube API key to YouTube Data API v3 and monitor quota in Google Cloud Console.
- OAuth for this MCP connector is separate from Google OAuth for accessing a user's own private channel data.
