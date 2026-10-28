/* Browser-only adapter for the public sample-data site. This is not access control. */
(() => {
  'use strict';
  window.BEVSTATS_STATIC_DEMO = true;
  // Keep authentication available for the future data layer; bypass it for now.
  window.BEVSTATS_DEMO_AUTH_ENABLED = false;
  const originalFetch = window.fetch.bind(window);
  const dataKey = 'bevstats.demo.sales.v1';
  const accountKey = 'bevstats.demo.account.v1';
  const sessionKey = 'bevstats.demo.session.v1';
  const encoder = new TextEncoder();
  const reply = (status, body) => new Response(JSON.stringify(body), {
    status, headers: {'Content-Type': 'application/json'}
  });
  const read = (storage, key, fallback) => {
    const text = storage.getItem(key);
    return text === null ? fallback : JSON.parse(text);
  };
  const sampleData = () => ({sample: true, locations: window.BEVSTATS_SAMPLE_LOCATIONS.map((row, index) => ({
    id: index + 1, ...row, updated: new Date().toISOString().slice(0, 19).replace('T', ' ')
  }))});
  const publicUser = account => ({id: 1, username: account.username, display_name: account.username});
  function user() {
    if (!window.BEVSTATS_DEMO_AUTH_ENABLED) return {id: 1, username: 'Corey', display_name: 'Corey'};
    const account = read(localStorage, accountKey, null);
    const session = read(sessionStorage, sessionKey, null);
    return account && session && session.username === account.username && session.expires > Date.now() ? publicUser(account) : null;
  }
  async function hash(password, salt) {
    const key = await crypto.subtle.importKey('raw', encoder.encode(password), 'PBKDF2', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits({name: 'PBKDF2', hash: 'SHA-256', salt: encoder.encode(salt), iterations: 210000}, key, 256);
    return Array.from(new Uint8Array(bits), b => b.toString(16).padStart(2, '0')).join('');
  }
  function cleanRows(rows, previousLocations) {
    if (!Array.isArray(rows) || rows.length > 1000) throw Error('Use up to 1,000 locations.');
    const previous = previousLocations || [];
    const previousById = new Map(previous.map(row => [row.id, row]));
    let nextId = Math.max(0, ...previous.map(row => Number.isInteger(row.id) ? row.id : 0)) + 1;
    const usedIds = new Set();
    return rows.map(row => {
      if (!row || typeof row.name !== 'string' || !row.name.trim() || row.name.trim().length > 80) throw Error('Enter a location name of 1-80 characters.');
      if (!Number.isInteger(row.cans) || row.cans < 0 || row.cans > 100000000) throw Error('Enter a valid whole-number can total.');
      for (const key of ['address', 'salesperson']) {
        if (row[key] !== undefined && (typeof row[key] !== 'string' || row[key].length > 200)) throw Error('Address and salesperson must be text up to 200 characters.');
      }
      if (row.price !== undefined && row.price !== null && (!Number.isFinite(row.price) || row.price < 0 || row.price > 100000)) throw Error('Beer price must be between $0 and $100,000.');
      const id = Number.isInteger(row.id) && row.id > 0 ? row.id : nextId++;
      if (usedIds.has(id)) throw Error('Location IDs must be unique.');
      usedIds.add(id);
      const previous = previousById.get(id);
      return {id, name: row.name.trim(), cans: row.cans,
        address: (row.address || '').trim(), salesperson: (row.salesperson || '').trim(),
        price: row.price ?? null, previous_cans: previous ? previous.cans : null,
        updated: new Date().toISOString().slice(0, 19).replace('T', ' ')};
    });
  }
  window.fetch = async (input, options = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, window.location.href);
    if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/')) return originalFetch(input, options);
    try {
      const method = (options.method || 'GET').toUpperCase();
      const path = url.pathname;
      if (method === 'GET' && path === '/api/session') return reply(200, {
        user: user(), setup_required: window.BEVSTATS_DEMO_AUTH_ENABLED && !read(localStorage, accountKey, null), demo_mode: true, static_demo: true
      });
      if (method === 'POST' && path === '/api/logout') {
        sessionStorage.removeItem(sessionKey);
        return reply(200, {ok: true});
      }
      const body = options.body ? JSON.parse(options.body) : {};
      if (method === 'POST' && ['/api/login', '/api/setup'].includes(path)) {
        let account = read(localStorage, accountKey, null);
        const username = typeof body.username === 'string' ? body.username.trim() : '';
        if (!username || username.length > 80 || typeof body.password !== 'string' || body.password.length > 256) return reply(400, {error: 'Invalid sign-in details.'});
        if (path === '/api/setup') {
          if (account) return reply(409, {error: 'A demo profile already exists in this browser. Please sign in.'});
          if (body.password.length < 4) return reply(400, {error: 'Enter a username and demo password of at least 4 characters.'});
          const salt = Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('');
          account = {username, display_name: username, salt, password_hash: await hash(body.password, salt)};
          // Recheck after asynchronous hashing to avoid replacing a profile from another tab.
          if (read(localStorage, accountKey, null)) return reply(409, {error: 'A demo profile already exists. Please sign in.'});
          localStorage.setItem(accountKey, JSON.stringify(account));
        } else if (!account || account.username.toLowerCase() !== username.toLowerCase() || await hash(body.password, account.salt) !== account.password_hash) {
          return reply(401, {error: 'Incorrect demo username or password.'});
        }
        sessionStorage.setItem(sessionKey, JSON.stringify({username: account.username, expires: Date.now() + 28800000}));
        return reply(200, {user: publicUser(account)});
      }
      if (path === '/api/locations') {
        if (!user()) return reply(401, {error: 'Please sign in to the browser demo.'});
        if (method === 'GET') {
          let data = read(localStorage, dataKey, null);
          if (data === null) {
            data = sampleData();
            localStorage.setItem(dataKey, JSON.stringify(data));
          }
          return reply(200, data);
        }
        if (method === 'POST') {
          const current = read(localStorage, dataKey, null);
          const data = {locations: cleanRows(body.locations, current && current.locations), sample: Boolean(body.sample)};
          localStorage.setItem(dataKey, JSON.stringify(data));
          return reply(200, {ok: true});
        }
      }
      return reply(404, {error: 'Not found'});
    } catch (error) {
      const blocked = ['QuotaExceededError', 'SecurityError'].includes(error.name);
      return reply(400, {error: blocked ? 'Browser storage is unavailable or full. Enable site storage, or export your data before clearing it.' : error.message});
    }
  };
  document.getElementById('restore-demo').classList.remove('hidden');
  document.getElementById('restore-demo').onclick = async () => {
    if (!confirm('Replace this browser\'s sales table with the 18 sample locations? Export CSV first to keep a copy.')) return;
    try {
      localStorage.setItem(dataKey, JSON.stringify(sampleData()));
      // A reload discards any unsaved edit draft as well as refreshing both views.
      window.location.reload();
    } catch (_) {
      alert('Could not save samples. Check that browser storage is enabled.');
    }
  };
})();
