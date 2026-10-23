/* =============================================================================
 * DejaViewed /flow — how the archive flows.
 *
 * Data: /flow_data.json (scripts/build_flow.py). Six vertical bands in data-flow order:
 *   Sources -> Pillars -> Tools/models/repos -> Techniques -> Guides & deeper -> Outputs.
 *
 * Ported from the Unicron Atlas (unicron/atlas/app.js, same owner):
 *   - "zones" layout: one band per zone, nodes stacked down the band, sankey-style horizontal
 *     cubic edges (section 5). Here the layout is fully deterministic (no simulation): nodes are
 *     ordered by barycenter of their upstream neighbours, bar height is proportional to count.
 *   - particle flow layer (section 11): a fixed ring of evenly phased particles per edge, phase
 *     from a djb2 hash of the edge key, so the layer allocates nothing per frame and its only
 *     state is elapsed time. performance.now() drives animation only; particles never move nodes.
 *     Paused when the tab is hidden; off by default under prefers-reduced-motion.
 * SVG draws structure, a single <canvas> overlay draws particles with the same transform.
 * ========================================================================== */
(function () {
  "use strict";

  /* ---- 1. constants ------------------------------------------------------ */
  var ZONE_COLOR = ["#e060a0", "#a78bfa", "#f0a050", "#60a5fa", "#4cda8c", "#fbbf24"];
  var LANE_COLOR = { anthropic: "#e08a5f", openai: "#34c79a", google: "#5b9cf6", "open-weight": "#c084fc",
                     creative: "#f472b6", automation: "#40d0e0", quant: "#fbbf24" };
  var LANE_LABEL = { anthropic: "Anthropic", openai: "OpenAI", google: "Google", "open-weight": "Open-weight",
                     creative: "Creative", automation: "Automation", quant: "Quant" };
  var KIND_LABEL = { collection: "Collection", creator: "Creator", "creator-group": "Creators (folded)",
    pillar: "Pillar", tool: "Tool", model: "Model", repo: "Repo", technique: "Technique", guide: "Guide",
    "prompt-system": "Prompt system", kit: "Content kit", hub: "Tool hub", compare: "Comparison",
    best: "Best-of", "system-prompts": "System prompts", "collection-pages": "Collection pages" };
  var OUT_BLOCK = { "prompt-system": 0, kit: 1, hub: 2, compare: 3, best: 3, "system-prompts": 3, "collection-pages": 3 };
  var SRC_BLOCK = { collection: 0, creator: 1, "creator-group": 2 };
  var BRIDGE = { "pillar-guide": [2, 3], "tool-guide": [3] };   // edge kind -> zones it skips
  var TIERS = ["S", "A", "B", "C"];
  var MOBILE_W = 760, BAR_W = 12, PAD_T = 44, PAD_B = 14, GAP = 2, MIN_H = 2.2;
  var PARTICLE_CAP = 2000, PARTICLE_R = 1.7;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- 2. state ---------------------------------------------------------- */
  var D = null, byId = new Map(), edges = [], nodes = [], outE = new Map(), inE = new Map();
  var st = { lanes: new Set(), tiers: new Set(TIERS), node: null, path: null, panel: null,
             collapsed: new Set(), bridges: false, particles: !reduceMotion };
  var panelOpen = false, W = 0, H = 0, dpr = 1, mobile = false, curT = d3.zoomIdentity, zoom = null;
  var svg, gRoot, gBands, gEdges, gRoute, gNodes, canvas, ctx;
  var nodeSel, edgeSel, xOf = [], laneIdx = {};

  var $ = function (id) { return document.getElementById(id); };
  var el = DV.el;

  /* ---- 3. load ----------------------------------------------------------- */
  fetch("/flow_data.json").catch(function () { return fetch("flow_data.json"); })
    .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(boot)
    .catch(function (e) { $("flow-loading").textContent = "Could not load flow data (" + e.message + ")."; });

  function boot(data) {
    D = data;
    D.lanes.forEach(function (l, i) { laneIdx[l] = i; });
    nodes = D.nodes;
    nodes.forEach(function (n) { byId.set(n.id, n); outE.set(n.id, []); inE.set(n.id, []); });
    edges = D.edges.filter(function (e) { return byId.has(e.source) && byId.has(e.target); });
    edges.forEach(function (e, i) {
      e.i = i; e.s = byId.get(e.source); e.t = byId.get(e.target);
      e.key = e.source + ">" + e.target; e.bridge = !!BRIDGE[e.kind];
      outE.get(e.source).push(e); inE.get(e.target).push(e);
    });
    buildControls();
    buildScene();
    readHash();
    layout(true);
    applyState();
    $("flow-loading").remove();
    var rt = null;
    window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(function () { layout(true); applyState(); }, 150); });
    window.addEventListener("hashchange", function () { if (!writingHash) { readHash(); layout(false); applyState(); } });
    document.addEventListener("visibilitychange", function () { if (particlesWanted()) startParticles(); else stopParticles(); });
    document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { st.node = null; st.path = null; st.panel = null; applyState(); } });
  }

  /* ---- 4. controls ------------------------------------------------------- */
  function btn(label, on, onclick, sw, title) {
    var b = el("button", { class: "fbtn" + (on ? " on" : ""), type: "button", title: title || null, onclick: onclick },
      sw ? [el("span", { class: "sw", style: "background:" + sw }), label] : label);
    return b;
  }
  function buildControls() {
    var lanes = $("flow-lanes");
    D.lanes.forEach(function (l) {
      var n = nodes.reduce(function (a, x) { return a + (x.zone === 2 && x.lanes[l] ? 1 : 0); }, 0);
      var b = btn(LANE_LABEL[l] || l, false, function () { toggle(st.lanes, l); applyState(); }, LANE_COLOR[l],
        "Light up the " + (LANE_LABEL[l] || l) + " ecosystem (" + n + " tool nodes)");
      b.dataset.lane = l; b.setAttribute("aria-pressed", "false");
      lanes.appendChild(b);
    });
    var tiers = $("flow-tiers");
    TIERS.forEach(function (t) {
      var b = btn(t, true, function () {
        if (st.tiers.has(t) && st.tiers.size === 1) return;   // never filter everything away
        toggle(st.tiers, t); applyState();
      }, null, "Count " + t + "-tier entries");
      b.dataset.tier = t; tiers.appendChild(b);
    });
    $("b-gaps").onclick = function () { st.panel = st.panel === "gaps" ? null : "gaps"; if (st.panel) st.node = null; applyState(); };
    $("b-paths").onclick = function () { st.panel = st.panel === "paths" ? null : "paths"; if (st.panel) st.node = null; applyState(); };
    $("b-bridges").onclick = function () { st.bridges = !st.bridges; applyState(); };
    $("b-particles").onclick = function () { st.particles = !st.particles; applyState(); };
    $("b-reset").onclick = function () {
      st.lanes.clear(); st.tiers = new Set(TIERS); st.node = null; st.path = null; st.panel = null;
      st.collapsed.clear(); st.bridges = false; st.particles = !reduceMotion; $("flow-q").value = "";
      layout(true); applyState();
    };
    $("fp-close").onclick = function () { st.node = null; st.panel = null; st.path = null; applyState(); };
    var lg = $("flow-legend");
    D.zones.forEach(function (z, i) { lg.appendChild(el("span", null, [el("i", { style: "background:" + ZONE_COLOR[i] }), z])); });
    lg.appendChild(el("span", null, [el("i", { style: "background:none;border:1px solid #fff" }), "solid outline = indexed hub"]));
    lg.appendChild(el("span", null, [el("i", { style: "background:none;border:1px dashed #fff" }), "dashed = noindex hub / unposted kit"]));
    lg.appendChild(el("span", null, ["click a band title to collapse a zone"]));
    buildSearch();
  }
  function toggle(set, v) { if (set.has(v)) set.delete(v); else set.add(v); }

  function buildSearch() {
    var q = $("flow-q"), ul = $("flow-sugg"), act = 0, hits = [];
    function close() { ul.hidden = true; q.setAttribute("aria-expanded", "false"); }
    function render() {
      ul.textContent = "";
      hits.forEach(function (n, i) {
        var li = el("li", { role: "option", class: i === act ? "act" : "", "aria-selected": i === act ? "true" : "false" },
          [el("span", null, shortLabel(n, 44)), el("small", null, (KIND_LABEL[n.kind] || n.kind) + " · " + n.count)]);
        li.addEventListener("mousedown", function (ev) { ev.preventDefault(); pick(n); });
        ul.appendChild(li);
      });
      ul.hidden = !hits.length; q.setAttribute("aria-expanded", hits.length ? "true" : "false");
    }
    function pick(n) { q.value = n.label; close(); select(n.id, true); }
    q.addEventListener("input", function () {
      var s = q.value.trim().toLowerCase(); act = 0;
      if (!s) { hits = []; render(); return; }
      var pre = [], mid = [];
      nodes.forEach(function (n) {
        var l = n.label.toLowerCase().replace(/^@/, ""), i = l.indexOf(s.replace(/^@/, ""));
        if (i === 0) pre.push(n); else if (i > 0) mid.push(n);
      });
      var by = function (a, b) { return b.count - a.count || (a.label < b.label ? -1 : 1); };
      hits = pre.sort(by).concat(mid.sort(by)).slice(0, 8); render();
    });
    q.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowDown") { act = Math.min(hits.length - 1, act + 1); render(); ev.preventDefault(); }
      else if (ev.key === "ArrowUp") { act = Math.max(0, act - 1); render(); ev.preventDefault(); }
      else if (ev.key === "Enter" && hits[act]) { pick(hits[act]); ev.preventDefault(); }
      else if (ev.key === "Escape") close();
    });
    q.addEventListener("blur", function () { setTimeout(close, 120); });
  }

  /* ---- 5. scene & layout ------------------------------------------------- */
  function buildScene() {
    svg = d3.select("#flow-svg");
    gRoot = svg.append("g");
    gBands = gRoot.append("g");
    gEdges = gRoot.append("g");
    gRoute = gRoot.append("g");
    gNodes = gRoot.append("g");
    canvas = $("flow-canvas"); ctx = canvas.getContext("2d");

    edgeSel = gEdges.selectAll("path").data(edges).join("path")
      .attr("class", function (e) { return "edge" + (e.bridge ? " bridge" : ""); })
      .attr("stroke", function (e) { return ZONE_COLOR[e.s.zone]; });
    nodeSel = gNodes.selectAll("g").data(nodes).join("g").attr("class", "node")
      .on("click", function (ev, n) { ev.stopPropagation(); select(st.node === n.id ? null : n.id, false); })
      .on("mousemove", function (ev, n) { tip(ev, n); })
      .on("mouseleave", function () { $("flow-tip").hidden = true; });
    nodeSel.append("rect")
      .attr("fill", function (n) { return ZONE_COLOR[n.zone]; })
      .attr("fill-opacity", function (n) { return n.kind === "kit" && n.status !== "posted" ? 0.45 : 0.85; })
      .attr("stroke", function (n) { return n.hub || n.kind === "kit" ? "#fff" : "none"; })
      .attr("stroke-opacity", function (n) { return n.hub || n.kind === "kit" ? 0.7 : 0; })
      .attr("stroke-dasharray", function (n) {
        return (n.hub && !n.indexed) || (n.kind === "kit" && n.status !== "posted") ? "2 2" : null; });
    nodeSel.append("text");
    svg.on("click", function () { if (st.node || st.path) { st.node = null; st.path = null; if (st.panel === "node") st.panel = null; applyState(); } });
  }

  function order() {
    // zone-by-zone barycenter ordering (deterministic: ties break on count then id)
    var pos = new Map(), cols = [[], [], [], [], [], []];
    nodes.forEach(function (n) { cols[n.zone].push(n); });
    function bary(n, z) {
      var s = 0, w = 0;
      inE.get(n.id).forEach(function (e) { if (pos.has(e.source) && !e.bridge) { s += pos.get(e.source) * e.weight; w += e.weight; } });
      if (!w) inE.get(n.id).forEach(function (e) { if (pos.has(e.source)) { s += pos.get(e.source) * e.weight; w += e.weight; } });
      return w ? s / w : 1e9;
    }
    var pillarRank = {}; D.pillars.forEach(function (p, i) { pillarRank["pillar:" + p.key] = i; });
    cols[1].sort(function (a, b) { return pillarRank[a.id] - pillarRank[b.id]; });
    cols[1].forEach(function (n, i) { pos.set(n.id, i); });
    // sources ordered by barycenter of their pillar targets (outgoing)
    function baryOut(n) {
      var s = 0, w = 0;
      outE.get(n.id).forEach(function (e) { if (pos.has(e.target)) { s += pos.get(e.target) * e.weight; w += e.weight; } });
      return w ? s / w : 1e9;
    }
    var b0 = new Map(); cols[0].forEach(function (n) { b0.set(n.id, baryOut(n)); });
    cols[0].sort(function (a, b) { return SRC_BLOCK[a.kind] - SRC_BLOCK[b.kind] || b0.get(a.id) - b0.get(b.id) || b.count - a.count || (a.id < b.id ? -1 : 1); });
    for (var z = 2; z <= 5; z++) {
      var bz = new Map(), zz = z;
      cols[z].forEach(function (n) { bz.set(n.id, bary(n, zz)); });
      cols[z].sort(function (a, b) {
        if (zz === 5 && OUT_BLOCK[a.kind] !== OUT_BLOCK[b.kind]) return OUT_BLOCK[a.kind] - OUT_BLOCK[b.kind];
        return bz.get(a.id) - bz.get(b.id) || b.count - a.count || (a.id < b.id ? -1 : 1);
      });
      cols[z].forEach(function (n, i) { pos.set(n.id, i); });
    }
    return cols;
  }

  function layout(fit) {
    var stage = $("flow-stage"), inner = $("flow-inner");
    mobile = window.innerWidth <= MOBILE_W;
    W = inner.clientWidth || stage.clientWidth; H = stage.clientHeight;
    dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    var cols = order();
    var tallest = Math.max.apply(null, cols.map(function (c) { return c.length; }));
    var WH = Math.max(H, mobile ? H : Math.min(1500, tallest * 4.6 + PAD_T + PAD_B));   // world height
    var fitK = Math.min(1, H / WH);
    // world width: fill the stage after the fit scale, minus the side panel when it is docked open
    var WW = (W - (panelOpen && !mobile ? 384 : 0)) / fitK;
    var vis = [0, 1, 2, 3, 4, 5].filter(function (z) { return !st.collapsed.has(z); });
    var labelRoom = mobile ? 150 : 190, left = 16, stub = 26;   // collapsed zones keep a stub so their title stays clickable
    var span = (WW - left - labelRoom - BAR_W - stub * st.collapsed.size) / Math.max(1, vis.length - 1);
    xOf = []; var x = left;
    for (var z = 0; z < 6; z++) { xOf[z] = x; x += st.collapsed.has(z) ? stub : span; }
    cols.forEach(function (col, z) {
      var avail = WH - PAD_T - PAD_B - GAP * Math.max(0, col.length - 1);
      var sum = col.reduce(function (a, n) { return a + Math.sqrt(n.count || 1); }, 0);
      var free = Math.max(0, avail - col.length * MIN_H), y = PAD_T;
      col.forEach(function (n) {
        n.h = MIN_H + free * Math.sqrt(n.count || 1) / (sum || 1);
        n.x = xOf[z]; n.y = y; y += n.h + GAP;
      });
    });
    // ports: stack edge ends down each bar in neighbour order
    nodes.forEach(function (n) {
      var o = outE.get(n.id).slice().sort(function (a, b) { return a.t.y - b.t.y; });
      o.forEach(function (e, k) { e.y0 = n.y + n.h * (k + 0.5) / o.length; });
      var i = inE.get(n.id).slice().sort(function (a, b) { return a.s.y - b.s.y; });
      i.forEach(function (e, k) { e.y1 = n.y + n.h * (k + 0.5) / i.length; });
    });
    var maxW = d3.max(edges, function (e) { return e.weight; }) || 1;
    edges.forEach(function (e) {
      e.x0 = e.s.x + BAR_W; e.x1 = e.t.x;
      e.cx = (e.x0 + e.x1) / 2;
      e.w = Math.max(0.6, Math.min(9, 0.6 + 8.4 * Math.sqrt(e.weight / maxW)));
      e.len = Math.abs(e.x1 - e.x0) * 1.08 + Math.abs(e.y1 - e.y0) * 0.5;
    });
    edgeSel.attr("d", edgePath).attr("stroke-width", function (e) { return e.w; });
    nodeSel.attr("transform", function (n) { return "translate(" + n.x + "," + n.y + ")"; });
    nodeSel.select("rect").attr("width", BAR_W).attr("height", function (n) { return Math.max(1, n.h); });
    nodeSel.select("text").attr("x", BAR_W + 4).attr("y", function (n) { return n.h / 2 + 3.5; })
      .text(function (n) { return shortLabel(n, n.zone === 5 ? 30 : 26); });
    // bands
    var bands = [0, 1, 2, 3, 4, 5].map(function (z) {
      var x0 = z === 0 ? 0 : (xOf[z - 1] + BAR_W + xOf[z]) / 2 - 2, x1 = z === 5 ? WW : (xOf[z] + BAR_W + xOf[z + 1]) / 2 - 2;
      return { z: z, x0: Math.min(x0, xOf[z] - 4), x1: Math.max(x1, xOf[z] + BAR_W + 4) };
    });
    gBands.selectAll("rect").data(bands).join("rect")
      .attr("class", function (b) { return "band" + (b.z % 2 ? " odd" : ""); })
      .attr("x", function (b) { return b.x0; }).attr("y", 0)
      .attr("width", function (b) { return Math.max(0, b.x1 - b.x0); }).attr("height", WH);
    gBands.selectAll("text").data(bands).join("text")
      .attr("class", "band-h").attr("x", function (b) { return xOf[b.z]; }).attr("y", 22)
      .attr("fill", function (b) { return ZONE_COLOR[b.z]; })
      .attr("role", "button").attr("tabindex", 0)
      .text(function (b) {
        var n = (D.zone_counts[b.z] || {}).nodes || 0;
        return st.collapsed.has(b.z) ? "▸" : ["Sources", "Pillars", "Tools", "Techniques", "Guides", "Outputs"][b.z] + " · " + n;
      })
      .on("click", function (ev, b) { ev.stopPropagation(); toggle(st.collapsed, b.z); layout(false); applyState(); })
      .on("keydown", function (ev, b) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); toggle(st.collapsed, b.z); layout(false); applyState(); } })
      .each(function (b) { this.setAttribute("aria-label", (st.collapsed.has(b.z) ? "Expand " : "Collapse ") + D.zones[b.z]); });
    // zoom
    if (!mobile) {
      if (!zoom) {
        zoom = d3.zoom().scaleExtent([0.3, 8]).on("zoom", function (ev) { curT = ev.transform; gRoot.attr("transform", curT); labels(); drawStatic(); });
        svg.call(zoom).on("dblclick.zoom", null);
      }
      if (fit) svg.call(zoom.transform, d3.zoomIdentity.scale(fitK));
      else gRoot.attr("transform", curT);
    } else {
      if (zoom) { svg.on(".zoom", null); zoom = null; }
      curT = d3.zoomIdentity.scale(H / WH); gRoot.attr("transform", curT);
    }
    labels();
  }

  function edgePath(e) { return "M" + e.x0 + "," + e.y0 + "C" + e.cx + "," + e.y0 + " " + e.cx + "," + e.y1 + " " + e.x1 + "," + e.y1; }
  function shortLabel(n, max) {
    var l = n.label.replace(/^(Prompt system|Content kit|Tool hub|Compare|Best of) · /, function (m, p) {
      return { "Prompt system": "❯ ", "Content kit": "▣ ", "Tool hub": "⌂ ", Compare: "⇄ ", "Best of": "★ " }[p]; });
    return l.length > max ? l.slice(0, max - 1) + "…" : l;
  }
  function labels() {
    var k = curT.k;
    nodeSel.select("text").style("display", function (n) {
      var h = n.h * k;
      if (n._focus) return null;
      if (n._hi) return h >= 4 ? null : "none";
      return (n.zone < 4 && h >= 7) || h >= 10 ? null : "none";
    });
  }

  /* ---- 6. state -> visuals ---------------------------------------------- */
  function nodeTierCount(n) { var s = 0; TIERS.forEach(function (t) { if (st.tiers.has(t)) s += n.tier_mix[t] || 0; }); return s; }
  function edgeTierW(e) { var s = 0; TIERS.forEach(function (t, i) { if (st.tiers.has(t)) s += e.tiers[i] || 0; }); return s; }
  function nodeLane(n) { if (!st.lanes.size) return true; for (var l of st.lanes) if (n.lanes[l]) return true; return false; }
  function edgeLane(e) { if (!st.lanes.size) return true; for (var l of st.lanes) if (e.lanes[laneIdx[l]]) return true; return false; }
  function edgeShown(e) {
    if (st.collapsed.has(e.s.zone) || st.collapsed.has(e.t.zone)) return false;
    if (e.bridge) return st.bridges || BRIDGE[e.kind].some(function (z) { return st.collapsed.has(z); });
    return true;
  }
  var allTiers = function () { return st.tiers.size === 4; };

  function applyState() {
    var wantPanel = !!((st.panel && (st.panel !== "node" || byId.has(st.node))) || (st.path != null && D.paths[st.path]));
    if (wantPanel !== panelOpen) { panelOpen = wantPanel; if (!mobile) layout(false); }
    var focus = null, route = null;
    if (st.path != null && D.paths[st.path]) {
      route = D.paths[st.path];
      focus = new Set(route.nodes);
    } else if (st.node && byId.has(st.node)) {
      focus = new Set([st.node]);
      outE.get(st.node).forEach(function (e) { if (edgeShown(e)) focus.add(e.target); });
      inE.get(st.node).forEach(function (e) { if (edgeShown(e)) focus.add(e.source); });
    }
    var routePairs = new Set();
    if (route) for (var i = 0; i + 1 < route.nodes.length; i++) routePairs.add(route.nodes[i] + ">" + route.nodes[i + 1]);
    var filtering = st.lanes.size || !allTiers();
    nodes.forEach(function (n) {
      n._on = !st.collapsed.has(n.zone) && nodeTierCount(n) > 0 && nodeLane(n);
      n._focus = !!(focus && focus.has(n.id));
      n._hi = n._focus || (st.lanes.size > 0 && n._on && !focus);
      n._dim = !n._on || (focus && !focus.has(n.id));
    });
    edges.forEach(function (e) {
      e._shown = edgeShown(e);
      e._on = e._shown && edgeTierW(e) > 0 && edgeLane(e) && e.s._on && e.t._on;
      if (route) e._hi = routePairs.has(e.key);
      else if (st.node) e._hi = e._on && (e.source === st.node || e.target === st.node);
      else e._hi = filtering && e._on && st.lanes.size > 0;
      e._dim = !e._on || ((route || st.node) && !e._hi);
    });
    nodeSel.style("display", function (n) { return st.collapsed.has(n.zone) ? "none" : null; })
      .classed("dim", function (n) { return n._dim; })
      .classed("hi", function (n) { return n._hi; })
      .classed("sel", function (n) { return n.id === st.node || (route && route.nodes.indexOf(n.id) >= 0); });
    edgeSel.style("display", function (e) { return e._shown ? null : "none"; })
      .classed("dim", function (e) { return e._dim; })
      .classed("hi", function (e) { return e._hi; })
      .attr("stroke-width", function (e) { return allTiers() ? e.w : Math.max(0.6, e.w * Math.sqrt(edgeTierW(e) / e.weight)); });
    // route overlay: draws the path even where a hop was below the edge threshold
    var segs = [];
    if (route) for (var j = 0; j + 1 < route.nodes.length; j++) {
      var a = byId.get(route.nodes[j]), b = byId.get(route.nodes[j + 1]);
      if (a && b && !st.collapsed.has(a.zone) && !st.collapsed.has(b.zone)) segs.push({ a: a, b: b });
    }
    gRoute.selectAll("path").data(segs).join("path").attr("class", "route").attr("d", function (s) {
      var x0 = s.a.x + BAR_W, y0 = s.a.y + s.a.h / 2, x1 = s.b.x, y1 = s.b.y + s.b.h / 2, cx = (x0 + x1) / 2;
      return "M" + x0 + "," + y0 + "C" + cx + "," + y0 + " " + cx + "," + y1 + " " + x1 + "," + y1;
    });
    labels();
    // controls
    document.querySelectorAll("#flow-lanes .fbtn").forEach(function (b) { var on = st.lanes.has(b.dataset.lane); b.classList.toggle("on", on); b.setAttribute("aria-pressed", on ? "true" : "false"); });
    document.querySelectorAll("#flow-tiers .fbtn").forEach(function (b) { b.classList.toggle("on", st.tiers.has(b.dataset.tier)); });
    $("b-gaps").classList.toggle("on", st.panel === "gaps");
    $("b-paths").classList.toggle("on", st.panel === "paths");
    $("b-bridges").classList.toggle("on", st.bridges);
    $("b-particles").classList.toggle("on", st.particles);
    renderPanel();
    rebuildParticles();
    writeHash();
    if (particlesWanted()) startParticles(); else stopParticles();
  }

  function select(id, center) {
    st.node = id; st.path = null; st.panel = id ? "node" : (st.panel === "node" ? null : st.panel);
    applyState();
    if (id && center) centerOn(byId.get(id));
  }
  function centerOn(n) {
    if (!n) return;
    if (mobile) { var sc = $("flow-scroll"); sc.scrollLeft = Math.max(0, n.x * curT.k - sc.clientWidth / 2); return; }
    var k = Math.max(curT.k, 1.25);
    svg.transition().duration(450).call(zoom.transform, d3.zoomIdentity.translate(W / 2 - (n.x + BAR_W / 2) * k - (W > 900 ? 160 : 0), H / 2 - (n.y + n.h / 2) * k).scale(k));
  }

  /* ---- 7. tooltip & panel ------------------------------------------------ */
  function tip(ev, n) {
    var t = $("flow-tip"); t.textContent = "";
    t.appendChild(el("b", null, n.label));
    t.appendChild(document.createTextNode((KIND_LABEL[n.kind] || n.kind) + " · " + n.count + " entries · S" + n.tier_mix.S + " A" + n.tier_mix.A + " B" + n.tier_mix.B + " C" + n.tier_mix.C));
    var ls = Object.keys(n.lanes);
    if (ls.length) t.appendChild(el("div", null, "lanes: " + ls.map(function (l) { return (LANE_LABEL[l] || l) + " " + n.lanes[l]; }).join(", ")));
    t.hidden = false;
    var x = ev.clientX + 14, y = ev.clientY + 12;
    if (x + 310 > window.innerWidth) x = ev.clientX - 310;
    t.style.left = x + "px"; t.style.top = y + "px";
  }

  function a(href, text) { return el("a", { href: href, target: /^https?:/.test(href) ? "_blank" : null, rel: /^https?:/.test(href) ? "noopener" : null }, text); }
  function section(body, title) { body.appendChild(el("h3", null, title)); }

  function renderPanel() {
    var p = $("flow-panel"), body = $("fp-body");
    if (!st.panel || (st.panel === "node" && !byId.has(st.node))) {
      if (st.path != null && D.paths[st.path]) st.panel = "paths"; else { p.hidden = true; return; }
    }
    p.hidden = false; body.textContent = "";
    if (st.panel === "gaps") return panelGaps(body);
    if (st.panel === "paths") return panelPaths(body);
    panelNode(body, byId.get(st.node));
  }

  function panelNode(body, n) {
    $("fp-kind").textContent = (KIND_LABEL[n.kind] || n.kind) + " · " + D.zones[n.zone];
    $("fp-label").textContent = n.label;
    var mix = el("div", { class: "chips" }, TIERS.map(function (t) { return el("span", { class: "chip" }, [el("span", { class: "tp " + t }, t), String(n.tier_mix[t] || 0)]); }));
    body.appendChild(el("p", { style: "margin:4px 0 6px" }, [el("strong", null, String(n.count)), " entries" + (n.folded ? " from " + n.folded + " creators with fewer than 4 saves each" : "")]));
    body.appendChild(mix);
    var ls = Object.keys(n.lanes);
    if (ls.length) {
      section(body, "Lanes");
      body.appendChild(el("div", { class: "chips" }, ls.map(function (l) {
        return el("span", { class: "chip link", title: "Filter to this lane", onclick: function () { st.lanes = new Set([l]); applyState(); } },
          [el("span", { class: "sw", style: "background:" + LANE_COLOR[l] }), (LANE_LABEL[l] || l) + " " + n.lanes[l]]);
      })));
    }
    var links = [];
    var openLbl = { collection: "Collection page", creator: "Creator on Instagram", pillar: "Top guide for this pillar",
      tool: "Tool hub", repo: "Repo on GitHub", guide: "Guide", "prompt-system": "Prompt system", kit: "Guide (kit source)",
      hub: "Tool hub", compare: "Comparison", best: "Best-of page", "system-prompts": "System prompts page", "collection-pages": "All collections" }[n.kind] || "Open";
    if (n.url) links.push(el("li", null, a(n.url, openLbl + (n.kind === "tool" || n.kind === "hub" ? (n.indexed ? " (indexed)" : " (noindex)") : ""))));
    if (n.deeper) links.push(el("li", null, a(n.deeper, "Deeper dive")));
    if (n.kind === "guide") {
      links.push(el("li", null, n.prompt_system ? a(n.url + "#prompt-system", "Prompt system") : el("span", { class: "chip" }, "no prompt system yet")));
      links.push(el("li", null, el("span", { class: "chip" }, "Content kit: " + (n.kit || "none"))));
    }
    if (n.kind === "kit") links.push(el("li", null, el("span", { class: "chip" }, "Status: " + (n.status || "?"))));
    if (n.affiliate) links.push(el("li", null, el("span", { class: "chip" }, "Affiliate program" + (n.affiliate_status ? ": " + n.affiliate_status : ""))));
    if (n.kind === "tool" && !n.hub) links.push(el("li", null, el("span", { class: "chip" }, "no /tools/ hub yet")));
    links.push(el("li", null, a("/search?q=" + encodeURIComponent(n.label.replace(/^@/, "").replace(/^(Prompt system|Content kit|Tool hub|Compare|Best of) · /, "")), "Find in archive search")));
    links.push(el("li", null, a("/catalog", "Open the catalog")));
    section(body, "Links"); body.appendChild(el("ul", null, links));
    function conn(list, dirKey, title) {
      var rows = list.filter(function (e) { return e._shown; }).sort(function (x, y) { return y.weight - x.weight; }).slice(0, 8);
      if (!rows.length) return;
      section(body, title + " (" + list.length + ")");
      body.appendChild(el("div", { class: "chips" }, rows.map(function (e) {
        var o = e[dirKey];
        return el("span", { class: "chip link", title: o.label, onclick: function () { select(o.id, true); } }, shortLabel(o, 28) + " · " + e.weight);
      })));
    }
    conn(inE.get(n.id), "s", "Flows in from");
    conn(outE.get(n.id), "t", "Flows out to");
    var gs = D.gaps.filter(function (g) { return g.node === n.id; });
    if (gs.length) { section(body, "Gaps"); gs.forEach(function (g) { body.appendChild(gapItem(g, false)); }); }
    var ents = (n.entries || []).filter(function (id) { var e = D.entries[id]; return e && st.tiers.has(e.tier); }).slice(0, 12);
    if (ents.length) {
      section(body, "Top entries");
      body.appendChild(el("ul", null, ents.map(function (id) {
        var e = D.entries[id];
        return el("li", null, [el("span", { class: "tp " + e.tier }, e.tier), a(e.u, e.t)]);
      })));
    }
  }

  function gapItem(g, clickable) {
    var kids = [el("div", { class: "k" }, g.kind.replace(/-/g, " ")), el("strong", null, g.label),
      el("div", { class: "m" }, g.metric), el("div", { class: "s" }, g.suggestion)];
    if (g.links && g.links.length) kids.push(el("ul", { style: "margin-top:4px" }, g.links.map(function (l) { return el("li", null, a(l.url, l.label)); })));
    var it = el("div", { class: "gap-item" + (clickable && g.node && byId.has(g.node) ? " click" : "") }, kids);
    if (clickable && g.node && byId.has(g.node)) it.addEventListener("click", function (ev) { if (ev.target.tagName !== "A") select(g.node, true); });
    return it;
  }
  function panelGaps(body) {
    $("fp-kind").textContent = "Gap analysis"; $("fp-label").textContent = D.gaps.length + " gaps, biggest first";
    body.appendChild(el("p", { class: "s", style: "color:var(--text-mute);margin:2px 0 10px" }, "Where the archive has material but no guide, hub or kit yet. Click a gap to find it on the map. Data: /flow_gaps.json"));
    D.gaps.forEach(function (g) { body.appendChild(gapItem(g, true)); });
  }
  function panelPaths(body) {
    $("fp-kind").textContent = "Top paths"; $("fp-label").textContent = "Strongest routes, creator to prompt system";
    body.appendChild(el("p", { style: "color:var(--text-mute);margin:2px 0 10px;font-size:12px" }, "Ranked by the product of link weights along the route; each route is walked end to end by at least one entry. Click to light it up."));
    D.paths.forEach(function (p, i) {
      var it = el("div", { class: "path-item" + (st.path === i ? " on" : "") }, [
        el("strong", null, "#" + p.rank + " · " + p.through + " entr" + (p.through === 1 ? "y" : "ies") + " end to end"),
        el("ol", null, p.labels.map(function (l) { return el("li", null, l); })),
        el("div", { class: "w" }, "link weights " + p.weights.join(" × ") + " = " + p.weight_product.toLocaleString())]);
      it.addEventListener("click", function () { st.path = st.path === i ? null : i; st.node = null; st.panel = "paths"; applyState(); });
      body.appendChild(it);
    });
  }

  /* ---- 8. hash ----------------------------------------------------------- */
  var writingHash = false;
  function writeHash() {
    var p = [];
    if (st.lanes.size) p.push("lane=" + Array.from(st.lanes).join(","));
    if (!allTiers()) p.push("tier=" + TIERS.filter(function (t) { return st.tiers.has(t); }).join(","));
    if (st.node) p.push("node=" + encodeURIComponent(st.node).replace(/%3A/g, ":"));
    if (st.path != null) p.push("path=" + (st.path + 1));
    if (st.panel === "gaps" || st.panel === "paths") p.push("panel=" + st.panel);
    if (st.collapsed.size) p.push("collapse=" + Array.from(st.collapsed).sort().join(","));
    if (st.bridges) p.push("bridges=1");
    if (st.particles === reduceMotion) p.push("particles=" + (st.particles ? 1 : 0));
    var h = p.length ? "#" + p.join("&") : "";
    if (h !== location.hash && !(h === "" && !location.hash)) {
      writingHash = true;
      history.replaceState(null, "", location.pathname + location.search + h);
      setTimeout(function () { writingHash = false; }, 0);
    }
  }
  function readHash() {
    var q = {};
    location.hash.replace(/^#/, "").split("&").forEach(function (kv) { var i = kv.indexOf("="); if (i > 0) q[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1)); });
    st.lanes = new Set((q.lane || "").split(",").filter(function (l) { return laneIdx[l] != null; }));
    var t = (q.tier || "").split(",").filter(function (x) { return TIERS.indexOf(x) >= 0; });
    st.tiers = new Set(t.length ? t : TIERS);
    st.node = q.node && byId.has(q.node) ? q.node : null;
    var pi = parseInt(q.path, 10);
    st.path = pi >= 1 && pi <= D.paths.length ? pi - 1 : null;
    st.panel = q.panel === "gaps" || q.panel === "paths" ? q.panel : (st.node ? "node" : (st.path != null ? "paths" : null));
    st.collapsed = new Set((q.collapse || "").split(",").map(Number).filter(function (z) { return z >= 0 && z <= 5 && String(z) !== "NaN"; }));
    if (q.collapse === undefined || q.collapse === "") st.collapsed.clear();
    st.bridges = q.bridges === "1";
    st.particles = q.particles != null ? q.particles === "1" : !reduceMotion;
  }

  /* ---- 9. particle flow layer (ported from Atlas section 11) ------------- */
  var pStart = 0, pRaf = null, pRunning = false, plist = [], pPoint = { x: 0, y: 0 };
  function phaseOf(key) {   // deterministic [0,1) phase per edge — djb2, same shape as Atlas/engine_ports
    var h = 5381;
    for (var i = 0; i < key.length; i++) h = ((h * 33) ^ key.charCodeAt(i)) >>> 0;
    return (h % 1000) / 1000;
  }
  function brighten(hex, amt) {
    var v = parseInt(hex.slice(1), 16), r = (v >> 16) & 255, g = (v >> 8) & 255, b = v & 255;
    return "rgb(" + Math.round(r + (255 - r) * amt) + "," + Math.round(g + (255 - g) * amt) + "," + Math.round(b + (255 - b) * amt) + ")";
  }
  var PCOL = ZONE_COLOR.map(function (c) { return brighten(c, 0.38); });
  function rebuildParticles() {
    plist = [];
    var maxW = d3.max(edges, function (e) { return e.weight; }) || 1, total = 0;
    edges.forEach(function (e) {
      if (!e._shown || !e._on) return;
      var w = allTiers() ? e.weight : edgeTierW(e);
      if (w <= 0) return;
      var norm = Math.log(1 + w) / Math.log(1 + maxW);
      var faint = w <= 1;
      var count = faint ? 1 : Math.min(6, 1 + Math.floor(Math.log2(w)));
      var pxs = faint ? 9 : 16 + 46 * norm;                      // screen-ish px per second, ∝ weight
      var alpha = faint ? 0.28 : 0.85;
      if ((st.node || st.path != null) && !e._hi) alpha = 0.08;
      plist.push({ e: e, count: count, speed: pxs / Math.max(40, e.len), alpha: alpha, phase: phaseOf(e.key), col: PCOL[e.s.zone] });
      total += count;
    });
    if (total > PARTICLE_CAP) {
      var f = PARTICLE_CAP / total;
      plist.forEach(function (p) { p.count = Math.max(1, Math.floor(p.count * f)); });
    }
  }
  function particlesWanted() { return st.particles && !document.hidden && plist.length > 0; }
  function startParticles() { if (pRunning) return; pRunning = true; pStart = performance.now(); pRaf = requestAnimationFrame(tick); }
  function stopParticles() { pRunning = false; if (pRaf) cancelAnimationFrame(pRaf); pRaf = null; clearFlow(); }
  function clearFlow() { ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H); }
  function tick(now) { if (!pRunning) return; pRaf = requestAnimationFrame(tick); drawParticles((now - pStart) / 1000); }
  function drawStatic() { if (!pRunning && st.particles) clearFlow(); }
  function cubicPoint(e, u, out) {
    var m = 1 - u, a = m * m * m, b = 3 * m * m * u, c = 3 * m * u * u, d = u * u * u;
    out.x = a * e.x0 + b * e.cx + c * e.cx + d * e.x1;
    out.y = a * e.y0 + b * e.y0 + c * e.y1 + d * e.y1;
  }
  function drawParticles(t) {
    var k = curT.k;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    ctx.setTransform(dpr * k, 0, 0, dpr * k, dpr * curT.x, dpr * curT.y);
    ctx.globalCompositeOperation = "lighter";
    var r = PARTICLE_R / Math.max(0.5, k);
    for (var i = 0; i < plist.length; i++) {
      var p = plist[i], e = p.e, base = p.phase + t * p.speed;
      ctx.fillStyle = p.col; ctx.globalAlpha = p.alpha;
      ctx.beginPath();
      for (var j = 0; j < p.count; j++) {
        cubicPoint(e, (base + j / p.count) % 1, pPoint);
        ctx.moveTo(pPoint.x + r, pPoint.y);
        ctx.arc(pPoint.x, pPoint.y, r, 0, 6.283185307179586);
      }
      ctx.fill();
    }
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
  }
})();
