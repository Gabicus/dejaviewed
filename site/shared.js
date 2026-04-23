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
  const BASE = (function(){
    const p = location.pathname;
    const dir = p.substring(0, p.lastIndexOf('/') + 1);
    if (dir.endsWith('/guides/') || dir.endsWith('/e/')) return '../';
    return '';
  })();

  DV.nav = function nav(active){
    const items = [
      { id:'graph',    href:BASE+'graph.html',        label:'Graph · Force'  },
      { id:'cosmos',   href:BASE+'graph-cosmos.html', label:'Graph · Cosmos' },
      { id:'board',    href:BASE+'board.html',        label:'Board'   },
      { id:'admin',    href:BASE+'admin.html',        label:'Admin'   },
    ];
    return DV.el('div', { class:'nav' }, items.map(it =>
      DV.el('a', { href: it.href, class: (active===it.id?'active':'') }, it.label)
    ));
  };

  // ── Header builder — mount with DV.mountHeader(document.body, 'catalog') ──
  //   The title reads "Home" and links to index.html. That's the home pill;
  //   there is no separate Home nav item.
  DV.mountHeader = function mountHeader(root, activeId){
    const nav = DV.nav(activeId);
    const burger = DV.el('button', { class:'hamburger', 'aria-label':'Menu', onclick: function(){
      nav.classList.toggle('open');
      this.textContent = nav.classList.contains('open') ? '✕' : '☰';
    }}, '☰');
    const h = DV.el('header', { class:'site' }, [
      DV.el('h1', null, [DV.el('a', { href:BASE+'index.html' }, 'DejaViewed')]),
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

    if (opts.filters){
      const ctrl = typeof opts.filters === 'string' ? document.querySelector(opts.filters) : opts.filters;
      if (ctrl){
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
  DV.guideUrl = function guideUrl(slug){ return slug ? BASE+'guides/'+encodeURIComponent(slug)+'.html' : null; };

  // ── Entry internal URL — anchors into the catalog home page ──
  DV.entryUrl = function entryUrl(id){ return BASE+'index.html#post-'+encodeURIComponent(id); };
})();
