/* Shared Supabase report adapter. No sample data or browser-local sales fallback. */
(() => {
  'use strict';
  const config = window.BEVSTATS_SUPABASE || {};
  const base = (config.url || '').replace(/\/$/, '');
  const nativeFetch = window.fetch.bind(window);
  const key = 'bevstats.supabase.session.v1';
  let session = null;
  try { session = JSON.parse(sessionStorage.getItem(key) || 'null'); } catch (_) {}
  const reply = (status, body) => new Response(JSON.stringify(body), {status, headers:{'Content-Type':'application/json'}});
  function store(value) {
    if (value && !value.expires_at) value.expires_at = Math.floor(Date.now()/1000) + (value.expires_in || 3600);
    session = value;
    if (value) sessionStorage.setItem(key, JSON.stringify(value));
    else sessionStorage.removeItem(key);
  }
  async function request(path, options = {}, token = null) {
    const headers = {'apikey':config.publishableKey, 'Content-Type':'application/json', ...options.headers};
    if (token) headers.Authorization = 'Bearer ' + token;
    const response = await nativeFetch(base + path, {...options, headers});
    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : null; } catch (_) { throw Error('Unexpected database response'); }
    if (!response.ok) {
      if (response.status === 401) store(null);
      const error = Error(data?.msg || data?.message || data?.error_description || 'Database request failed');
      error.status = response.status;
      throw error;
    }
    return data;
  }
  const visitor = {id:null, username:'Public view', visitor:true, can_edit:false};
  async function isOwner() {
    if (!session) return false;
    const owners = await request('/rest/v1/bevstats_owner?select=user_id&limit=1', {}, session.access_token);
    return owners.length === 1;
  }
  function publicUser() { return session?.user ? {id:session.user.id, username:session.user.email, display_name:session.user.email, can_edit:true} : null; }
  async function freshSession() {
    if (session && session.expires_at * 1000 < Date.now() + 60000) {
      try {
        store(await request('/auth/v1/token?grant_type=refresh_token', {method:'POST', body:JSON.stringify({refresh_token:session.refresh_token})}));
      } catch (error) { store(null); throw error; }
    }
  }
  window.fetch = async (input, options = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, window.location.href);
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return nativeFetch(input, options);
    try {
      if (!base || !config.publishableKey) return reply(503, {error:'Supabase is not configured yet. Connect the project to load the real report.'});
      const method = (options.method || 'GET').toUpperCase(), path = url.pathname;
      const body = options.body ? JSON.parse(options.body) : {};
      if (path === '/api/login' && method === 'POST') {
        const email = String(body.username || '').trim().toLowerCase();
        if (email !== config.adminEmail.toLowerCase()) return reply(403, {error:'Admin sign-in is available only to the designated account.'});
        const redirect = location.origin + location.pathname;
        await request('/auth/v1/otp?redirect_to=' + encodeURIComponent(redirect), {method:'POST',body:JSON.stringify({email,create_user:false})});
        return reply(200, {email_sent:true});
      }
      if (path === '/api/logout' && method === 'POST') {
        try { if (session) await request('/auth/v1/logout',{method:'POST'},session.access_token); } finally { store(null); }
        return reply(200, {ok:true});
      }
      if (path === '/api/session') {
        const fragment = new URLSearchParams(location.hash.slice(1));
        if (fragment.has('access_token') || fragment.has('error_description')) {
          history.replaceState(null, '', location.pathname + location.search);
          if (fragment.has('error_description')) throw Error(fragment.get('error_description'));
          const token = fragment.get('access_token');
          const user = await request('/auth/v1/user', {}, token);
          if (user.email?.toLowerCase() !== config.adminEmail.toLowerCase() || !user.email_confirmed_at) {
            store(null); throw Error('This sign-in link does not belong to the verified admin account.');
          }
          store({access_token:token,refresh_token:fragment.get('refresh_token'),expires_in:Number(fragment.get('expires_in')) || 3600,user});
          if (!await isOwner()) { store(null); throw Error('Your email is verified, but database admin access has not been assigned yet.'); }
        }

        try { await freshSession(); if (await isOwner()) return reply(200, {user:publicUser(),setup_required:false}); } catch (_) {}
        store(null);
        return reply(200, {user:visitor,setup_required:false});
      }
      if (path === '/api/locations' && method === 'GET') {
        const reports = await request('/rest/v1/bevstats_reports?select=*&order=current_end.desc,loaded_at.desc,id.desc&limit=1', {});
        if (!reports.length) return reply(200, {locations:[],sample:false,report:null});
        const report = reports[0];
        const rows = [];
        // Supabase may cap responses at 1,000 rows. Page explicitly.
        for (let offset=0; ; offset+=1000) {
          const page = await request('/rest/v1/bevstats_dashboard?select=*&report_id=eq.' + report.id + '&order=id&limit=1000&offset=' + offset, {});
          rows.push(...page);
          if (page.length < 1000) break;
        }
        return reply(200, {sample:false,report,locations:rows.map(r=>({...r,cans:r.current_case_equivalents,previous_cans:r.prior_case_equivalents,price:r.beer_price,updated:r.loaded_at}))});
      }
      return reply(405, {error:'Report data is read-only in the dashboard. Load reports through the database import.'});
    } catch (error) { return reply(error.status || 503, {error:error.message || 'Unable to connect to Supabase'}); }
  };
})();
