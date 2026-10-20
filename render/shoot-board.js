/* Renderiza un artboard .dc.html del lienzo a PNG y lo recorta en los 4 cajones. */
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');

const SRC = process.argv[2];
const OUT = process.argv[3] || '/home/user/totem/render/art';
const ASSETS = '/home/user/totem/render/assets';
const S = 3;                       // factor de escala
const W = 640, H = 1168;           // tamano del artboard

(async () => {
  let html = fs.readFileSync(SRC, 'utf8');
  const helmet = (html.match(/<helmet>([\s\S]*?)<\/helmet>/) || [, ''])[1];
  let body = (html.match(/<\/helmet>([\s\S]*?)<\/x-dc>/) || [, ''])[1];
  if (!body.trim()) { console.error('no se encontro el cuerpo del artboard'); process.exit(1); }
  const holes = body.match(/\{\{[^}]+\}\}/g);
  if (holes) console.warn('AVISO: huecos sin resolver ->', [...new Set(holes)].join(' '));

  body = body.replace(/\/_blob\/([0-9a-f]{32})/g, (m, id) => {
    const f = path.join(ASSETS, id + '.png');
    if (!fs.existsSync(f)) { console.warn('AVISO: falta el asset', id); return m; }
    return 'data:image/png;base64,' + fs.readFileSync(f).toString('base64');
  });

  const page = `<!doctype html><meta charset="utf-8">${helmet}
<style>html,body{margin:0;padding:0;background:#fff}#root{width:${W}px;height:${H}px}</style>
<div id="root">${body}</div>`;

  const proxy = process.env.HTTPS_PROXY;
  const b = await chromium.launch({
    proxy: proxy ? { server: proxy } : undefined,
    args: ['--allow-file-access-from-files', '--force-device-scale-factor=' + S],
  });
  const p = await b.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: S });
  const errs = [];
  p.on('pageerror', e => errs.push(String(e)));
  p.on('requestfailed', r => errs.push('fallo ' + r.url().slice(0, 90)));
  await p.setContent(page, { waitUntil: 'networkidle' });
  await p.evaluate(async () => { await document.fonts.ready; });
  await p.waitForTimeout(900);

  fs.mkdirSync(OUT, { recursive: true });
  await p.locator('#root').screenshot({ path: path.join(OUT, 'face.png') });
  console.log('cara completa ->', path.join(OUT, 'face.png'), S + 'x');
  console.log('incidencias:', errs.length ? errs : 'ninguna');
  await b.close();
})();
