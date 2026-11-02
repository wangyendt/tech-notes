// Synthetic DOM/service events: these do not prove live GitHub or counter behavior.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../content/javascripts/engagement.js'), 'utf8');

function fixture({ origin = 'https://wangyendt.github.io', search = '',
  pathname = '/tech-notes/systems/example/', enabled = true, categoryId = 'TEST_CATEGORY',
  pageviews = true, hasSection = true } = {}) {
  const element = () => ({ textContent: '', hidden: false, style: {}, children: [],
    attrs: {}, appendChild(child) { this.children.push(child); },
    setAttribute(key, value) { this.attrs[key] = value; } });
  const status = element(), comments = element(), value = element(), counter = element();
  const container = element(), head = element(), body = element();
  body.dataset = { mdColorScheme: 'default' };
  const messages = [];
  const frame = { contentWindow: { postMessage: (...args) => messages.push(args) } };
  container.querySelector = () => frame;
  const section = {
    dataset: { canonical: 'https://wangyendt.github.io/tech-notes/systems/example/',
      giscusEnabled: String(enabled), repo: 'test/repo', repoId: 'TEST_REPO',
      category: 'Announcements', categoryId },
    querySelector: (s) => ({ '[data-pageviews-status]': pageviews ? status : null,
      '[data-giscus-status]': comments, '.pageviews': counter, '.giscus': container })[s]
  };
  const observers = [], timers = new Map(), events = {};
  const context = {
    URL, location: { origin, pathname, search },
    document: { head, body,
      querySelector: (s) => s === '.engagement' ? (hasSection ? section : null) : null,
      getElementById: (s) => s === 'busuanzi_value_page_pv' ? value : counter,
      createElement: element },
    window: { addEventListener: (type, cb) => { events[type] = cb; } },
    MutationObserver: class {
      constructor(cb) { this.cb = cb; observers.push(this); }
      observe(target) { this.target = target; }
      disconnect() { this.disconnected = true; }
    },
    setTimeout: (cb) => { const id = timers.size + 1; timers.set(id, cb); return id; },
    clearTimeout: (id) => timers.delete(id)
  };
  vm.runInNewContext(source, context);
  return { status, comments, value, counter, container, head, body, observers, timers,
    events, frame, messages };
}

test('directory pages and local previews send no third-party requests', () => {
  for (const options of [{ hasSection: false }, { origin: 'http://localhost:8000' }]) {
    const f = fixture(options);
    assert.equal(f.head.children.length + f.container.children.length, 0);
  }
});

test('disabled or incomplete giscus never injects a client', () => {
  for (const options of [{ enabled: false }, { categoryId: '' }]) {
    const f = fixture(options);
    assert.equal(f.container.children.length, 0);
    assert.equal(f.head.children.length, 1);
  }
  assert.equal(fixture({ pageviews: false }).head.children.length, 0);
});

test('query strings (including OAuth credentials) and index aliases never reach busuanzi', () => {
  for (const options of [{ search: '?giscus=SYNTHETIC_SESSION' }, { search: '?utm_source=test' },
    { pathname: '/tech-notes/systems/example/index.html' }]) {
    const f = fixture(options);
    assert.equal(f.head.children.length, 0);
    assert.equal(f.container.children[0].attrs['data-term'], '/tech-notes/systems/example/');
  }
});

test('counter handles actual zero, timeout, late success, and network failure', () => {
  const f = fixture({ enabled: false });
  assert.match(f.head.children[0].src, /^https:\/\/busuanzi\.ibruce\.info\//);
  [...f.timers.values()][0]();
  assert.match(f.status.textContent, /暂不可用/);
  assert.equal(f.status.hidden, false);
  f.value.textContent = '0';
  f.observers[0].cb();
  assert.equal(f.status.hidden, true);
  assert.equal(f.observers[0].disconnected, true);
  const error = fixture({ enabled: false });
  error.head.children[0].onerror();
  assert.match(error.status.textContent, /暂不可用/);
});

test('giscus is Chinese, strict, and enables reactions with a stable key', () => {
  const f = fixture();
  const attrs = f.container.children[0].attrs;
  assert.equal(attrs['data-lang'], 'zh-CN');
  assert.equal(attrs['data-mapping'], 'specific');
  assert.equal(attrs['data-strict'], '1');
  assert.equal(attrs['data-reactions-enabled'], '1');
  assert.equal(attrs['data-term'], '/tech-notes/systems/example/');
  assert.equal(attrs['data-theme'], 'light');
});

test('only messages from the giscus iframe update readiness; theme follows the page', () => {
  const f = fixture();
  const good = { origin: 'https://giscus.app', source: f.frame.contentWindow,
    data: { giscus: { resizeHeight: 300 } } };
  f.events.message({ ...good, origin: 'https://example.org' });
  assert.equal(f.comments.hidden, false);
  f.events.message({ ...good, source: {} });
  assert.equal(f.comments.hidden, false);
  f.events.message(good);
  assert.equal(f.comments.hidden, true);
  f.body.dataset.mdColorScheme = 'slate';
  f.observers.find(o => o.target === f.body).cb();
  assert.equal(f.messages[0][0].giscus.setConfig.theme, 'dark');
  assert.equal(f.messages[0][1], 'https://giscus.app');
  f.events.message({ ...good, data: { giscus: { error: 'SYNTHETIC_FAILURE' } } });
  assert.equal(f.comments.hidden, false);
  assert.match(f.comments.textContent, /暂不可用/);
});

test('giscus load errors and timeouts are visible and do not remove article content', () => {
  const f = fixture({ pageviews: false });
  [...f.timers.values()][0]();
  assert.match(f.comments.textContent, /暂不可用/);
  f.container.children[0].onerror();
  assert.match(f.comments.textContent, /暂不可用/);
});

test('a missing discussion is the normal empty state, including after a timeout', () => {
  const f = fixture({ pageviews: false });
  [...f.timers.values()][0]();
  assert.equal(f.comments.hidden, false);
  f.events.message({ origin: 'https://giscus.app', source: f.frame.contentWindow,
    data: { giscus: { error: 'Discussion not found' } } });
  assert.equal(f.comments.hidden, true);
});
