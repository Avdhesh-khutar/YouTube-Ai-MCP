import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { createMcpHandler } from "agents/mcp";
import OAuthProvider, {
  AuthorizationError,
  type OAuthHelpers,
  type ConsentDescription,
} from "@cloudflare/workers-oauth-provider";
import { z } from "zod";

interface Env {
  OAUTH_KV: KVNamespace;
  OAUTH_PROVIDER: OAuthHelpers;
  OAUTH_ADMIN_PASSWORD?: string;
  YOUTUBE_API_KEY?: string;
}

const MCP_PATH = "/mcp";
const MCP_RESOURCE = "https://youtube-ai-mcp.mkkhutar2.workers.dev/mcp";
const SCOPES = ["mcp:read"];

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);
}

function page(title: string, body: string, status = 200): Response {
  return new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(title)}</title><style>body{font:16px system-ui;max-width:620px;margin:48px auto;padding:0 18px;color:#172033}main{border:1px solid #ddd;border-radius:14px;padding:24px}input{box-sizing:border-box;width:100%;padding:12px;margin:8px 0 18px}button{padding:12px 18px;border:0;border-radius:8px;background:#155eef;color:white;font-weight:600}small{color:#555}</style></head><body><main><h1>${escapeHtml(title)}</h1>${body}</main></body></html>`, {
    status,
    headers: { "content-type": "text/html; charset=utf-8", "x-content-type-options": "nosniff", "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'", "referrer-policy": "no-referrer" },
  });
}

function consentPage(details: ConsentDescription, handle: string): Response {
  const name = escapeHtml(details.clientName);
  const scopeHtml = details.scope.map((scope) => `<li>${escapeHtml(scope)}</li>`).join("");
  const domain = details.clientDomain
    ? `Client domain: <strong>${escapeHtml(details.clientDomain)}</strong>`
    : "The client name is supplied by the connecting app and is not independently verified.";
  return page("Connect YouTube AI Assistant", `
    <p><strong>${name}</strong> is requesting access to this MCP service.</p>
    <p>${domain}</p>
    <p>Authorization will return to: <strong>${escapeHtml(details.redirectHost)}</strong></p>
    ${details.redirectIsLoopback ? "<p><strong>Warning:</strong> this sends authorization to an app on your device. Continue only if you just started this connection.</p>" : ""}
    <p>Requested permissions:</p><ul>${scopeHtml}</ul>
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
      response.headers.set("set-cookie", consent.headers.get("set-cookie") ?? "");
      // Preserve all browser-binding headers required by the OAuth library.
      for (const [key, value] of consent.headers) {
        if (key.toLowerCase() !== "content-type") response.headers.set(key, value);
      }
      return response;
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
        return page("Sign-in failed", "<p>The connector password was not correct.</p><p><a href=\"javascript:history.back()\">Go back and try again</a></p>", 401);
      }

      const approved = await oauth.approveConsent(request, handle, { scope: SCOPES });
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

function createServer(youtubeApiKey?: string): McpServer {
  const server = new McpServer({ name: "youtube-ai-mcp", version: "0.2.0" });

  server.tool(
    "youtube_video_research",
    "Search public YouTube videos by keyword. Does not access private channel analytics.",
    {
      query: z.string().min(2).max(120).describe("Topic or keyword"),
      maxResults: z.number().int().min(1).max(10).optional().describe("Number of results, default 5"),
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
      const response = await fetch(url);
      if (!response.ok) {
        return { content: [{ type: "text", text: `YouTube API returned HTTP ${response.status}. Check the API key, YouTube Data API v3 enablement, restrictions, and quota.` }], isError: true };
      }
      const data = await response.json() as { items?: Array<{ id?: { videoId?: string }; snippet?: { title?: string; channelTitle?: string; publishedAt?: string; description?: string } }> };
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

  server.tool(
    "youtube_training_video_outline",
    "Create a training-video outline draft; does not create or publish a video.",
    {
      topic: z.string().min(3).max(180),
      audience: z.string().max(120).optional(),
      durationMinutes: z.number().int().min(1).max(60).optional(),
      language: z.string().max(40).optional(),
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
  return server;
}

const mcpHandler = {
  fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    return createMcpHandler(createServer(env.YOUTUBE_API_KEY))(request, env, ctx);
  },
};

export default new OAuthProvider<Env>({
  apiRoute: MCP_PATH,
  apiHandler: mcpHandler,
  defaultHandler: {
    fetch(request: Request, env: Env): Promise<Response> {
      const url = new URL(request.url);
      if (url.pathname === "/health") {
        return Promise.resolve(Response.json({ ok: true, service: "youtube-ai-mcp", version: "0.2.0", oauth: true }));
      }
      if (url.pathname === "/authorize") return authorize(request, env);
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
    scopes_supported: SCOPES,
    resource_name: "YouTube AI MCP",
  },
  clientIdMetadataDocumentEnabled: true,
});
