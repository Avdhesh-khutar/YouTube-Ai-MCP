export interface ChannelEnv {
  OAUTH_KV: KVNamespace;
  OAUTH_ADMIN_PASSWORD?: string;
  GOOGLE_OAUTH_CLIENT_ID?: string;
  GOOGLE_OAUTH_CLIENT_SECRET?: string;
}

const BASE = "https://youtube-ai-mcp.mkkhutar2.workers.dev";
const REDIRECT_URI = BASE + "/google/callback";
const CHANNEL_PREFIX = "yt-channel:";

function esc(value: string): string {
  return value.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] ?? c));
}

function html(title: string, body: string, status = 200): Response {
  return new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>${esc(title)}</title><style>
  :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#f4f6ff;font:16px system-ui,-apple-system,sans-serif}main{max-width:850px;margin:0 auto;padding:28px 16px 60px}.hero{padding:26px;border:1px solid #28324c;border-radius:22px;background:linear-gradient(135deg,#171f38,#101729)}h1{margin:0 0 8px;font-size:clamp(26px,6vw,40px)}p{color:#b7c1d8;line-height:1.55}.panel{margin-top:18px;padding:20px;border:1px solid #28324c;border-radius:18px;background:#11182a}label{display:block;font-weight:600;margin-bottom:8px}input{width:100%;padding:13px;border:1px solid #394560;border-radius:10px;background:#0b1020;color:#fff;margin-bottom:12px}button{border:0;border-radius:10px;padding:12px 16px;background:#e52d45;color:white;font-weight:700;cursor:pointer}button.secondary{background:#26324b;color:#eef2ff}button.danger{background:#502532}button:disabled{opacity:.5;cursor:wait}.muted{color:#93a0bb;font-size:13px}.status{padding:10px 12px;background:#0b1020;border-radius:10px;margin-top:12px;white-space:pre-wrap}.channel{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:14px 0;border-bottom:1px solid #28324c}.channel:last-child{border-bottom:0}.channel strong{display:block;overflow-wrap:anywhere}.channel small{color:#9aa8c4}.row{display:flex;gap:10px;flex-wrap:wrap}.pill{display:inline-block;padding:5px 9px;border-radius:999px;background:#203a32;color:#a8f1c8;font-size:12px}a{color:#9ebcff}@media(max-width:520px){.channel{align-items:flex-start;flex-direction:column}.channel button{width:100%}}
  </style></head><body><main><header class="hero"><p class="muted">CLOUDFLARE WORKER · YOUTUBE AI MCP</p><h1>YouTube Control Panel</h1><p>Connect and manage multiple YouTube channels securely. Channel tokens stay on the Worker and are never shown in this dashboard.</p><span class="pill">Private uploads by default</span></header>${body}</main></body></html>`, {
    status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff", "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'", "referrer-policy": "no-referrer" }
  });
}

function json(data: unknown, status = 200): Response {
  return Response.json(data, { status, headers: { "cache-control": "no-store", "x-content-type-options": "nosniff" } });
}

function authorized(request: Request, env: ChannelEnv): boolean {
  const expected = env.OAUTH_ADMIN_PASSWORD ?? "";
  const supplied = request.headers.get("x-admin-password") ?? "";
  return expected.length > 0 && supplied.length === expected.length && supplied === expected;
}

export interface StoredYouTubeChannel {
  channelId: string;
  title: string;
  customUrl?: string;
  refreshToken: string;
  connectedAt: string;
}

export async function getChannelRefreshToken(env: ChannelEnv, channelId?: string): Promise<string | null> {
  if (channelId) {
    const raw = await env.OAUTH_KV.get(CHANNEL_PREFIX + channelId);
    if (raw) {
      try {
        const record = JSON.parse(raw) as StoredYouTubeChannel;
        if (record.channelId === channelId && record.refreshToken) return record.refreshToken;
      } catch { /* malformed record is ignored */ }
    }
    return null;
  }
  return env.OAUTH_KV.get("youtube-google-refresh-token");
}

export async function handleDashboard(request: Request, env: ChannelEnv): Promise<Response | null> {
  const url = new URL(request.url);
  if (url.pathname === "/dashboard" || url.pathname === "/dashboard/") {
    if (request.method !== "GET") return new Response("Method Not Allowed", { status: 405, headers: { allow: "GET" } });
    const connected = url.searchParams.get("connected");
    const notice = connected === "1" ? "Google authorization succeeded. Your channels are listed below." : "";
    const body = `
      <section class="panel"><h2>Admin sign-in</h2><p>Enter the Worker admin password you configured in Cloudflare. It is kept only in this tab's memory.</p><label for="password">Worker admin password</label><input id="password" type="password" autocomplete="current-password" placeholder="Admin password"><div class="row"><button id="login">Unlock dashboard</button><button id="connect" class="secondary" disabled>＋ Connect Google account / channels</button></div><div id="status" class="status" role="status">${esc(notice || "Sign in to load your connected channels.")}</div></section>
      <section class="panel"><h2>Upload a video</h2><p class="muted">Choose a video from your computer. It will be uploaded to the selected connected channel as PRIVATE.</p><label for="upload-channel">YouTube channel</label><select id="upload-channel" disabled style="width:100%;padding:12px;border:1px solid #394560;border-radius:10px;background:#0b1020;color:#fff;margin-bottom:12px"><option>Unlock dashboard first</option></select><label for="upload-file">Video file (MP4 recommended, max 47 MB)</label><input id="upload-file" type="file" accept="video/*" disabled><label for="upload-title">Video title</label><input id="upload-title" maxlength="100" value="आख़िरी मुलाक़ात 💔 | 5 साल बाद मिली मोहब्बत | Emotional Hindi Love Story" disabled><label for="upload-description">Description</label><textarea id="upload-description" rows="5" style="width:100%;padding:12px;border:1px solid #394560;border-radius:10px;background:#0b1020;color:#fff;margin-bottom:12px" disabled>एक भावुक हिंदी प्रेम कहानी — आख़िरी मुलाक़ात, पाँच साल बाद मिली मोहब्बत और यादों का सफ़र।</textarea><button id="upload-button" disabled>Upload video as Private</button><div id="upload-status" class="status" role="status">Unlock dashboard to upload.</div></section>
      <section class="panel"><h2>Connected channels</h2><p class="muted">One Google account may expose multiple channels. Connect another Google account to add its channels too.</p><div id="channels"><p class="muted">Dashboard locked.</p></div></section>
      <script>
      (()=>{let adminPassword="";const $=id=>document.getElementById(id);const status=$("status"),list=$("channels"),login=$("login"),connect=$("connect"),uploadButton=$("upload-button"),uploadStatus=$("upload-status"),channelSelect=$("upload-channel");let defaultChannelId="";
      function say(t){status.textContent=t}
      async function api(path,opts={}){const headers=new Headers(opts.headers||{});headers.set("x-admin-password",adminPassword);if(opts.body&&!headers.has("content-type")&&!(opts.body instanceof FormData))headers.set("content-type","application/json");const r=await fetch(path,{...opts,headers});const d=await r.json().catch(()=>({error:"Invalid server response"}));if(!r.ok)throw new Error(d.error||"Request failed ("+r.status+")");return d}
      function draw(channels,defaultId=""){defaultChannelId=defaultId||"";channelSelect.replaceChildren();if(!channels.length){channelSelect.add(new Option("No connected channels",""));channelSelect.disabled=true;uploadButton.disabled=true;list.innerHTML="<p>No channels connected yet. Use Connect above to add one.</p>";return}channelSelect.disabled=false;uploadButton.disabled=false;for(const c of channels){const option=new Option(c.title,c.channelId);option.selected=c.channelId===defaultChannelId;channelSelect.add(option)}list.replaceChildren();for(const c of channels){const row=document.createElement("div");row.className="channel";const info=document.createElement("div");const name=document.createElement("strong");name.textContent=(c.title||"YouTube channel")+(c.channelId===defaultChannelId?" · DEFAULT UPLOAD CHANNEL":"");const id=document.createElement("small");id.textContent="Channel ID: "+c.channelId;info.append(name,id);const btn=document.createElement("button");btn.className="danger";btn.textContent="Disconnect";btn.addEventListener("click",async()=>{if(!confirm("Disconnect "+(c.title||c.channelId)+" from this Worker?"))return;try{await api("/dashboard/api/channels?channelId="+encodeURIComponent(c.channelId),{method:"DELETE"});say("Channel disconnected.");await load()}catch(e){say(e.message)}});const primary=document.createElement("button");primary.className="secondary";primary.textContent=c.channelId===defaultChannelId?"Default upload channel":"Set as default";primary.disabled=c.channelId===defaultChannelId;primary.addEventListener("click",async()=>{primary.disabled=true;try{await api("/dashboard/api/default",{method:"POST",body:JSON.stringify({channelId:c.channelId})});say("Default upload channel saved.");await load()}catch(e){say(e.message);primary.disabled=false}});const actions=document.createElement("div");actions.className="row";actions.append(primary,btn);row.append(info,actions);list.append(row)}}
      async function load(){try{const d=await api("/dashboard/api/channels");draw(d.channels||[],d.defaultChannelId||"");connect.disabled=false;say("Dashboard unlocked. "+(d.channels||[]).length+" channel(s) connected.")}catch(e){draw([]);say(e.message)}}
      login.addEventListener("click",async()=>{adminPassword=$("password").value;if(!adminPassword){say("Enter the Worker admin password.");return}connect.disabled=true;await load()});
      connect.addEventListener("click",async()=>{const label=prompt("Optional label for this Google account (e.g. Alpha Studio):","");if(label===null)return;connect.disabled=true;say("Opening Google authorization…");try{const d=await api("/dashboard/api/connect",{method:"POST",body:JSON.stringify({label})});if(!d.authorizationUrl)throw new Error("Google authorization URL missing.");location.assign(d.authorizationUrl)}catch(e){say(e.message);connect.disabled=false}});
      uploadButton.addEventListener("click",async()=>{const file=$("upload-file").files[0];if(!file){uploadStatus.textContent="Choose a video file first.";return}if(file.size>47*1024*1024){uploadStatus.textContent="Video must be 47 MB or smaller.";return}if(!channelSelect.value){uploadStatus.textContent="Connect and select a channel first.";return}const form=new FormData();form.append("video",file);form.append("channelId",channelSelect.value);form.append("title",$("upload-title").value);form.append("description",$("upload-description").value);uploadButton.disabled=true;uploadStatus.textContent="Uploading video to YouTube as PRIVATE. Keep this tab open…";try{const d=await api("/dashboard/api/upload",{method:"POST",body:form});uploadStatus.textContent="Upload successful: "+d.title+" — "+d.url+" (PRIVATE)";}catch(e){uploadStatus.textContent=e.message}finally{uploadButton.disabled=false}});
      if(location.hash==="#unlock")$("password").focus();
      })();
      </script>`;
    return html("YouTube Control Panel", body);
  }

  if (url.pathname === "/dashboard/api/channels") {
    if (!authorized(request, env)) return json({ error: "Unauthorized. Unlock the dashboard with the Worker admin password." }, 401);
    if (request.method === "GET") {
      // Migrate the existing single-channel OAuth token into the channel registry on first dashboard visit.
      const existing = await env.OAUTH_KV.list({ prefix: CHANNEL_PREFIX, limit: 1 });
      const legacyRefreshToken = await env.OAUTH_KV.get("youtube-google-refresh-token");
      if (existing.keys.length === 0 && legacyRefreshToken && env.GOOGLE_OAUTH_CLIENT_ID && env.GOOGLE_OAUTH_CLIENT_SECRET) {
        try {
          const refresh = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ client_id: env.GOOGLE_OAUTH_CLIENT_ID, client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET, refresh_token: legacyRefreshToken, grant_type: "refresh_token" }) });
          if (refresh.ok) {
            const token = await refresh.json() as { access_token?: string };
            if (token.access_token) {
              const response = await fetch("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true&maxResults=50", { headers: { authorization: "Bearer " + token.access_token } });
              if (response.ok) {
                const data = await response.json() as { items?: Array<{ id?: string; snippet?: { title?: string; customUrl?: string } }> };
                for (const c of data.items ?? []) {
                  if (!c.id || !c.snippet?.title) continue;
                  const record: StoredYouTubeChannel = { channelId: c.id, title: c.snippet.title, customUrl: c.snippet.customUrl, refreshToken: legacyRefreshToken, connectedAt: new Date().toISOString() };
                  await env.OAUTH_KV.put(CHANNEL_PREFIX + record.channelId, JSON.stringify(record));
                }
              }
            }
          }
        } catch { /* Keep the legacy token intact; user can reconnect from dashboard if migration fails. */ }
      }
      const keys = await env.OAUTH_KV.list({ prefix: CHANNEL_PREFIX, limit: 100 });
      const channels: Array<{ channelId: string; title: string; customUrl?: string; connectedAt: string }> = [];
      for (const key of keys.keys) {
        const raw = await env.OAUTH_KV.get(key.name);
        if (!raw) continue;
        try {
          const c = JSON.parse(raw) as StoredYouTubeChannel;
          if (c.channelId && c.title) channels.push({ channelId: c.channelId, title: c.title, customUrl: c.customUrl, connectedAt: c.connectedAt });
        } catch { /* skip malformed channel entry */ }
      }
      channels.sort((a, b) => a.title.localeCompare(b.title));
      const defaultChannelId = await env.OAUTH_KV.get("youtube-default-channel-id") ?? channels[0]?.channelId ?? "";\n      if (defaultChannelId && !(await env.OAUTH_KV.get("youtube-default-channel-id"))) await env.OAUTH_KV.put("youtube-default-channel-id", defaultChannelId);\n      return json({ channels, defaultChannelId });
    }
    if (request.method === "DELETE") {
      const channelId = url.searchParams.get("channelId") ?? "";
      if (!/^UC[A-Za-z0-9_-]{20,}$/.test(channelId)) return json({ error: "Invalid channel ID." }, 400);
      await env.OAUTH_KV.delete(CHANNEL_PREFIX + channelId);
      return json({ disconnected: true, channelId });
    }
    return new Response("Method Not Allowed", { status: 405, headers: { allow: "GET, DELETE" } });
  }

  if (url.pathname === "/dashboard/api/default") {
    if (request.method !== "POST") return new Response("Method Not Allowed", { status: 405, headers: { allow: "POST" } });
    if (!authorized(request, env)) return json({ error: "Unauthorized. Unlock the dashboard first." }, 401);
    const body = await request.json().catch(() => ({})) as { channelId?: string };
    const channelId = String(body.channelId ?? "");
    if (!/^UC[A-Za-z0-9_-]{20,}$/.test(channelId)) return json({ error: "Invalid channel ID." }, 400);
    const raw = await env.OAUTH_KV.get(CHANNEL_PREFIX + channelId);
    if (!raw) return json({ error: "Choose a channel that is connected in this dashboard." }, 404);
    await env.OAUTH_KV.put("youtube-default-channel-id", channelId);
    return json({ defaultChannelId: channelId, saved: true });
  }

  if (url.pathname === "/dashboard/api/upload") {
    if (request.method !== "POST") return new Response("Method Not Allowed", { status: 405, headers: { allow: "POST" } });
    if (!authorized(request, env)) return json({ error: "Unauthorized. Unlock the dashboard first." }, 401);
    if (!env.GOOGLE_OAUTH_CLIENT_ID || !env.GOOGLE_OAUTH_CLIENT_SECRET) return json({ error: "Google OAuth client credentials are not configured." }, 503);
    const length = Number(request.headers.get("content-length") ?? "0");
    if (length > 49 * 1024 * 1024) return json({ error: "Request exceeds the 49 MB upload limit." }, 413);
    let form: FormData;
    try { form = await request.formData(); } catch { return json({ error: "Expected multipart video upload." }, 400); }
    const video = form.get("video");
    const channelId = String(form.get("channelId") ?? "");
    const title = String(form.get("title") ?? "").trim().slice(0, 100);
    const description = String(form.get("description") ?? "").slice(0, 5000);
    if (!video || typeof video !== "object" || typeof (video as File).arrayBuffer !== "function") return json({ error: "Choose a video file." }, 400);
    const file = video as File;
    if (!/^UC[A-Za-z0-9_-]{20,}$/.test(channelId)) return json({ error: "Select a valid connected channel." }, 400);
    if (!title) return json({ error: "Enter a video title." }, 400);
    if (file.size < 1 || file.size > 47 * 1024 * 1024 || !file.type.startsWith("video/")) return json({ error: "Video must be a valid video file no larger than 47 MB." }, 413);
    const raw = await env.OAUTH_KV.get(CHANNEL_PREFIX + channelId);
    if (!raw) return json({ error: "This channel is not connected. Reconnect it in the dashboard." }, 401);
    let channel: StoredYouTubeChannel;
    try { channel = JSON.parse(raw) as StoredYouTubeChannel; } catch { return json({ error: "Connected channel record is invalid." }, 500); }
    if (channel.channelId !== channelId || !channel.refreshToken) return json({ error: "Connected channel token is missing." }, 401);
    const refresh = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ client_id: env.GOOGLE_OAUTH_CLIENT_ID, client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET, refresh_token: channel.refreshToken, grant_type: "refresh_token" }) });
    if (!refresh.ok) return json({ error: "Google token refresh failed. Reconnect this channel from the dashboard." }, 401);
    const token = await refresh.json() as { access_token?: string };
    if (!token.access_token) return json({ error: "Google did not return an access token." }, 401);
    const metadata = { snippet: { title, description, categoryId: "22" }, status: { privacyStatus: "private", selfDeclaredMadeForKids: false } };
    const init = await fetch("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", { method: "POST", headers: { authorization: "Bearer " + token.access_token, "content-type": "application/json; charset=UTF-8", "x-upload-content-type": file.type || "video/mp4", "x-upload-content-length": String(file.size) }, body: JSON.stringify(metadata) });
    if (!init.ok) return json({ error: "YouTube upload initialization failed (HTTP " + init.status + "). Check YouTube API permissions." }, 502);
    const uploadUrl = init.headers.get("location");
    if (!uploadUrl || !uploadUrl.startsWith("https://")) return json({ error: "YouTube did not return a resumable upload URL." }, 502);
    const uploaded = await fetch(uploadUrl, { method: "PUT", headers: { authorization: "Bearer " + token.access_token, "content-type": file.type || "video/mp4", "content-length": String(file.size) }, body: await file.arrayBuffer() });
    const data = await uploaded.json().catch(() => ({})) as { id?: string; snippet?: { title?: string }; status?: { privacyStatus?: string } };
    if (!uploaded.ok || !data.id) return json({ error: "YouTube upload failed (HTTP " + uploaded.status + "). " + JSON.stringify(data).slice(0, 350) }, 502);
    return json({ uploaded: true, videoId: data.id, title: data.snippet?.title || title, privacyStatus: data.status?.privacyStatus || "private", url: "https://www.youtube.com/watch?v=" + data.id });
  }

  if (url.pathname === "/dashboard/api/connect") {
    if (request.method !== "POST") return new Response("Method Not Allowed", { status: 405, headers: { allow: "POST" } });
    if (!authorized(request, env)) return json({ error: "Unauthorized. Unlock the dashboard first." }, 401);
    if (!env.GOOGLE_OAUTH_CLIENT_ID || !env.GOOGLE_OAUTH_CLIENT_SECRET) return json({ error: "Google OAuth client ID/secret are not configured in Cloudflare Worker secrets." }, 503);
    const body = await request.json().catch(() => ({})) as { label?: string };
    const label = String(body.label ?? "").trim().slice(0, 80);
    const state = crypto.randomUUID();
    const verifierBytes = crypto.getRandomValues(new Uint8Array(32));
    const verifier = btoa(String.fromCharCode(...verifierBytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
    const challenge = btoa(String.fromCharCode(...new Uint8Array(digest))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
    await env.OAUTH_KV.put("google-oauth-state:" + state, JSON.stringify({ verifier, createdAt: Date.now(), mode: "dashboard", label }), { expirationTtl: 600 });
    const auth = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    auth.searchParams.set("client_id", env.GOOGLE_OAUTH_CLIENT_ID);
    auth.searchParams.set("redirect_uri", REDIRECT_URI);
    auth.searchParams.set("response_type", "code");
    auth.searchParams.set("scope", ["https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/yt-analytics.readonly"].join(" "));
    auth.searchParams.set("access_type", "offline");
    auth.searchParams.set("prompt", "consent select_account");
    auth.searchParams.set("include_granted_scopes", "true");
    auth.searchParams.set("state", state);
    auth.searchParams.set("code_challenge", challenge);
    auth.searchParams.set("code_challenge_method", "S256");
    return json({ authorizationUrl: auth.toString() });
  }
  return null;
}

export async function completeDashboardGoogleOAuth(request: Request, env: ChannelEnv): Promise<Response | null> {
  const url = new URL(request.url);
  if (url.pathname !== "/google/callback") return null;
  const state = url.searchParams.get("state") ?? "";
  if (!state) return null;
  const stateKey = "google-oauth-state:" + state;
  const raw = await env.OAUTH_KV.get(stateKey);
  if (!raw) return null;
  let data: { verifier?: string; createdAt?: number; mode?: string; label?: string };
  try { data = JSON.parse(raw) as typeof data; } catch { return null; }
  if (data.mode !== "dashboard") return null;
  await env.OAUTH_KV.delete(stateKey);
  const error = url.searchParams.get("error");
  if (error) return html("Google connection cancelled", "<p>Google authorization was cancelled. Return to the dashboard and try again.</p>", 400);
  const code = url.searchParams.get("code");
  if (!code || !data.verifier || !data.createdAt || Date.now() - data.createdAt > 600_000) return html("Authorization expired", "<p>Authorization code or state is missing/expired. Please reconnect from the dashboard.</p>", 400);
  if (!env.GOOGLE_OAUTH_CLIENT_ID || !env.GOOGLE_OAUTH_CLIENT_SECRET) return html("OAuth setup required", "<p>Google OAuth client credentials are not configured.</p>", 503);
  const tokenResponse = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ code, client_id: env.GOOGLE_OAUTH_CLIENT_ID, client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET, redirect_uri: REDIRECT_URI, grant_type: "authorization_code", code_verifier: data.verifier }) });
  if (!tokenResponse.ok) return html("Google token exchange failed", "<p>Could not exchange the authorization code. Check OAuth settings and reconnect.</p>", 502);
  const tokens = await tokenResponse.json() as { access_token?: string; refresh_token?: string };
  if (!tokens.access_token || !tokens.refresh_token) return html("Google token missing", "<p>Google did not return the required access/refresh token. Revoke this app in your Google account and reconnect with consent.</p>", 502);
  const channelResponse = await fetch("https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails&mine=true&maxResults=50", { headers: { authorization: "Bearer " + tokens.access_token } });
  if (!channelResponse.ok) return html("Could not read YouTube channels", "<p>YouTube channel lookup failed. Ensure YouTube Data API v3 is enabled and reconnect.</p>", 502);
  const channelData = await channelResponse.json() as { items?: Array<{ id?: string; snippet?: { title?: string; customUrl?: string } }> };
  const items = (channelData.items ?? []).filter((c) => c.id && c.snippet?.title);
  if (!items.length) return html("No YouTube channels found", "<p>This Google account did not return a YouTube channel. Create/select a channel and connect again.</p>", 404);
  const connectedAt = new Date().toISOString();
  for (const c of items) {
    const record: StoredYouTubeChannel = { channelId: c.id!, title: c.snippet!.title!, customUrl: c.snippet?.customUrl, refreshToken: tokens.refresh_token, connectedAt };
    await env.OAUTH_KV.put(CHANNEL_PREFIX + record.channelId, JSON.stringify(record));
  }
  // Keep the existing single-channel MCP/workflow compatible with the first connected channel.
  if (!(await env.OAUTH_KV.get("youtube-google-refresh-token"))) await env.OAUTH_KV.put("youtube-google-refresh-token", tokens.refresh_token);
  const label = data.label ? " Account label: " + esc(data.label) + "." : "";
  return html("YouTube channels connected", `<p>Google authorization succeeded. ${items.length} channel(s) were saved securely in Cloudflare KV.${label}</p><p>Channel names and IDs are visible in the <a href="/dashboard">YouTube Control Panel</a>. Refresh tokens are not displayed.</p><p><a href="/dashboard">Return to dashboard</a></p>`);
}
