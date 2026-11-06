import { parseWorkbook } from "./report.ts";

Deno.serve(async request => {
  const secret = Deno.env.get("SYNC_SECRET");
  if (!secret || request.headers.get("x-sync-secret") !== secret) return new Response("Unauthorized", {status: 401});
  if (request.method !== "POST") return new Response("Use POST", {status: 405});
  const started = new Date().toISOString();
  const base = Deno.env.get("SUPABASE_URL")!;
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  async function rpc(name: string, body: unknown) {
    const response = await fetch(`${base}/rest/v1/rpc/${name}`, {method: "POST", headers: {apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json"}, body: JSON.stringify(body), signal: AbortSignal.timeout(15000)});
    if (!response.ok) throw new Error("Database sync rejected; check configuration and restaurant mappings");
    return response.json();
  }
  try {
    await rpc("bevstats_sync_attempt", {p_started: started});
    const url = Deno.env.get("REPORT_URL");
    if (!url || new URL(url).hostname !== "eaglerockdist.com" || new URL(url).protocol !== "https:") throw new Error("Configure REPORT_URL");
    const response = await fetch(url, {signal: AbortSignal.timeout(45000)});
    if (!response.ok) throw new Error("Report download failed");
    const data = await response.arrayBuffer();
    if (data.byteLength > 5000000) throw new Error("Report exceeds size limit");
    const parsed = await parseWorkbook(data);
    const result = await rpc("bevstats_sync_sales", {p_started: started, p_rows: parsed.rows, p_cache_time: parsed.source_cache_time});
    return Response.json(result);
  } catch (error) {
    // Do not log upstream URLs, tokens, response bodies, or customer data.
    const message = error instanceof Error && /^(Configure|Report |Unexpected|Invalid|Duplicate|Incomplete|Restaurant|Missing|Reporting|Database)/.test(error.message) ? error.message : "Report sync failed";
    try { await rpc("bevstats_sync_failure", {p_started: started, p_error: message}); } catch { console.error("Unable to record sync failure"); }
    return Response.json({error: message}, {status: 502});
  }
});
