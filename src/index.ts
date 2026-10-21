import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import OAuthProvider, {
  AuthorizationError,
  type OAuthHelpers,
  type ConsentDescription,
} from "@cloudflare/workers-oauth-provider";
import { z } from "zod/v4";
import { isValidDateOnly } from "./date-validation";

interface Env {
  OAUTH_KV: KVNamespace;
  OAUTH_PROVIDER: OAuthHelpers;
  OAUTH_ADMIN_PASSWORD?: string;
  YOUTUBE_API_KEY?: string;
  GOOGLE_OAUTH_CLIENT_ID?: string;
  GOOGLE_OAUTH_CLIENT_SECRET?: string;
  DAILY_UPLOAD_TOKEN?: string;
}

const MCP_PATH = "/mcp";
const MCP_RESOURCE = "https://youtube-ai-mcp.mkkhutar2.workers.dev/mcp";
const SCOPES = ["mcp:read"];

async function safeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response | null> {
  try {
    return await fetch(input, init);
  } catch {
    return null;
  }
}

async function safeJson<T>(response: Response): Promise<T | null> {
  try {
    return await response.json() as T;
  } catch {
    return null;
  }
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);
}

function page(title: string, body: string, status = 200): Response {
  return new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(title)}</title><style>body{font:16px system-ui;max-width:620px;margin:48px auto;padding:0 18px;color:#172033}main{border:1px solid #ddd;border-radius:14px;padding:24px}input{box-sizing:border-box;width:100%;padding:12px;margin:8px 0 18px}button{padding:12px 18px;border:0;border-radius:8px;background:#155eef;color:white;font-weight:600}small{color:#555}</style></head><body><main><h1>${escapeHtml(title)}</h1>${body}</main></body></html>`, {
    status,
    headers: { "content-type": "text/html; charset=utf-8", "x-content-type-options": "nosniff", "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'", "referrer-policy": "no-referrer" },
  });
}

const GOOGLE_REDIRECT_URI = "https://youtube-ai-mcp.mkkhutar2.workers.dev/google/callback";
const GOOGLE_SCOPES = [
  "https://www.googleapis.com/auth/yt-analytics.readonly",
  "https://www.googleapis.com/auth/youtube.readonly",
  "https://www.googleapis.com/auth/youtube.upload",
].join(" ");

type GoogleTokenSet = { access_token?: string; refresh_token?: string };


function htmlMessage(title: string, message: string, status = 200): Response {
  return page(title, `<p>${escapeHtml(message)}</p>`, status);
}

async function googleConnect(request: Request, env: Env): Promise<Response> {
  if (!env.OAUTH_ADMIN_PASSWORD || !env.GOOGLE_OAUTH_CLIENT_ID || !env.GOOGLE_OAUTH_CLIENT_SECRET) {
    return htmlMessage("Google OAuth setup required", "Configure OAUTH_ADMIN_PASSWORD, GOOGLE_OAUTH_CLIENT_ID, and GOOGLE_OAUTH_CLIENT_SECRET as Cloudflare Worker secrets.", 503);
  }
  if (request.method === "GET") {
    return page("Connect your YouTube channel", `
      <p>This starts Google's official authorization flow for the channel owner.</p>
      <p>Requested access includes YouTube channel read access, Analytics reports, and permission to upload videos as private. Uploads remain private until you review them.</p>
      <form id="google-connect-form" method="post" action="/google/connect">
        <label for="password">Worker admin password</label>
        <input id="password" name="password" type="password" autocomplete="current-password" required>
        <button id="google-connect-button" type="submit">Continue to Google</button>
        <p id="connect-status" role="status" aria-live="polite"></p>
      </form>
      <script>
        const form = document.getElementById("google-connect-form");
        const button = document.getElementById("google-connect-button");
        const status = document.getElementById("connect-status");
        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          button.disabled = true;
          button.textContent = "Connecting...";
          status.textContent = "Contacting the authorization service...";
          try {
            const response = await fetch(form.action, {
              method: "POST",
              body: new FormData(form),
              headers: { "Accept": "application/json" },
              redirect: "manual"
            });
            if (response.type === "opaqueredirect") {
              status.textContent = "Opening Google...";
              window.location.href = "https://youtube-ai-mcp.mkkhutar2.workers.dev/google/connect";
              return;
            }
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.error || "Request failed (HTTP " + response.status + ").");
            if (!data.authorizationUrl) throw new Error("Authorization link was not returned. Please retry.");
            window.location.assign(data.authorizationUrl);
          } catch (error) {
            status.textContent = error instanceof Error ? error.message : "Could not connect. Please retry.";
            button.disabled = false;
            button.textContent = "Continue to Google";
          }
        });
      </script>
      <p><small>Do not enter your Google account password here. You will sign in only on Google's website.</small></p>
    `);
  }
  if (request.method !== "POST") return new Response("Method Not Allowed", { status: 405, headers: { allow: "GET, POST" } });
  const form = await request.formData();
  if (String(form.get("password") ?? "") !== env.OAUTH_ADMIN_PASSWORD) {
    return htmlMessage("Sign-in failed", "The Worker admin password was incorrect.", 401);
  }
  const state = crypto.randomUUID();
  const verifierBytes = crypto.getRandomValues(new Uint8Array(32));
  const verifier = btoa(String.fromCharCode(...verifierBytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  const challenge = btoa(String.fromCharCode(...new Uint8Array(digest))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  await env.OAUTH_KV.put(`google-oauth-state:${state}`, JSON.stringify({ verifier, createdAt: Date.now() }), { expirationTtl: 600 });

  const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authUrl.searchParams.set("client_id", env.GOOGLE_OAUTH_CLIENT_ID);
  authUrl.searchParams.set("redirect_uri", GOOGLE_REDIRECT_URI);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("scope", GOOGLE_SCOPES);
  authUrl.searchParams.set("access_type", "offline");
  authUrl.searchParams.set("prompt", "consent");
  authUrl.searchParams.set("include_granted_scopes", "true");
  authUrl.searchParams.set("state", state);
  authUrl.searchParams.set("code_challenge", challenge);
  authUrl.searchParams.set("code_challenge_method", "S256");
  if (request.headers.get("accept")?.includes("application/json")) {
    return Response.json({ authorizationUrl: authUrl.toString() }, {
      headers: { "cache-control": "no-store", "x-content-type-options": "nosniff" },
    });
  }
  return Response.redirect(authUrl.toString(), 302);
}

async function googleCallback(request: Request, env: Env): Promise<Response> {
  if (!env.GOOGLE_OAUTH_CLIENT_ID || !env.GOOGLE_OAUTH_CLIENT_SECRET) {
    return htmlMessage("Google OAuth setup required", "Configure Google OAuth client ID and client secret in Cloudflare.", 503);
  }
  const url = new URL(request.url);
  const googleError = url.searchParams.get("error");
  if (googleError) return htmlMessage("Google authorization cancelled", `Google returned: ${googleError}`, 400);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (!code || !state) return htmlMessage("Invalid callback", "Google callback is missing the required code or state.", 400);

  const stateKey = `google-oauth-state:${state}`;
  const stateValue = await env.OAUTH_KV.get(stateKey);
  if (!stateValue) return htmlMessage("Expired authorization", "This authorization request is invalid or expired. Start again from /google/connect.", 400);
  await env.OAUTH_KV.delete(stateKey);
  let stateData: { verifier: string; createdAt: number };
  try {
    stateData = JSON.parse(stateValue) as { verifier: string; createdAt: number };
  } catch {
    return htmlMessage("Invalid authorization state", "This authorization request is invalid. Start again from /google/connect.", 400);
  }
  if (!stateData.verifier || !Number.isFinite(stateData.createdAt) || Date.now() - stateData.createdAt > 600_000) {
    return htmlMessage("Expired authorization", "This authorization request expired. Start again from /google/connect.", 400);
  }

  let tokenResponse: Response;
  try {
    tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        code,
        client_id: env.GOOGLE_OAUTH_CLIENT_ID,
        client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET,
        redirect_uri: GOOGLE_REDIRECT_URI,
        grant_type: "authorization_code",
        code_verifier: stateData.verifier,
      }),
    });
  } catch {
    return htmlMessage("Google connection unavailable", "Could not reach Google's token service. Please start the connection again later.", 502);
  }
  if (!tokenResponse.ok) return htmlMessage("Google token exchange failed", `Google returned HTTP ${tokenResponse.status}. Check the OAuth client and exact callback URL.`, 502);
  let tokens: GoogleTokenSet;
  try {
    tokens = await tokenResponse.json() as GoogleTokenSet;
  } catch {
    return htmlMessage("Google token response invalid", "Google returned an unreadable token response. Please reconnect.", 502);
  }
  if (!tokens.refresh_token) {
    return htmlMessage("Refresh token missing", "Google did not return a refresh token. Remove this app's access from your Google Account and reconnect to grant consent again.", 502);
  }
  await env.OAUTH_KV.put("youtube-google-refresh-token", tokens.refresh_token);
  await env.OAUTH_KV.put("youtube-google-connected-at", new Date().toISOString());
  return page("YouTube authorization completed", `
    <p>Google authorization succeeded. The refresh token is stored in Cloudflare KV and is not displayed.</p>
    <p>You can close this page and return to Claude.</p>
  `);
}

async function getGoogleAccessToken(env: Env): Promise<string | null> {
  if (!env.GOOGLE_OAUTH_CLIENT_ID || !env.GOOGLE_OAUTH_CLIENT_SECRET) return null;
  const refreshToken = await env.OAUTH_KV.get("youtube-google-refresh-token");
  if (!refreshToken) return null;
  try {
    const response = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: env.GOOGLE_OAUTH_CLIENT_ID,
        client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET,
        refresh_token: refreshToken,
        grant_type: "refresh_token",
      }),
    });
    if (!response.ok) return null;
    const tokens = await response.json() as GoogleTokenSet;
    return tokens.access_token ?? null;
  } catch {
    return null;
  }
}

async function fetchAnalyticsReport(accessToken: string, params: Record<string, string>): Promise<{ ok: boolean; status: number; data: unknown }> {
  const url = new URL("https://youtubeanalytics.googleapis.com/v2/reports");
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  try {
    const response = await fetch(url, { headers: { authorization: `Bearer ${accessToken}` } });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, status: response.status, data };
  } catch {
    return { ok: false, status: 0, data: { error: "network_error" } };
  }
}

function consentPage(details: ConsentDescription, handle: string): Response {
  const name = escapeHtml(details.clientName);
  const scopeHtml = details.scope.map((scope) => `<label><input type="checkbox" name="scope" value="${escapeHtml(scope)}" checked> ${escapeHtml(scope)}</label><br>`).join("");
  const domain = details.clientDomain
    ? `Client domain: <strong>${escapeHtml(details.clientDomain)}</strong>`
    : "The client name is supplied by the connecting app and is not independently verified.";
  return page("Connect YouTube AI Assistant", `
    <p><strong>${name}</strong> is requesting access to this MCP service.</p>
    <p>${domain}</p>
    <p>Authorization will return to: <strong>${escapeHtml(details.redirectHost)}</strong></p>
    ${details.redirectIsLoopback ? "<p><strong>Warning:</strong> this sends authorization to an app on your device. Continue only if you just started this connection.</p>" : ""}
    <p>Requested permissions (uncheck anything you do not want to grant):</p><div>${scopeHtml}</div>
    <p>This password is only for this MCP connector; it is not your Google password.</p>
    <form method="post" action="/authorize">
      <input type="hidden" name="handle" value="${escapeHtml(handle)}">
      <label for="password">Connector admin password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required>
      <button name="decision" value="approve" type="submit">Sign in and allow</button>
      <button name="decision" value="deny" type="submit" formnovalidate>Deny</button>
    </form>
    <p><small>Only the permissions listed above are granted. Never enter your Google account password here.</small></p>
  `);
}

async function authorize(request: Request, env: Env): Promise<Response> {
  if (!env.OAUTH_ADMIN_PASSWORD) {
    return page("Setup required", "<p>The owner must add the OAUTH_ADMIN_PASSWORD secret in Cloudflare before connecting Claude.</p>", 503);
  }

  const oauth = env.OAUTH_PROVIDER;
  try {
    if (request.method === "GET") {
      const oauthRequest = await oauth.parseAuthRequest(request);
      const details = await oauth.describeConsent(oauthRequest);
      const consent = await oauth.beginConsent(oauthRequest);
      const response = consentPage(details, consent.handle);
      const headers = new Headers(consent.headers);
      for (const [key, value] of response.headers) {
        if (!headers.has(key)) headers.set(key, value);
      }
      headers.set("content-type", "text/html; charset=utf-8");
      return new Response(response.body, { headers });
    }

    if (request.method === "POST") {
      const form = await request.formData();
      const handle = String(form.get("handle") ?? "");
      const decision = String(form.get("decision") ?? "deny");
      if (decision !== "approve") {
        const denied = await oauth.denyConsent(request, handle);
        return new Response(null, { status: 302, headers: denied.headers });
      }

      const suppliedPassword = String(form.get("password") ?? "");
      if (suppliedPassword.length < 1 || suppliedPassword !== env.OAUTH_ADMIN_PASSWORD) {
        return page("Sign-in failed", "<p>The connector password was not correct. Return to the previous page and try again.</p>", 401);
      }

      const requestedScopes = form.getAll("scope").map(String).filter((scope) => SCOPES.includes(scope));
      const approved = await oauth.approveConsent(request, handle, { scope: requestedScopes });
      const { redirectTo } = await oauth.completeAuthorization({
        request: approved.request,
        userId: "channel-owner",
        metadata: { clientName: "Claude MCP client" },
        scope: approved.request.scope,
        props: { userId: "channel-owner" },
      });
      const headers = new Headers(approved.headers);
      headers.set("location", redirectTo);
      return new Response(null, { status: 302, headers });
    }
    return new Response("Method Not Allowed", { status: 405, headers: { allow: "GET, POST" } });
  } catch (error) {
    if (error instanceof AuthorizationError && error.redirectTo) {
      return Response.redirect(error.redirectTo, 302);
    }
    if (error instanceof AuthorizationError) {
      return page("Authorization request error", escapeHtml(error.description), 400);
    }
    return page("Authorization unavailable", "The authorization request could not be completed. Please try connecting again.", 500);
  }
}


async function automatedPrivateUpload(request: Request, env: Env): Promise<Response> {
  if (!env.DAILY_UPLOAD_TOKEN) {
    return Response.json({ error: "Daily upload endpoint is not configured. Add DAILY_UPLOAD_TOKEN as a Cloudflare Worker secret." }, { status: 503 });
  }
  const supplied = request.headers.get("authorization") ?? "";
  if (supplied.length !== env.DAILY_UPLOAD_TOKEN.length + 7 || !supplied.startsWith("Bearer ") ||
      supplied.slice(7) !== env.DAILY_UPLOAD_TOKEN) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (request.method !== "POST") {
    return Response.json({ error: "Method not allowed" }, { status: 405, headers: { allow: "POST" } });
  }
  const length = Number(request.headers.get("content-length") ?? "0");
  if (length > 48 * 1024 * 1024) {
    return Response.json({ error: "Video package exceeds the 48 MB upload limit." }, { status: 413 });
  }
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return Response.json({ error: "Expected multipart form data with a video file." }, { status: 400 });
  }
  const video = form.get("video");
  if (!(video instanceof File) || video.size < 1 || video.size > 47 * 1024 * 1024 || !video.type.startsWith("video/")) {
    return Response.json({ error: "Provide a video file no larger than 47 MB." }, { status: 400 });
  }
  const title = String(form.get("title") ?? "Daily YouTube explainer").trim().slice(0, 100);
  const description = String(form.get("description") ?? "Automatically generated draft. Please review in YouTube Studio.").slice(0, 5000);
  const tags = String(form.get("tags") ?? "YouTubeGrowth,CreatorTips").split(",").map((tag) => tag.trim()).filter(Boolean).slice(0, 15);
  const accessToken = await getGoogleAccessToken(env);
  if (!accessToken) {
    return Response.json({ error: "YouTube channel is not connected or Google token refresh failed. Reconnect at /google/connect." }, { status: 401 });
  }
  const metadata = {
    snippet: { title, description, tags, categoryId: "27" },
    status: { privacyStatus: "private", selfDeclaredMadeForKids: false },
  };
  const init = await safeFetch("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", {
    method: "POST",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json; charset=UTF-8",
      "x-upload-content-type": video.type || "video/mp4",
      "x-upload-content-length": String(video.size),
    },
    body: JSON.stringify(metadata),
  });
  if (!init) return Response.json({ error: "Could not reach YouTube upload service. Check Studio before retrying." }, { status: 502 });
  if (!init.ok) {
    const detail = (await init.text().catch(() => "")).slice(0, 400);
    return Response.json({ error: `YouTube upload initialization failed (HTTP ${init.status}). ${detail}` }, { status: 502 });
  }
  const uploadUrl = init.headers.get("location");
  if (!uploadUrl || !uploadUrl.startsWith("https://")) {
    return Response.json({ error: "YouTube did not return a valid resumable upload URL." }, { status: 502 });
  }
  const bytes = await video.arrayBuffer();
  const uploaded = await safeFetch(uploadUrl, {
    method: "PUT",
    headers: { authorization: `Bearer ${accessToken}`, "content-type": video.type || "video/mp4", "content-length": String(bytes.byteLength) },
    body: bytes,
  });
  if (!uploaded) return Response.json({ error: "Upload connection failed. Check YouTube Studio before retrying to avoid duplicates." }, { status: 502 });
  const data = await safeJson<{ id?: string; snippet?: { title?: string }; status?: { privacyStatus?: string } }>(uploaded);
  if (!uploaded.ok || !data?.id) {
    return Response.json({ error: `YouTube upload failed (HTTP ${uploaded.status}).`, detail: data }, { status: 502 });
  }
  return Response.json({
    uploaded: true,
    videoId: data.id,
    title: data.snippet?.title ?? title,
    privacyStatus: data.status?.privacyStatus ?? "private",
    url: `https://www.youtube.com/watch?v=${data.id}`,
    nextStep: "Review in YouTube Studio. This endpoint always uploads as PRIVATE.",
  }, { headers: { "cache-control": "no-store", "x-content-type-options": "nosniff" } });
}

function createServer(env: Env): McpServer {
  const youtubeApiKey = env.YOUTUBE_API_KEY;
  const server = new McpServer({ name: "youtube-ai-mcp", version: "0.5.0" });

  server.registerTool(
    "youtube_video_research",
    {
      description: "Search public YouTube videos by keyword. Does not access private channel analytics.",
      inputSchema: z.object({
        query: z.string().min(2).max(120).describe("Topic or keyword"),
        maxResults: z.number().int().min(1).max(10).optional().describe("Number of results, default 5"),
      }),
    },
    async ({ query, maxResults }) => {
      if (!youtubeApiKey) {
        return { content: [{ type: "text", text: "Not configured: add YOUTUBE_API_KEY as a Cloudflare Worker secret." }], isError: true };
      }
      const url = new URL("https://www.googleapis.com/youtube/v3/search");
      url.searchParams.set("part", "snippet");
      url.searchParams.set("type", "video");
      url.searchParams.set("order", "viewCount");
      url.searchParams.set("q", query);
      url.searchParams.set("maxResults", String(maxResults ?? 5));
      url.searchParams.set("key", youtubeApiKey);
      const response = await safeFetch(url);
      if (!response) {
        return { content: [{ type: "text", text: "Could not reach YouTube Data API. Check network/service status and retry later." }], isError: true };
      }
      if (!response.ok) {
        return { content: [{ type: "text", text: `YouTube API returned HTTP ${response.status}. Check the API key, YouTube Data API v3 enablement, restrictions, and quota.` }], isError: true };
      }
      const data = await safeJson<{ items?: Array<{ id?: { videoId?: string }; snippet?: { title?: string; channelTitle?: string; publishedAt?: string; description?: string } }> }>(response);
      if (!data) {
        return { content: [{ type: "text", text: "YouTube API returned an unreadable response. Please retry later." }], isError: true };
      }
      const videos = (data.items ?? []).map((item) => ({
        videoId: item.id?.videoId ?? "",
        title: item.snippet?.title ?? "",
        channel: item.snippet?.channelTitle ?? "",
        publishedAt: item.snippet?.publishedAt ?? "",
        description: (item.snippet?.description ?? "").slice(0, 300),
        url: item.id?.videoId ? `https://www.youtube.com/watch?v=${item.id.videoId}` : "",
      }));
      return { content: [{ type: "text", text: JSON.stringify({ query, note: "Public results ordered by view count; this does not predict or guarantee future views.", videos }, null, 2) }] };
    },
  );

  server.registerTool(
    "youtube_training_video_outline",
    {
      description: "Create a training-video outline draft; does not create or publish a video.",
      inputSchema: z.object({
        topic: z.string().min(3).max(180),
        audience: z.string().max(120).optional(),
        durationMinutes: z.number().int().min(1).max(60).optional(),
        language: z.string().max(40).optional(),
      }),
    },
    async ({ topic, audience, durationMinutes, language }) => {
      const outline = {
        topic, language: language ?? "Hindi", audience: audience ?? "beginners", durationMinutes: durationMinutes ?? 8,
        titleIdeas: [`${topic}: Step-by-Step Guide for Beginners`, `${topic} पूरी जानकारी | आसान तरीका`, `${topic} की 5 आम गलतियाँ`],
        sections: ["0:00 Hook and viewer problem", "Promise and prerequisites", "Step-by-step demo with a real example", "Common mistakes and recap", "Relevant question and related-video invitation"],
        descriptionChecklist: ["State viewer benefit in first two lines", "Add accurate chapters after recording", "Use relevant hashtags only"],
        thumbnailGuidance: "One clear subject, 2–4 readable words, high contrast, no misleading claim.",
        note: "Check current search suggestions and recent videos. Views are not guaranteed.",
      };
      return { content: [{ type: "text", text: JSON.stringify(outline, null, 2) }] };
    },
  );

  server.registerTool(
    "youtube_competitor_analysis",
    {
      description: "Analyze public YouTube videos in a niche using video metadata and public statistics. Provides competitor patterns and content opportunities; does not access private analytics or guarantee views.",
      inputSchema: z.object({
        query: z.string().min(2).max(120).describe("Niche, topic, or competitor keyword"),
        maxResults: z.number().int().min(3).max(10).optional().describe("Number of public videos to compare, default 5"),
      }),
    },
    async ({ query, maxResults }) => {
      if (!youtubeApiKey) {
        return { content: [{ type: "text", text: "Not configured: add YOUTUBE_API_KEY as a Cloudflare Worker secret." }], isError: true };
      }

      const searchUrl = new URL("https://www.googleapis.com/youtube/v3/search");
      searchUrl.searchParams.set("part", "snippet");
      searchUrl.searchParams.set("type", "video");
      searchUrl.searchParams.set("order", "viewCount");
      searchUrl.searchParams.set("q", query);
      searchUrl.searchParams.set("maxResults", String(maxResults ?? 5));
      searchUrl.searchParams.set("key", youtubeApiKey);

      const searchResponse = await safeFetch(searchUrl);
      if (!searchResponse) {
        return { content: [{ type: "text", text: "Could not reach YouTube search API. Check network/service status and retry later." }], isError: true };
      }
      if (!searchResponse.ok) {
        return { content: [{ type: "text", text: `YouTube search API returned HTTP ${searchResponse.status}. Check the API key, YouTube Data API v3 enablement, restrictions, and quota.` }], isError: true };
      }

      const searchData = await safeJson<{
        items?: Array<{
          id?: { videoId?: string };
          snippet?: { title?: string; channelTitle?: string; publishedAt?: string; description?: string };
        }>;
      }>(searchResponse);
      if (!searchData) {
        return { content: [{ type: "text", text: "YouTube search API returned an unreadable response. Please retry later." }], isError: true };
      }
      const items = (searchData.items ?? []).filter((item) => item.id?.videoId);
      const ids = items.map((item) => item.id!.videoId!).join(",");
      let statisticsById: Record<string, { viewCount?: string; likeCount?: string; commentCount?: string }> = {};
      let statisticsWarning: string | null = null;

      if (ids) {
        const statsUrl = new URL("https://www.googleapis.com/youtube/v3/videos");
        statsUrl.searchParams.set("part", "statistics");
        statsUrl.searchParams.set("id", ids);
        statsUrl.searchParams.set("key", youtubeApiKey);
        const statsResponse = await safeFetch(statsUrl);
        if (statsResponse?.ok) {
          const statsData = await safeJson<{
            items?: Array<{ id?: string; statistics?: { viewCount?: string; likeCount?: string; commentCount?: string } }>;
          }>(statsResponse);
          if (statsData) {
            for (const item of statsData.items ?? []) {
              if (item.id) statisticsById[item.id] = item.statistics ?? {};
            }
          } else {
            statisticsWarning = "YouTube video statistics API returned an unreadable response; counts may be unavailable.";
          }
        } else {
          statisticsWarning = statsResponse
            ? `YouTube video statistics API returned HTTP ${statsResponse.status}; counts may be unavailable.`
            : "Could not reach YouTube video statistics API; counts may be unavailable.";
        }
      }

      const statisticsRetrievedAt = new Date().toISOString();
      const nowMs = Date.now();
      const videos = items.map((item) => {
        const id = item.id!.videoId!;
        const stats = statisticsById[id] ?? {};
        const publishedAt = item.snippet?.publishedAt ?? "";
        const views = stats.viewCount !== undefined ? Number(stats.viewCount) : null;
        const likes = stats.likeCount !== undefined ? Number(stats.likeCount) : null;
        const comments = stats.commentCount !== undefined ? Number(stats.commentCount) : null;
        const ageDays = publishedAt && Number.isFinite(Date.parse(publishedAt))
          ? Math.max(1, (nowMs - Date.parse(publishedAt)) / 86_400_000)
          : null;
        return {
          videoId: id,
          title: item.snippet?.title ?? "",
          channel: item.snippet?.channelTitle ?? "",
          publishedAt,
          views,
          likes,
          comments,
          viewsPerDay: views !== null && ageDays !== null ? Math.round(views / ageDays) : null,
          likeRatePercent: views !== null && views > 0 && likes !== null
            ? Number(((likes / views) * 100).toFixed(4))
            : null,
          commentRatePercent: views !== null && views > 0 && comments !== null
            ? Number(((comments / views) * 100).toFixed(4))
            : null,
          description: (item.snippet?.description ?? "").slice(0, 220),
          url: `https://www.youtube.com/watch?v=${id}`,
          statisticsAvailable: stats.viewCount !== undefined,
        };
      });

      const measuredViews = videos.map((video) => video.views).filter((value): value is number => value !== null && Number.isFinite(value));
      const averageViews = measuredViews.length
        ? Math.round(measuredViews.reduce((sum, value) => sum + value, 0) / measuredViews.length)
        : null;
      const measuredLikeRates = videos.map((video) => video.likeRatePercent).filter((value): value is number => value !== null);
      const averageLikeRatePercent = measuredLikeRates.length
        ? Number((measuredLikeRates.reduce((sum, value) => sum + value, 0) / measuredLikeRates.length).toFixed(2))
        : null;
      const repeatedChannels = videos.reduce<Record<string, number>>((counts, video) => {
        counts[video.channel] = (counts[video.channel] ?? 0) + 1;
        return counts;
      }, {});
      const channelPatterns = Object.entries(repeatedChannels)
        .filter(([, count]) => count > 1)
        .map(([channel, count]) => ({ channel, matchingVideos: count }));

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            query,
            statisticsRetrievedAt,
            statisticsWarning,
            dataSource: "YouTube Data API v3 public search and video statistics endpoints",
            analysis: {
              videosCompared: videos.length,
              videosWithPublicStatistics: videos.filter((video) => video.statisticsAvailable).length,
              averageViewsOfVideosWithAvailableStatistics: averageViews,
              averageLikeRatePercentOfVideosWithAvailableStatistics: averageLikeRatePercent,
              repeatedChannelsInResults: channelPatterns,
              opportunityTips: [
                "Treat views, likes, and comments as a snapshot captured at statisticsRetrievedAt; they can change.",
                "viewsPerDay is a rough lifetime average, not recent daily views or a prediction.",
                "Like and comment rates are percentages of public counts divided by views, rounded to four decimal places so small rates are not incorrectly displayed as 0%.",
                "A statisticsWarning means the statistics endpoint failed; unavailable counts must not be interpreted as zero.",
                "Compare titles and descriptions to find unanswered beginner questions; content opportunities are suggestions, not measured facts."
              ],
            },
            videos,
            limitations: "Uses public search results and public video statistics only; it does not access private channel analytics. Statistics can be hidden or unavailable, in which case fields are null. Results are not an exhaustive list of competitors, and engagement rates do not establish causation or predict future performance."
          }, null, 2)
        }]
      };
    },
  );

  server.registerTool(
    "youtube_upload_video_from_url",
    {
      description: "Upload a finished video from a direct public HTTPS video URL to the connected owner's YouTube channel as PRIVATE. This does not generate the video. The source must return a video/* content type, must not redirect, and must be 50 MB or smaller. Requires reconnecting Google OAuth to grant youtube.upload scope.",
      inputSchema: z.object({
        videoUrl: z.string().url().max(2048).describe("Direct HTTPS URL to a finished video file (maximum 50 MB; redirects are not followed)"),
        title: z.string().trim().min(1).max(100).describe("YouTube video title"),
        description: z.string().max(5000).optional().describe("Video description"),
        tags: z.array(z.string().trim().min(1).max(100)).max(15).optional().describe("Up to 15 relevant tags"),
        categoryId: z.string().regex(/^\\d{1,3}$/).optional().describe("YouTube category ID; defaults to 27 (Education)"),
      }),
    },
    async ({ videoUrl, title, description, tags, categoryId }) => {
      let source: URL;
      try {
        source = new URL(videoUrl);
      } catch {
        return { content: [{ type: "text", text: "videoUrl must be a valid direct HTTPS URL." }], isError: true };
      }
      if (source.protocol !== "https:" || source.username || source.password ||
          source.hostname === "localhost" || source.hostname.endsWith(".localhost") ||
          source.hostname === "127.0.0.1" || source.hostname === "::1" ||
          /^\\d{1,3}(\\.\\d{1,3}){3}$/.test(source.hostname)) {
        return { content: [{ type: "text", text: "For safety, videoUrl must use a public HTTPS hostname without embedded credentials or an IP address." }], isError: true };
      }
      const accessToken = await getGoogleAccessToken(env);
      if (!accessToken) {
        return { content: [{ type: "text", text: "YouTube channel is not connected. Open /google/connect and authorize the channel owner first." }], isError: true };
      }

      const sourceResponse = await safeFetch(source.toString(), { redirect: "error" });
      if (!sourceResponse) {
        return { content: [{ type: "text", text: "Could not fetch the video file. Confirm the direct HTTPS URL is reachable and does not redirect." }], isError: true };
      }
      if (!sourceResponse.ok) {
        return { content: [{ type: "text", text: `Video source returned HTTP ${sourceResponse.status}. Use a direct, publicly accessible video URL.` }], isError: true };
      }
      const sourceType = (sourceResponse.headers.get("content-type") ?? "").split(";")[0].trim().toLowerCase();
      if (!sourceType.startsWith("video/")) {
        return { content: [{ type: "text", text: `Video source must return a video/* content type; received "${sourceType || "unknown"}".` }], isError: true };
      }
      const declaredLength = Number(sourceResponse.headers.get("content-length") ?? "0");
      const maxBytes = 50 * 1024 * 1024;
      if (declaredLength > maxBytes) {
        return { content: [{ type: "text", text: "Video exceeds the 50 MB upload limit for this Worker tool." }], isError: true };
      }
      let videoBytes: ArrayBuffer;
      try {
        videoBytes = await sourceResponse.arrayBuffer();
      } catch {
        return { content: [{ type: "text", text: "Could not read the video file from the source URL." }], isError: true };
      }
      if (videoBytes.byteLength === 0 || videoBytes.byteLength > maxBytes) {
        return { content: [{ type: "text", text: "Video file must be non-empty and no larger than 50 MB." }], isError: true };
      }

      const metadata = {
        snippet: {
          title,
          description: description ?? "",
          tags: tags ?? [],
          categoryId: categoryId ?? "27",
        },
        status: {
          privacyStatus: "private",
          selfDeclaredMadeForKids: false,
        },
      };
      const initiate = await safeFetch(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        {
          method: "POST",
          headers: {
            authorization: `Bearer ${accessToken}`,
            "content-type": "application/json; charset=UTF-8",
            "x-upload-content-type": sourceType,
            "x-upload-content-length": String(videoBytes.byteLength),
          },
          body: JSON.stringify(metadata),
        },
      );
      if (!initiate) {
        return { content: [{ type: "text", text: "Could not reach the YouTube upload service. Please retry later." }], isError: true };
      }
      if (!initiate.ok) {
        const detail = (await initiate.text().catch(() => "")).slice(0, 500);
        return { content: [{ type: "text", text: `YouTube upload initialization failed (HTTP ${initiate.status}). Reconnect Google and grant the youtube.upload permission if needed. ${detail}` }], isError: true };
      }
      const uploadUrl = initiate.headers.get("location");
      if (!uploadUrl || !uploadUrl.startsWith("https://")) {
        return { content: [{ type: "text", text: "YouTube did not return a valid resumable upload URL." }], isError: true };
      }
      const uploaded = await safeFetch(uploadUrl, {
        method: "PUT",
        headers: {
          authorization: `Bearer ${accessToken}`,
          "content-type": sourceType,
          "content-length": String(videoBytes.byteLength),
        },
        body: videoBytes,
      });
      if (!uploaded) {
        return { content: [{ type: "text", text: "Upload connection failed. Check YouTube Studio before retrying to avoid duplicate uploads." }], isError: true };
      }
      const uploadedData = await safeJson<{ id?: string; snippet?: { title?: string }; status?: { privacyStatus?: string } }>(uploaded);
      if (!uploaded.ok || !uploadedData?.id) {
        const detail = uploadedData ? JSON.stringify(uploadedData).slice(0, 500) : "Unreadable response";
        return { content: [{ type: "text", text: `YouTube upload failed (HTTP ${uploaded.status}). ${detail}` }], isError: true };
      }
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            uploaded: true,
            videoId: uploadedData.id,
            title: uploadedData.snippet?.title ?? title,
            privacyStatus: uploadedData.status?.privacyStatus ?? "private",
            url: `https://www.youtube.com/watch?v=${uploadedData.id}`,
            nextStep: "Review the video in YouTube Studio. This tool always uploads as PRIVATE and does not publish automatically.",
          }, null, 2),
        }],
      };
    },
  );

  server.registerTool(
    "youtube_channel_analytics",
    {
      description: "Read the authorized owner's YouTube Analytics summary for a date range. Requires Google OAuth connection first.",
      inputSchema: z.object({
        startDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).describe("Start date YYYY-MM-DD"),
        endDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).describe("End date YYYY-MM-DD"),
      }),
    },
    async ({ startDate, endDate }) => {
      if (!isValidDateOnly(startDate) || !isValidDateOnly(endDate)) {
        return { content: [{ type: "text", text: "Dates must be real calendar dates in YYYY-MM-DD format." }], isError: true };
      }
      if (startDate > endDate) return { content: [{ type: "text", text: "startDate must be on or before endDate." }], isError: true };
      const todayUtc = new Date().toISOString().slice(0, 10);
      if (endDate > todayUtc) {
        return { content: [{ type: "text", text: `endDate cannot be in the future. Use ${todayUtc} or an earlier date.` }], isError: true };
      }
      const accessToken = await getGoogleAccessToken(env);
      if (!accessToken) return { content: [{ type: "text", text: "YouTube channel not connected. Open https://youtube-ai-mcp.mkkhutar2.workers.dev/google/connect and complete Google authorization first." }], isError: true };
      const report = await fetchAnalyticsReport(accessToken, {
        ids: "channel==MINE", startDate, endDate,
        metrics: "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost",
      });
      if (!report.ok) return { content: [{ type: "text", text: report.status === 0 ? "Could not reach YouTube Analytics API. Check network/service status and retry later." : `YouTube Analytics API returned HTTP ${report.status}. Confirm YouTube Analytics API is enabled and the authorized Google account owns or manages a channel.` }], isError: true };
      const analyticsData = report.data as {
        columnHeaders?: Array<{ name?: string }>;
        rows?: Array<Array<string | number | null>>;
      };
      const headers = analyticsData.columnHeaders ?? [];
      const firstRow = analyticsData.rows?.[0] ?? [];
      const metricValue = (name: string): number | null => {
        const index = headers.findIndex((header) => header.name === name);
        if (index < 0 || firstRow[index] === null || firstRow[index] === undefined) return null;
        const value = Number(firstRow[index]);
        return Number.isFinite(value) ? value : null;
      };
      const views = metricValue("views");
      const estimatedMinutesWatched = metricValue("estimatedMinutesWatched");
      const averageViewDuration = metricValue("averageViewDuration");
      const derivedAverageViewDurationSeconds = views && views > 0 && estimatedMinutesWatched !== null
        ? (estimatedMinutesWatched * 60) / views
        : null;
      const durationDifferencePercent = derivedAverageViewDurationSeconds !== null &&
        averageViewDuration !== null && averageViewDuration > 0
        ? Number((Math.abs(derivedAverageViewDurationSeconds - averageViewDuration) / averageViewDuration * 100).toFixed(1))
        : null;
      const analyticsConsistency = {
        derivedAverageViewDurationSeconds: derivedAverageViewDurationSeconds === null
          ? null
          : Number(derivedAverageViewDurationSeconds.toFixed(1)),
        reportedAverageViewDurationSeconds: averageViewDuration,
        durationDifferencePercent,
        note: durationDifferencePercent !== null && durationDifferencePercent > 10
          ? "The reported average duration differs from estimated watch time divided by views. Treat this as a diagnostic only; YouTube metrics may use different aggregation or processing."
          : "Diagnostic comparison only; the original YouTube Analytics report remains authoritative.",
      };
      return { content: [{ type: "text", text: JSON.stringify({ startDate, endDate, analyticsConsistency, report: report.data }, null, 2) }] };
    },
  );
  return server;
}

const mcpHandler = {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    try {
      return await createMcpHandler(() => createServer(env), {
        onerror(error) {
          console.error("MCP protocol handler error", {
            errorName: error instanceof Error ? error.name : "UnknownError",
            errorMessage: error instanceof Error ? error.message : String(error),
            stack: error instanceof Error ? error.stack : undefined,
          });
        },
      })(request, env, ctx);
    } catch (error) {
      // Capture unexpected MCP-handler exceptions without logging credentials or request bodies.
      console.error("MCP handler exception", {
        method: request.method,
        path: new URL(request.url).pathname,
        errorName: error instanceof Error ? error.name : "UnknownError",
        errorMessage: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      return Response.json({ error: "MCP handler failed", requestId: crypto.randomUUID() }, { status: 500 });
    }
  },
};

export default new OAuthProvider<Env>({
  apiRoute: MCP_PATH,
  apiHandler: mcpHandler,
  defaultHandler: {
    fetch(request: Request, env: Env): Promise<Response> {
      const url = new URL(request.url);
      if (url.pathname === "/health") {
        return Promise.resolve(Response.json({ ok: true, service: "youtube-ai-mcp", version: "0.5.0", oauth: true }));
      }
      if (url.pathname === "/authorize") return authorize(request, env);
      if (url.pathname === "/google/connect") return googleConnect(request, env);
      if (url.pathname === "/google/callback") return googleCallback(request, env);
      if (url.pathname === "/automation/upload") return automatedPrivateUpload(request, env);
      return Promise.resolve(Response.json({ error: "Not found", mcpEndpoint: MCP_PATH }, { status: 404 }));
    },
  },
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/oauth/token",
  clientRegistrationEndpoint: "/oauth/register",
  scopesSupported: SCOPES,
  requiredScopes: SCOPES,
  resourceMetadata: {
    resource: MCP_RESOURCE,
    authorization_servers: ["https://youtube-ai-mcp.mkkhutar2.workers.dev"],
    resource_name: "YouTube AI MCP",
  },
  clientIdMetadataDocumentEnabled: true,
  onError({ code, description, status, internal }) {
    // Log OAuth diagnostics without logging tokens, cookies, or request bodies.
    console.error("OAuthProvider error", {
      code,
      status,
      description,
      category: internal?.category,
      reason: internal?.reason,
      detail: internal?.detail instanceof Error ? internal.detail.message : undefined,
    });
  },
});
