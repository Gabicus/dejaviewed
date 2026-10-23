// shared.js — small utilities used by every DejaViewed page.
// Kept deliberately tiny — no framework, no bundler, no fetch when we can avoid it.

(function(){
  // Expose a lightweight namespace
  const DV = window.DV = window.DV || {};

  // ── Catalog loader (works on file:// via catalog.js + falls back to fetch) ──
  DV.loadCatalog = async function loadCatalog(){
    if (window.__CATALOG) return window.__CATALOG;
    try {
      const r = await fetch('catalog.json');
      if (!r.ok) throw new Error('HTTP '+r.status);
      return await r.json();
    } catch (e) {
      console.warn('catalog fetch failed, relying on window.__CATALOG', e);
      return null;
    }
  };

  // ── Summaries loader (landing/core) ──
  DV.loadSummaries = async function loadSummaries(){
    if (window.__SUMMARIES) return window.__SUMMARIES;
    try { const r = await fetch('summaries.json'); return r.ok ? r.json() : null; }
    catch { return null; }
  };

  // ── Recommendations loader (landing) ──
  DV.loadRecommendations = async function loadRecommendations(){
    if (window.__RECOMMENDATIONS) return window.__RECOMMENDATIONS;
    try { const r = await fetch('recommendations.json'); return r.ok ? r.json() : null; }
    catch { return null; }
  };

  // ── DOM helpers (no innerHTML for user-provided content; these only
  //     accept trusted static strings for tag names) ──
  DV.el = function el(tag, attrs, children){
    const n = document.createElement(tag);
    if (attrs) for (const [k,v] of Object.entries(attrs)){
      if (v === false || v === null || v === undefined) continue;
      if (k === 'class') n.className = v;
      else if (k === 'dataset') for (const [dk,dv] of Object.entries(v)) n.dataset[dk]=dv;
      else if (k.startsWith('on') && typeof v === 'function') n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v);
    }
    if (children != null){
      if (!Array.isArray(children)) children = [children];
      for (const c of children){
        if (c == null || c === false) continue;
        n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
      }
    }
    return n;
  };

  // ── Nav builder — every page uses this for consistency ──
  // Over http(s) every link is a root-absolute clean URL (/catalog, /guides/) — what
  // Cloudflare Pages serves without a 308 hop. Clean URLs can't resolve on file://, so
  // local file previews keep relative .html links (or run scripts/serve.py instead).
  const IS_FILE = location.protocol === 'file:';
  const BASE = (function(){
    if (!IS_FILE) return '/';
    const p = location.pathname;
    const dir = p.substring(0, p.lastIndexOf('/') + 1);
    if (/\/(guides|e|deeper|collections|links)\/$/.test(dir)) return '../';
    return '';
  })();
  DV.BASE = BASE;
  // page URL: DV.url('catalog') -> '/catalog' (http) | 'catalog.html' (file://);
  // DV.url('guides/') -> '/guides/' | 'guides/index.html'
  DV.url = function url(page){
    if (!IS_FILE) return BASE + page;
    if (page === '') return BASE + 'index.html';
    return BASE + (page.endsWith('/') ? page + 'index.html' : page + '.html');
  };

  DV.nav = function nav(active){
    const items = [
      { id:'catalog',  href:DV.url('catalog'),      label:'Catalog' },
      { id:'start',    href:DV.url('start-here'),   label:'Start here' },
      { id:'guides',   href:DV.url('guides/'),      label:'Guides'  },
      { id:'prompts',  href:DV.url('prompts'),      label:'Prompts' },
      { id:'search',   href:DV.url('search'),       label:'Search'  },
      { id:'graph',    href:DV.url('graph'),        label:'Graph · Force'  },
      { id:'cosmos',   href:DV.url('graph-cosmos'), label:'Graph · Cosmos' },
      { id:'board',    href:DV.url('board'),        label:'Board'   },
      { id:'about',    href:DV.url('about/'),       label:'About'   },
      // Entries (/e/) and Collections (/collections/) live in the static footer nav
      // (scripts/normalize_links.py) — this bar is already 9 items wide.
      // Admin is intentionally not in the public nav — still reachable at admin.html
    ];
    return DV.el('div', { class:'nav' }, items.map(it =>
      DV.el('a', { href: it.href, class: (active===it.id?'active':'') }, it.label)
    ));
  };

  // ── Header builder — mount with DV.mountHeader(document.body, 'catalog') ──
  //   The wordmark links to / (the showcase landing); the catalog
  //   lives at /catalog. There is no separate Home nav item.
  // The wordmark is a <div class="brand">, not an <h1>: every page owns its single <h1>, and a
  // JS-injected second one confuses crawlers that render scripts. shared.css styles
  // `header.site h1`, so the same look is injected once here for `.brand`.
  function brandStyle(){
    if (document.getElementById('dv-brand-css')) return;
    const st = document.createElement('style');
    st.id = 'dv-brand-css';
    st.textContent = "header.site .brand{margin:0;padding:0;font-weight:900;font-size:22px;line-height:1;"
      + "letter-spacing:-0.03em;background:linear-gradient(135deg,#fff 0%,var(--accent) 45%,var(--accent-2) 100%);"
      + "-webkit-background-clip:text;background-clip:text;color:transparent;font-family:inherit}"
      + "header.site .brand a{color:inherit;text-decoration:none}"
      + "@media(max-width:640px){header.site .brand{font-size:18px}}";
    document.head.appendChild(st);
  }

  DV.mountHeader = function mountHeader(root, activeId){
    brandStyle();
    const nav = DV.nav(activeId);
    const burger = DV.el('button', { class:'hamburger', 'aria-label':'Menu', onclick: function(){
      nav.classList.toggle('open');
      this.textContent = nav.classList.contains('open') ? '✕' : '☰';
    }}, '☰');
    const h = DV.el('header', { class:'site' }, [
      DV.el('div', { class:'brand' }, [DV.el('a', { href:DV.url('') }, 'DejaViewed')]),
      burger,
      nav,
    ]);
    root.prepend(h);
    return h;
  };

  DV.isMobile = function(){ return window.innerWidth <= 900; };

  DV.mountMobileToggles = function mountMobileToggles(opts){
    const backdrop = DV.el('div', { class:'panel-backdrop', onclick: function(){ DV.closeMobilePanels(); }});
    document.body.appendChild(backdrop);
    DV._backdrop = backdrop;
    DV._mobilePanels = [];

    function addCloseBtn(panel){
      var close = DV.el('button', { class:'mobile-panel-close', onclick: function(){ DV.closeMobilePanels(); }}, 'Done');
      panel.appendChild(close);
    }

    if (opts.filters){
      const ctrl = typeof opts.filters === 'string' ? document.querySelector(opts.filters) : opts.filters;
      if (ctrl){
        addCloseBtn(ctrl);
        const btn = DV.el('button', { class:'mobile-toggle filters-btn', onclick: function(){
          DV.closeMobilePanels();
          ctrl.classList.add('open');
          backdrop.classList.add('vis');
        }}, 'Filters');
        document.body.appendChild(btn);
        DV._mobilePanels.push({ el:ctrl, btn:btn });
      }
    }
    if (opts.utils){
      const um = typeof opts.utils === 'string' ? document.querySelector(opts.utils) : opts.utils;
      if (um){
        addCloseBtn(um);
        const btn = DV.el('button', { class:'mobile-toggle utils-btn', onclick: function(){
          DV.closeMobilePanels();
          um.classList.add('vis');
          backdrop.classList.add('vis');
        }}, 'Utils');
        document.body.appendChild(btn);
        DV._mobilePanels.push({ el:um, btn:btn });
      }
    }
  };

  DV.closeMobilePanels = function(){
    if (DV._backdrop) DV._backdrop.classList.remove('vis');
    document.querySelectorAll('.controls.open').forEach(function(c){ c.classList.remove('open'); });
    document.querySelectorAll('#u-menu.vis').forEach(function(m){ m.classList.remove('vis'); });
  };

  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape') DV.closeMobilePanels();
  });

  // ── Tier pill ──
  DV.tierPill = function tierPill(tier){
    const t = String(tier||'C').toUpperCase();
    return DV.el('span', { class:'tier-pill tier-'+t.toLowerCase() }, t);
  };

  // ── Guide URL from CMS slug ──
  DV.guideUrl = function guideUrl(slug){ return slug ? DV.url('guides/'+encodeURIComponent(slug)) : null; };

  // ── Entry internal URL — anchors into the catalog home page ──
  DV.entryUrl = function entryUrl(id){ return DV.url('catalog')+'#post-'+encodeURIComponent(id); };
})();
