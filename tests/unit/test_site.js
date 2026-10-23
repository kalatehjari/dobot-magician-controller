// Checks the website in docs/ (GitHub Pages): the app copy, links, search-engine tags (node tests/unit/test_site.js)
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..', '..'), DOCS = path.join(ROOT, 'docs');
const SITE = 'https://kalatehjari.github.io/dobot-magician-controller/';
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };
const read = f => fs.readFileSync(path.join(DOCS, f), 'utf8');
const version = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8')).version;

// the app on the website is the built app, byte for byte
const app = fs.readFileSync(path.join(ROOT, 'magician-smart-controller.html'));
const siteApp = fs.existsSync(path.join(DOCS, 'app', 'index.html')) ? fs.readFileSync(path.join(DOCS, 'app', 'index.html')) : Buffer.alloc(0);
t('docs/app/index.html is the same file as magician-smart-controller.html (run python3 build.py)', app.equals(siteApp), `${siteApp.length} bytes`);

const home = read('index.html');
const meta = (attr, name) => { const m = home.match(new RegExp(`<meta ${attr}="${name}" content="([^"]*)"`)); return m ? m[1] : null; };
const title = (home.match(/<title>([^<]*)<\/title>/) || [])[1] || '';
const desc = meta('name', 'description') || '';
t('home page: title and description fit in search results', title.length >= 20 && title.length <= 65 && desc.length >= 70 && desc.length <= 160, `${title.length} / ${desc.length} characters`);
t('home page: canonical address is the site root', home.includes(`<link rel="canonical" href="${SITE}">`));
t('home page: keeps the Google Search Console verification tag', /<meta name="google-site-verification" content="[\w-]{20,}">/.test(home));
t('home page: exactly one h1', (home.match(/<h1[\s>]/g) || []).length === 1);
const levels = [...home.matchAll(/<h([1-6])[\s>]/g)].map(m => +m[1]);
t('home page: headings do not skip a level', levels.every((l, i) => i === 0 || l <= levels[i - 1] + 1), levels.join(''));

// structured data
let ld = null;
try { ld = JSON.parse((home.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/) || [])[1]); } catch (e) { ld = null; }
const node = type => ld && ld['@graph'].find(n => n['@type'] === type);
t('structured data parses: WebSite, WebApplication, SoftwareSourceCode, FAQPage', !!(node('WebSite') && node('WebApplication') && node('SoftwareSourceCode') && node('FAQPage')));
t(`structured data and the page show version ${version}`, node('WebApplication') && node('WebApplication').softwareVersion === version && home.includes(`version ${version}`));
const faqLd = node('FAQPage') ? node('FAQPage').mainEntity.map(q => q.name) : [];
const faqPage = [...home.matchAll(/<summary>([^<]*)<\/summary>/g)].map(m => m[1].replace(/&amp;/g, '&'));
t('every question in the structured data is on the page, in the same order', faqLd.length > 0 && faqLd.join('|') === faqPage.join('|'), `${faqLd.length} questions`);

// every local link and picture exists; every #anchor has a target
const local = u => {
  if (u.startsWith(SITE)) u = u.slice(SITE.length);
  else if (u.startsWith('/dobot-magician-controller/')) u = u.slice('/dobot-magician-controller/'.length);
  else if (/^(https?:|mailto:|#)/.test(u)) return null;
  u = u.split('#')[0];
  if (u === '' || u === './' || u.endsWith('/')) u += 'index.html';
  return u.replace(/^\.\//, '');
};
const missing = [];
for (const f of ['index.html', '404.html']) {
  const html = read(f);
  for (const m of html.matchAll(/(?:href|src)="([^"]+)"|<meta property="og:image" content="([^"]+)"/g)) {
    const p = local(m[1] || m[2]);
    if (p && !fs.existsSync(path.join(DOCS, p))) missing.push(`${f}: ${m[1] || m[2]}`);
  }
}
const ids = new Set([...home.matchAll(/ id="([^"]+)"/g)].map(m => m[1]));
for (const m of home.matchAll(/href="#([^"]+)"/g)) if (!ids.has(m[1])) missing.push('#' + m[1]);
t('every local link, picture and anchor exists', missing.length === 0, missing.join(', '));
const imgs = [...home.matchAll(/<img [^>]*>/g)].map(m => m[0]);
t('every picture has alt text, width and height; only the first loads eagerly', imgs.length > 0 && imgs.every(i => / alt="[^"]+"/.test(i) && / width="\d+"/.test(i) && / height="\d+"/.test(i)) &&
  /fetchpriority="high"/.test(imgs[0]) && imgs.slice(1).every(i => /loading="lazy"/.test(i)), `${imgs.length} pictures`);

// sitemap, 404 page, IndexNow key, no Jekyll
const locs = [...read('sitemap.xml').matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
t('sitemap lists the home page and the app, all under the site and existing', locs.includes(SITE) && locs.includes(SITE + 'app/') && locs.every(u => u.startsWith(SITE) && fs.existsSync(path.join(DOCS, local(u)))), locs.join(' '));
t('404 page is not indexed and links back with absolute paths', /<meta name="robots" content="noindex">/.test(read('404.html')) && !/href="(?!\/|https?:)/.test(read('404.html')));
const keys = fs.readdirSync(DOCS).filter(f => /^[a-zA-Z0-9-]{8,128}\.txt$/.test(f) && read(f) === f.slice(0, -4));
t('IndexNow key file: its name is its content', keys.length === 1, keys.join(''));
t('.nojekyll is there, so GitHub Pages serves the files as they are', fs.existsSync(path.join(DOCS, '.nojekyll')));

console.log(fails ? `\n${fails} FAILED` : '\nall website tests passed');
process.exit(fails ? 1 : 0);
