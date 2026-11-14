/* Classic script intentionally shares the dashboard's lexical scope. */
(() => {
  const normalise = value => String(value || '').toUpperCase().replace(/[^A-Z0-9]/g,'');
  const select = node('select');
  select.id = 'aircraft-presence';
  select.setAttribute('aria-label','Aircraft tracking status');
  for (const [value,label] of [['all','All aircraft'],['live','Live aircraft'],['historical','Historical aircraft'],['unknown','Unknown status']]) {
    const option = node('option',label); option.value = value; select.append(option);
  }
  $('only').closest('.tools').insertBefore(select,$('sort'));
  const note = node('p','Loading aircraft-position status…','presence-note');
  select.closest('.tools').after(note);
  let snapshot = null, failure = '', loading = false;
  const classify = message => {
    if (!snapshot || !snapshot.ready || Date.now()/1000 - snapshot.generatedAt > 30) return 'unknown';
    const hex = String(message.hex || '').toLowerCase(), reg = normalise(message.tail);
    if (!hex && !reg) return 'unknown';
    const now = Date.now()/1000;
    const found = snapshot.aircraft.some(a => now - a.positionTime <= snapshot.maxAgeSeconds && (hex ? a.hex === hex : reg && a.registration === reg));
    return found ? 'live' : 'historical';
  };
  const originalMatching = matching;
  matching = function() { const rows = originalMatching(); return select.value === 'all' ? rows : rows.filter(m => classify(m) === select.value); };
  const originalRender = render;
  render = function() {
    originalRender();
    if (!data) return;
    const rows = matching().slice(0,shown);
    document.querySelectorAll('#messages > article').forEach((card,i) => {
      if (!rows[i]) return;
      const status = classify(rows[i]);
      const label = status === 'live' ? 'Live aircraft' : status === 'historical' ? 'Historical · not recently seen here' : 'Tracking status unknown';
      const badge = node('span',label,'badge presence-'+status);
      badge.title = 'Based on server-cached ADS-B coverage, not a complete global aircraft feed.';
      card.querySelector('.meta')?.append(badge);
    });
    if (!matching().length && messages.length && select.value !== 'all') $('empty').textContent = 'No loaded messages match this aircraft-status filter. Try All aircraft; status depends on cached map coverage.';
  };
  select.onchange = () => { shown = 50; render(); };
  async function refresh() {
    if (loading || paused) return;
    loading = true;
    try {
      const response = await fetch('/api/acars-tracking',{cache:'no-store'});
      if (!response.ok) throw Error('Tracking HTTP '+response.status);
      const next = await response.json();
      if (paused) return;
      snapshot = next; failure = '';
    } catch (error) { failure = error.message; snapshot = null; }
    finally {
      loading = false;
      if (!paused) {
        note.textContent = (failure ? failure+' · status unknown. ' : '')+'Live = matched position within 2 minutes. Historical = not recently seen in this server’s cached aircraft feed; not proof of landing or absence worldwide. Unidentified/stale status remains Unknown. '+(snapshot ? snapshot.aircraft.length+' recent aircraft in cached coverage.' : 'Waiting for tracking status.');
        render();
      }
    }
  }
  const oldPause = $('pause').onclick;
  $('pause').onclick = function(event) { oldPause.call(this,event); if (!paused) void refresh(); };
  setInterval(() => void refresh(),10000);
  void refresh();
})();
