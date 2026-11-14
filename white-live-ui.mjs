import fs from 'node:fs';
let source = fs.readFileSync('src/core/themeState.svelte.ts','utf8');
if (!source.includes('themeState.theme = loadTheme();')) throw Error('Theme initialisation changed; review white-theme patch.');
source = source.replace('applyTheme, loadTheme, saveTheme','applyTheme, saveTheme').replace('themeState.theme = loadTheme();','themeState.theme = "light";');
fs.writeFileSync('src/core/themeState.svelte.ts',source);
for (const path of ['index.html','public/acars.html']) {
  let html = fs.readFileSync(path,'utf8');
  if (!html.includes('</head>')) throw Error('Missing head: '+path);
  html = html.replace('</head>','<link rel="stylesheet" href="/white-ui.css" /></head>');
  if (path === 'public/acars.html') html = html.replace('</head>','<script src="/aircraft-presence.js" defer></script></head>');
  fs.writeFileSync(path,html);
}
