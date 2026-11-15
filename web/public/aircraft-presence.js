/* Classic script intentionally shares the dashboard's lexical scope. */
(() => {
  const normalise = value => String(value || '').toUpperCase().replace(/[^A-Z0-9]/g,'');
  const toggle = node('input');
  toggle.type = 'checkbox';
  toggle.id = 'include-archived-aircraft';
  toggle.checked = false;
  toggle.setAttribute('aria-describedby','aircraft-presence-note');
  const label = node('label');
  label.style.cssText = 'display:inline-flex;align-items:center;gap:8px;cursor:pointer';
  label.append(toggle,document.createTextNode('Include archived aircraft'));
  label.title = 'Also show messages from historical and unknown-status aircraft. This does not change message retention.';
  const tools = $('only').closest('.tools');
  tools.insertBefore(label,$('sort'));
  const note = node('p','Live aircraft only. Loading aircraft-position status…','presence-note');
  note.id = 'aircraft-presence-note';
  tools.after(note);
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
  matching = function() { const rows = originalMatching(); return toggle.checked ? rows : rows.filter(m => classify(m) === 'live'); };
  function updateNote() {
    note.textContent = (toggle.checked ? 'Live + archived aircraft (including unknown status). ' : 'Live aircraft only. ')+(failure ? failure+' · tracking status unknown. ' : '')+'Live = matched position within 2 minutes, regardless of message age. Historical = not recently seen in this server’s cached aircraft feed; not proof of landing or absence worldwide. '+(snapshot && snapshot.ready ? snapshot.aircraft.length+' recent aircraft in cached coverage.' : 'Waiting for tracking status.')+' Filters apply to loaded messages; archive retention is unchanged.';
  }
  const originalRender = render;
  render = function() {
    updateNote();
    originalRender();
    if (!data) return;
    const rows = matching().slice(0,shown);
    document.querySelectorAll('#messages > article').forEach((card,i) => {
      if (!rows[i]) return;
      const status = classify(rows[i]);
      const text = status === 'live' ? 'Live aircraft' : status === 'historical' ? 'Historical · not recently seen here' : 'Tracking status unknown';
      const badge = node('span',text,'badge presence-'+status);
      badge.title = 'Based on server-cached ADS-B coverage, not a complete global aircraft feed.';
      card.querySelector('.meta')?.append(badge);
    });
    if (!matching().length && !toggle.checked) $('empty').textContent = !snapshot || !snapshot.ready ? 'Aircraft tracking status is unavailable or loading. Enable Include archived aircraft to view stored messages.' : 'No loaded messages match live aircraft and your current filters. Enable Include archived aircraft to include historical and unknown-status aircraft. Live status depends on cached map coverage.';
  };
  toggle.onchange = () => { shown = 50; render(); };
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
    finally { loading = false; if (!paused) render(); }
  }
  const oldPause = $('pause').onclick;
  $('pause').onclick = function(event) { oldPause.call(this,event); if (!paused) void refresh(); };
  setInterval(() => void refresh(),10000);
  render();
  void refresh();
})();
