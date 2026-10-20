# YouTube AI MCP (starter)

A Cloudflare Workers MCP starter for researching public YouTube videos and planning training-video content.

## Implemented tools
- `youtube_video_research`: searches public YouTube videos by keyword using YouTube Data API v3.
- `youtube_training_video_outline`: drafts a training-video outline, title ideas, and a description checklist.

## Current security
- `/health` is public and reports service health only.
- The MCP endpoint requires `Authorization: Bearer <MCP_ACCESS_TOKEN>`.
- Keep `MCP_ACCESS_TOKEN` and `YOUTUBE_API_KEY` in Cloudflare Worker secrets. Never commit secrets to this repository.
- Restrict the Google API key to YouTube Data API v3.

## Important: Claude web connector is not yet ready
Claude's custom connector screen does not provide a field for an arbitrary static bearer token. Selecting “No sign-in” cannot work with the current bearer-protected endpoint; it produces HTTP 401. Do not remove endpoint authentication as a workaround because that would expose the YouTube API quota to unauthenticated callers.

A proper OAuth authorization/consent flow (or another supported, securely authenticated connection method) must be implemented before connecting this server through Claude's web custom connector. The current code does not yet implement that OAuth flow.

## Not yet implemented
- Private channel analytics.
- Changing existing video titles/descriptions.
- Uploading or publishing videos.
These require Google OAuth authorization from the channel owner and additional implementation. Views cannot be guaranteed.

## Deploy
1. Connect this repository to Cloudflare Workers using Workers & Pages → Create application → Import a repository.
2. Build command: `npm run build`; deploy command: `npx wrangler deploy`.
3. Add Worker secrets in Cloudflare Settings → Variables and Secrets: `MCP_ACCESS_TOKEN` (long random secret) and `YOUTUBE_API_KEY` (YouTube Data API v3 key).

## Build note
The build script intentionally avoids running a separate TypeScript compiler because the Cloudflare build environment previously hit a JavaScript heap out-of-memory error. Wrangler bundles the Worker during deployment. Verify the newest deployment logs after each code change.