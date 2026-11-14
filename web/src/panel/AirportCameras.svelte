<script lang="ts">
  let { code, name = "" }: { code: string; name?: string } = $props();
  type Camera = { title: string; url: string; note: string };
  const sources: Record<string, Camera[]> = {
    EGKK: [{ title: "Gatwick · AIRLIVE camera directory", url: "https://cam.airlive.net/lgw/", note: "Directory of Gatwick livestream providers; broadcasts can be occasional or offline." }],
    EGLL: [{ title: "Heathrow · plane-spotting webcam page", url: "https://www.webcamtaxi.com/en/england/london/heathrow-airport-cam.html", note: "Third-party webcam page. Check the video timestamp and provider for current availability." }],
  };
  const aliases: Record<string, string> = { LGW: "EGKK", LHR: "EGLL" };
  const icao = $derived(aliases[code.toUpperCase()] || code.toUpperCase());
  const cameras = $derived(sources[icao] || []);
  const query = $derived(`${name || icao} ${icao} airport live plane spotting takeoffs landings`);
  const youtube = $derived(`https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`);
  const search = $derived(`https://www.google.com/search?q=${encodeURIComponent(`${name || icao} ${icao} airport official runway webcam livestream`)}`);
</script>
<section class="cameras" aria-label="Airport cameras and livestreams">
  <h3>Cameras &amp; livestreams</h3>
  <p>Watch takeoffs and landings around {name || icao}. Sources open in a new tab so you can keep the map open.</p>
  {#each cameras as camera (camera.url)}
    <a class="camera" href={camera.url} target="_blank" rel="noopener noreferrer"><strong>{camera.title}</strong><span>{camera.note}</span><small>Camera source · live status not checked</small></a>
  {/each}
  {#if !cameras.length}<p>No curated camera source has been added for this airport yet. This does not mean no camera exists.</p>{/if}
  <a class="camera" href={youtube} target="_blank" rel="noopener noreferrer"><strong>Find streams on YouTube</strong><span>Airport-specific search, not a verified live feed. Results can include recordings, scheduled streams or unrelated videos.</span></a>
  <a class="camera" href={search} target="_blank" rel="noopener noreferrer"><strong>Find airport webcams</strong><span>Search for official airport cameras and other public sources.</span></a>
  <p class="note">Availability, viewing angle and broadcast schedules vary. Streams may be delayed, restricted or offline. Check the provider's timestamp; not for navigation or operational use.</p>
</section>
<style>
.cameras{padding:14px;border-radius:var(--radius);background:var(--surface-2)}h3{margin:0 0 10px;font-size:var(--fs-m)}p,.note{font-size:var(--fs-s);line-height:1.5;color:var(--text-dim)}.camera{display:flex;flex-direction:column;gap:6px;padding:12px;margin:10px 0;border:1px solid var(--surface-4);border-radius:var(--radius-sm);background:var(--surface);text-decoration:none;color:var(--text)}.camera strong{color:var(--accent-text);font-size:var(--fs-s)}.camera span,.camera small{font-size:12px;color:var(--text-dim);line-height:1.5}.camera:hover{border-color:var(--accent-text)}.note{margin-bottom:0}
</style>
