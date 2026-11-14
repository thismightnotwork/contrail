import fs from 'node:fs';
function edit(path, transform) { fs.writeFileSync(path, transform(fs.readFileSync(path, 'utf8'))); }
edit('index.html', source => {
  source = source.split('\n').filter(line => !/og:url|og:image|twitter:image|rel="icon"|rel="apple-touch-icon"/.test(line)).join('\n');
  source = source.replaceAll('Contrail', 'SkySignal').replaceAll('summary_large_image', 'summary');
  source = source.replace(/<title>.*?<\/title>/, '<title>SkySignal | Aircraft &amp; ACARS</title>');
  source = source.replaceAll('Live air traffic map with smooth aircraft motion, flight details and airport weather.', 'Aircraft. Messages. Context. Explore aircraft positions and the sampled ACARS messages captured by your server.');
  source = source.replace('#0d0f12', '#07111f');
  return source.replace('</head>', '<link rel="icon" href="/skysignal.svg" type="image/svg+xml" /><link rel="stylesheet" href="/skysignal.css" /></head>');
});
edit('src/App.svelte', source => {
  const start = source.indexOf('      <svg viewBox="0 0 32 32"');
  const end = source.indexOf('      <span>Contrail</span>', start);
  if (start < 0 || end < 0) throw Error('Map branding anchors changed; review before building.');
  source = source.slice(0, start) + '      <img src="/skysignal.svg" width="30" height="30" alt="" />\n      <span>SkySignal<small>Aircraft. Messages. Context.</small></span>' + source.slice(end + '      <span>Contrail</span>'.length);
  return source.replace('Contrail, live air traffic map', 'SkySignal, aircraft map and recorded ACARS').replace('display: none;\n    align-items: center;', 'display: inline-flex;\n    align-items: center;');
});
edit('src/Root.svelte', s => s.replace('Contrail hit an unexpected error', 'SkySignal hit an unexpected error'));
edit('public/acars.html', source => source.replace('<title>Contrail · ACARS archive</title>', '<title>SkySignal | ACARS archive</title>').replace('</head>', '<link rel="icon" href="/skysignal.svg" type="image/svg+xml" /><link rel="stylesheet" href="/skysignal.css" /></head>').replace('<body>', '<body class="sky-archive">').replace('<h1>ACARS Top 500 &amp; aircraft archive</h1>', '<header class="sky-heading"><img src="/skysignal.svg" width="52" height="52" alt="" /><div><h1>SkySignal</h1><p>Aircraft. Messages. Context.</p></div></header><h2>ACARS Top 500 &amp; aircraft archive</h2>').replace('</main>', '<footer class="sky-footer">SkySignal · Built on <a href="https://github.com/MaciejZiel/contrail" target="_blank" rel="noreferrer">Contrail</a>. Keyword highlights are not verified incidents.</footer></main>'));
edit('index.html', s => s.replace('>ACARS Top 500</a>', ' class="sky-archive-link">ACARS Top 500</a>'));
