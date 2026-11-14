<script lang="ts">
  let { hex, registration = "" }: { hex: string; registration?: string } = $props();
  type Message = { key: string; text: string; flight: string; tail: string; received: number; direction: string; score: number; raw: unknown; hits: { name: string; terms: string[] }[] };
  let messages = $state<Message[]>([]);
  let total = $state(0);
  let error = $state("");
  let state = $state("Loading archive…");
  let days = $state(7);
  let limit = $state(20000);
  let page = $state(0);
  $effect(() => { void hex; void registration; page = 0; });
  $effect(() => {
    const h = hex, reg = registration, offset = page * 100;
    const ctl = new AbortController();
    let busy = false;
    messages = []; total = 0; error = "";
    async function load() {
      if (busy) return;
      busy = true;
      try {
        const q = new URLSearchParams({ hex: h, registration: reg, offset: String(offset) });
        const r = await fetch(`/api/acars?${q}`, { signal: ctl.signal, cache: "no-store" });
        if (!r.ok) throw Error(`Archive HTTP ${r.status}`);
        const data = await r.json();
        if (ctl.signal.aborted) return;
        messages = data.messages; total = data.total; state = data.status.state; days = data.retentionDays; limit = data.maxMessages;
        error = data.status.error || "";
      } catch (e) { if (!ctl.signal.aborted) error = e instanceof Error ? e.message : "Archive unavailable"; }
      finally { busy = false; }
    }
    void load();
    const timer = setInterval(() => void load(), 10000);
    return () => { ctl.abort(); clearInterval(timer); };
  });
</script>
<section class="acars">
  <h3>Recorded ACARS · {total}</h3>
  <p>{state} · <a href="/acars" target="_blank" rel="noreferrer">Top 500 &amp; archive search</a></p>
  <p>Sampled messages captured by this server, not all aircraft communications. Retained up to {days} days, subject to the shared {limit.toLocaleString()}-message and payload caps. Direction is shown as supplied; unknown is not inferred.</p>
  {#if error}<p role="status">{error}</p>{/if}
  {#if !messages.length}<p>No retained messages matched this aircraft yet. Matching uses ICAO24 or registration, never callsign alone.</p>{/if}
  {#each messages as m (m.key)}
    <article>
      <p><strong>{m.flight || m.tail || hex}</strong> · {new Date(m.received * 1000).toISOString()} · {m.direction}</p>
      {#if m.hits.length}<p class="reason">Score {m.score}: {m.hits.map(h => h.name).join(" · ")} — keyword hints, not a verified incident.</p>{/if}
      <pre>{m.text}</pre>
      <details><summary>All supplied message metadata</summary><pre>{JSON.stringify(m.raw, null, 2)}</pre></details>
    </article>
  {/each}
  <nav aria-label="ACARS message pages">
    <button disabled={page === 0} onclick={() => page--}>Newer</button>
    <span>{total ? page * 100 + 1 : 0}–{Math.min((page + 1) * 100, total)} of {total}</span>
    <button disabled={(page + 1) * 100 >= total} onclick={() => page++}>Older</button>
  </nav>
  <p>ACARS data: <a href="https://airframes.io" target="_blank" rel="noreferrer">Airframes.io</a> and its community feeders.</p>
</section>
<style>
.acars{padding:12px;border-radius:8px;background:var(--surface-2);overflow-wrap:anywhere}.acars h3{margin:0 0 8px}.acars p{font-size:12px;line-height:1.5;color:var(--text-dim)}a{color:inherit;text-decoration:underline}article{border-top:1px solid var(--surface-4);padding:10px 0}pre{font:12px/1.6 monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:450px;overflow:auto}nav{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:12px}button{padding:8px;cursor:pointer;background:var(--surface-3);color:inherit;border:0;border-radius:5px}button:disabled{opacity:.4}summary{cursor:pointer}
</style>
