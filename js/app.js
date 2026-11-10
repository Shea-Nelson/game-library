/* Shea's Game Shelf — vanilla JS, no build step */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const slug = (s) => String(s).toLowerCase().normalize("NFKD").replace(/[^\w\s-]/g, "").trim().replace(/[\s_]+/g, "-").replace(/-+/g, "-");
  const HUES = [262, 285, 172, 328, 222];
  const hue = (id) => HUES[id % HUES.length];

  const ICON = {
    users: '<svg aria-hidden="true" viewBox="0 0 24 24" width="15" height="15"><circle cx="9" cy="8" r="3.2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M16 4.5a3.2 3.2 0 010 6.3M18 14.3c1.8.9 3 2.9 3 5.7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    clock: '<svg aria-hidden="true" viewBox="0 0 24 24" width="15" height="15"><circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7.5V12l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    weight: '<svg aria-hidden="true" viewBox="0 0 24 24" width="15" height="15"><path d="M6 9h12l2 11H4L6 9z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="12" cy="6" r="2.5" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    age: '<svg aria-hidden="true" viewBox="0 0 24 24" width="15" height="15"><circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    play: '<svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>',
    scroll: '<svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14"><path d="M7 4h10v14a2 2 0 01-2 2H6a2 2 0 01-2-2v-2h3V4zM10 8h4M10 12h4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    close: '<svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>',
    bigplay: '<svg aria-hidden="true" viewBox="0 0 24 24" width="30" height="30"><path d="M8 5v14l11-7z" fill="#c4302b"/></svg>',
  };

  const state = { q: "", players: null, time: null, weight: null, cat: "", mech: "", best: false, house: false, video: false, exp: false, sort: "name", dir: "asc" };
  let GAMES = [], META = null, byId = new Map(), lastFocus = null;

  const TIME = [
    { k: "15", label: "≤ 15 min", test: (g) => (g.maxPlayTime || g.minPlayTime || 999) <= 15 },
    { k: "30", label: "≤ 30 min", test: (g) => (g.maxPlayTime || g.minPlayTime || 999) <= 30 },
    { k: "60", label: "≤ 60 min", test: (g) => (g.maxPlayTime || g.minPlayTime || 999) <= 60 },
    { k: "long", label: "Over an hour", test: (g) => (g.maxPlayTime || 0) > 60 },
  ];
  const WEIGHT = [
    { k: "light", label: "Light (< 1.8)", test: (g) => g.weight != null && g.weight < 1.8 },
    { k: "medium", label: "Medium (1.8–2.6)", test: (g) => g.weight != null && g.weight >= 1.8 && g.weight < 2.6 },
    { k: "heavy", label: "Meatier (2.6+)", test: (g) => g.weight != null && g.weight >= 2.6 },
  ];
  const PLAYERS = [1, 2, 3, 4, 5, 6, 7, 8, 10];

  const maxP = (g) => g.maxPlayersWithExpansions || g.maxPlayers || 0;
  const playersText = (g) => {
    const a = g.minPlayers, b = maxP(g);
    if (!a && !b) return "?";
    if (b >= 99) return `${a}+`;
    return a === b ? `${a}` : `${a}–${b}`;
  };
  const timeText = (g) => {
    const a = g.minPlayTime, b = g.maxPlayTime;
    if (!a && !b) return null;
    return a && b && a !== b ? `${a}–${b} min` : `${a || b} min`;
  };
  const parseCounts = (s) => {
    const out = new Set();
    String(s || "").split(",").forEach((p) => {
      const m = p.trim().match(/^(\d+)(?:-(\d+))?/);
      if (!m) return;
      const a = +m[1], b = m[2] ? +m[2] : a;
      for (let i = a; i <= b && i < 200; i++) out.add(i);
    });
    return out;
  };
  const playsWith = (g, n) => {
    if (n === 10) return maxP(g) >= 10;
    return (g.minPlayers || 1) <= n && maxP(g) >= n;
  };
  const bestAt = (g, n) => {
    const s = g._best; if (!s.size) return false;
    if (n === 10) return [...s].some((x) => x >= 10);
    return s.has(n);
  };

  /* ---------- data ---------- */
  async function load() {
    try {
      const r = await fetch("data/games.json", { cache: "no-cache" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      GAMES = await r.json();
    } catch (e) {
      // Fallback for file:// or offline: inline copy
      try {
        await new Promise((res, rej) => { const s = document.createElement("script"); s.src = "js/games-data.js"; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
        GAMES = window.GAMES_DATA || [];
        META = window.GAMES_META || null;
      } catch (e2) {
        const el = $("#loadError"); el.hidden = false;
        el.textContent = "Sorry, the game list couldn't load. Try refreshing the page.";
        return;
      }
    }
    if (!META) { try { const r = await fetch("data/coverage.json", { cache: "no-cache" }); if (r.ok) META = await r.json(); } catch (e) { /* optional */ } }
    GAMES.forEach((g) => {
      g._slug = `${g.bggId}-${slug(g.name)}`;
      g._best = parseCounts(g.bestPlayers);
      g._hay = [g.name, g.bggName, g.publisher, ...(g.designers || []), ...(g.categories || []), ...(g.mechanics || []), ...(g.expansions || []).map((e) => e.name)].join(" ").toLowerCase();
      byId.set(g.bggId, g);
    });
    init();
  }

  /* ---------- controls ---------- */
  function chip(label, pressed, data) {
    return `<button type="button" class="chip" aria-pressed="${pressed}" data-v="${esc(data)}">${esc(label)}</button>`;
  }
  function renderChips() {
    $("#playerChips").innerHTML = chip("Any", state.players == null, "") + PLAYERS.map((n) => chip(n === 10 ? "10+" : String(n), state.players === n, n)).join("");
    $("#timeChips").innerHTML = chip("Any", state.time == null, "") + TIME.map((t) => chip(t.label, state.time === t.k, t.k)).join("");
    $("#weightChips").innerHTML = chip("Any", state.weight == null, "") + WEIGHT.map((t) => chip(t.label, state.weight === t.k, t.k)).join("");
  }
  function fillSelect(sel, values) {
    const counts = {};
    GAMES.forEach((g) => (g[values] || []).forEach((v) => (counts[v] = (counts[v] || 0) + 1)));
    Object.keys(counts).sort((a, b) => a.localeCompare(b)).forEach((v) => {
      const o = document.createElement("option"); o.value = v; o.textContent = `${v} (${counts[v]})`; sel.appendChild(o);
    });
  }
  function activeFilterCount() {
    return [state.time, state.weight, state.cat || null, state.mech || null, state.best || null, state.house || null, state.video || null, state.exp || null].filter((x) => x != null && x !== false).length;
  }

  function init() {
    fillSelect($("#catSel"), "categories");
    fillSelect($("#mechSel"), "mechanics");
    renderChips();
    stats();

    $("#playerChips").addEventListener("click", (e) => { const b = e.target.closest(".chip"); if (!b) return; state.players = b.dataset.v === "" ? null : +b.dataset.v; update(); });
    $("#timeChips").addEventListener("click", (e) => { const b = e.target.closest(".chip"); if (!b) return; state.time = b.dataset.v || null; update(); });
    $("#weightChips").addEventListener("click", (e) => { const b = e.target.closest(".chip"); if (!b) return; state.weight = b.dataset.v || null; update(); });
    let t; $("#q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { state.q = e.target.value.trim().toLowerCase(); update(); }, 120); });
    $("#sortBy").addEventListener("change", (e) => { state.sort = e.target.value; state.dir = ["rating", "weight", "year"].includes(state.sort) ? "desc" : "asc"; update(); });
    $("#sortDir").addEventListener("click", () => { state.dir = state.dir === "asc" ? "desc" : "asc"; update(); });
    $("#catSel").addEventListener("change", (e) => { state.cat = e.target.value; update(); });
    $("#mechSel").addEventListener("change", (e) => { state.mech = e.target.value; update(); });
    [["fBest", "best"], ["fHouse", "house"], ["fVideo", "video"], ["fExp", "exp"]].forEach(([id, k]) => $("#" + id).addEventListener("change", (e) => { state[k] = e.target.checked; update(); }));
    $("#filtersBtn").addEventListener("click", () => toggleFilters());
    $("#doneBtn").addEventListener("click", () => toggleFilters(false));
    $("#clearAll").addEventListener("click", clearAll);
    $("#emptyClear").addEventListener("click", clearAll);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#filters").hidden && document.body.classList.contains("sheet-open")) toggleFilters(false); });
    document.addEventListener("click", (e) => { if (document.body.classList.contains("sheet-open") && !e.target.closest("#filters") && !e.target.closest("#filtersBtn")) toggleFilters(false); });

    $("#grid").addEventListener("click", (e) => { const a = e.target.closest("a.card__btn"); if (!a) return; lastFocus = a; });
    window.addEventListener("hashchange", route);
    const dlg = $("#detail");
    dlg.addEventListener("close", () => { if (location.hash.startsWith("#game/")) history.pushState("", document.title, location.pathname + location.search); restoreFocus(); });
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });

    // theme
    const tt = $("#themeToggle");
    const syncTheme = () => { const dark = document.documentElement.getAttribute("data-theme") === "dark"; tt.setAttribute("aria-pressed", String(dark)); tt.querySelector(".theme-toggle__label").textContent = dark ? "Light mode" : "Dark mode"; };
    tt.addEventListener("click", () => {
      const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("gs-theme", next); } catch (e) {}
      syncTheme();
    });
    syncTheme();

    const gen = META && META.stats && META.stats.generated;
    $("#snapshot").textContent = "Data snapshot: " + (gen ? new Date(gen).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "America/New_York" }) : "November 2026") + ". Collection from BoardGameGeek user Scorpy311.";
    update();
    route();
  }

  function toggleFilters(force) {
    const panel = $("#filters"), btn = $("#filtersBtn");
    const open = force ?? panel.hidden;
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
    const mobile = matchMedia("(max-width:720px)").matches;
    document.body.classList.toggle("sheet-open", open && mobile);
    if (open) { const first = panel.querySelector(".chip, select, input"); first && first.focus({ preventScroll: true }); }
    else if (mobile) btn.focus();
  }
  function clearAll() {
    Object.assign(state, { q: "", players: null, time: null, weight: null, cat: "", mech: "", best: false, house: false, video: false, exp: false });
    $("#q").value = ""; $("#catSel").value = ""; $("#mechSel").value = "";
    ["fBest", "fHouse", "fVideo", "fExp"].forEach((id) => ($("#" + id).checked = false));
    update();
  }

  function stats() {
    const n = GAMES.length, ex = GAMES.reduce((s, g) => s + (g.expansions || []).length, 0);
    const vids = GAMES.filter((g) => g.video).length, hr = GAMES.reduce((s, g) => s + (g.houseRules || []).length, 0);
    $("#heroStats").innerHTML = [[n, "games"], [ex, "expansions"], [vids, "videos"], [hr, "house rules"]].map(([v, l]) => `<div><dt>${l}</dt><dd>${v}</dd></div>`).join("");
  }

  /* ---------- filter + sort ---------- */
  function filtered() {
    const tTest = TIME.find((t) => t.k === state.time), wTest = WEIGHT.find((w) => w.k === state.weight);
    const words = state.q.split(/\s+/).filter(Boolean);
    return GAMES.filter((g) => {
      if (words.length && !words.every((w) => g._hay.includes(w))) return false;
      if (state.players != null) { if (!playsWith(g, state.players)) return false; if (state.best && !bestAt(g, state.players)) return false; }
      else if (state.best && !g._best.size) return false;
      if (tTest && !tTest.test(g)) return false;
      if (wTest && !wTest.test(g)) return false;
      if (state.cat && !(g.categories || []).includes(state.cat)) return false;
      if (state.mech && !(g.mechanics || []).includes(state.mech)) return false;
      if (state.house && !(g.houseRules || []).length) return false;
      if (state.video && !g.video) return false;
      if (state.exp && !(g.expansions || []).length) return false;
      return true;
    });
  }
  const sortName = (g) => g.name.toLowerCase().replace(/^(the|a|an) /, "");
  const KEYS = {
    name: (g) => sortName(g), players: (g) => maxP(g) * 1000 + (g.minPlayers || 0), time: (g) => g.maxPlayTime || g.minPlayTime || null,
    weight: (g) => g.weight, rating: (g) => g.bggRating, year: (g) => g.year,
  };
  function sorted(list) {
    const k = KEYS[state.sort], d = state.dir === "asc" ? 1 : -1;
    return list.slice().sort((a, b) => {
      const x = k(a), y = k(b);
      if (x == null && y == null) return sortName(a).localeCompare(sortName(b));
      if (x == null) return 1; if (y == null) return -1;
      const c = typeof x === "string" ? x.localeCompare(y) : x - y;
      return c * d || sortName(a).localeCompare(sortName(b));
    });
  }

  /* ---------- render ---------- */
  function card(g, i) {
    const flags = (g.video ? `<span class="flag" title="Has a how-to-play video">${ICON.play}<span class="sr-only">Has video</span></span>` : "") +
      ((g.houseRules || []).length ? `<span class="flag" title="Has house rules">${ICON.scroll}<span class="sr-only">Has house rules</span></span>` : "");
    const best = g.bestPlayers ? `<span class="best">Best ${esc(g.bestPlayers)}</span>` : "";
    const t = timeText(g);
    const exp = (g.expansions || []).length ? ` · +${g.expansions.length} exp.` : "";
    return `<li class="card" style="--i:${Math.min(i, 30)};--h:${hue(g.bggId)}">
      <a class="card__btn" href="#game/${g._slug}" aria-label="${esc(g.name)}: details">
        <div class="card__art"><img src="${esc(g.image.local || g.image.remote)}" alt="Box art for ${esc(g.name)}" loading="${i < 8 ? "eager" : "lazy"}" decoding="async" width="246" height="300"
          onerror="if(this.dataset.f!=='1'){this.dataset.f='1';this.src='${esc(g.image.remote || "")}'}"></div>
        ${flags ? `<div class="card__flags">${flags}</div>` : ""}
        <div class="card__body">
          <h2 class="card__title">${esc(g.name)}</h2>
          <span class="card__year">${g.year || ""}${exp}</span>
          <div class="card__players"><span class="num">${playersText(g)}</span><span class="lbl">players</span>${best}</div>
          <div class="meta">
            ${t ? `<span>${ICON.clock}${t}</span>` : ""}
            ${g.weight ? `<span title="BGG weight (1 light – 5 heavy)">${ICON.weight}${g.weight.toFixed(1)}/5</span>` : ""}
            ${g.minAge ? `<span>${ICON.age}${g.minAge}+</span>` : ""}
          </div>
        </div>
      </a></li>`;
  }

  function update() {
    renderChips();
    $("#sortBy").value = state.sort;
    const sd = $("#sortDir"); sd.dataset.dir = state.dir; sd.setAttribute("aria-label", state.dir === "asc" ? "Sort ascending (click for descending)" : "Sort descending (click for ascending)");
    const fc = activeFilterCount(), badge = $("#filterCount");
    badge.hidden = !fc; badge.textContent = fc;
    const list = sorted(filtered());
    $("#grid").innerHTML = list.map(card).join("");
    $("#empty").hidden = list.length > 0;
    const pieces = [];
    if (state.players != null) pieces.push(`plays with ${state.players === 10 ? "10+" : state.players}${state.best ? " (best)" : ""}`);
    if (state.q) pieces.push(`matching “${esc(state.q)}”`);
    $("#resultLine").innerHTML = `<strong>${list.length}</strong> of ${GAMES.length} games${pieces.length ? " · " + pieces.join(" · ") : ""}`;
  }

  /* ---------- detail ---------- */
  const SRC = { publisher: "Publisher", bgg_file: "BGG file", bgg_files_page: "BGG files", bgg_forum: "BGG forum", web: "Guide", bgg_listed: "Publisher site" };
  function vbadge(l) { return l && l.verified === false ? ' <span class="badge badge--warn" title="We could not confirm this link automatically">Not verified</span>' : ""; }
  const isBgg = (u) => /boardgamegeek\.com\/filepage\//.test(u || "");
  function linkRow(kind, l, extra = "") {
    if (!l) return "";
    const note = l.note ? `<span class="note">${esc(l.note)}</span>` : "";
    return `<li><span class="kind">${esc(kind)}</span><a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.title || l.url)}</a>${extra}${vbadge(l)}${note}</li>`;
  }
  function videoBlock(v, name) {
    if (!v) return "";
    const id = esc(v.youtubeId);
    return `<div class="video" data-yt="${id}"><button type="button" aria-label="Play video: ${esc(v.title)}">
        <img src="https://i.ytimg.com/vi/${id}/hqdefault.jpg" alt="Video thumbnail: ${esc(v.title)}" loading="lazy">
        <span class="play">${ICON.bigplay}</span></button></div>
      <p class="vmeta"><a href="${esc(v.url)}" target="_blank" rel="noopener">${esc(v.title)}</a> · ${esc(v.channel || "YouTube")}
      ${v.channelType === "preferred" ? '<span class="badge badge--ok">Trusted teacher</span>' : v.channelType === "publisher" ? '<span class="badge badge--ok">Publisher</span>' : ""}
      ${v.kind && v.kind !== "how-to-play" ? `<span class="badge badge--soft">${esc(v.kind)}</span>` : ""}${vbadge(v)}</p>
      ${v.note ? `<p class="note" style="margin-left:0">${esc(v.note)}</p>` : ""}`;
  }
  function houseRules(list) {
    if (!list || !list.length) return "";
    return `<ul class="hr-list">${list.map((h) => `<li><h4>${esc(h.name)} <span class="badge ${h.kind === "Official" ? "badge--ok" : "badge--comm"}">${h.kind === "Official" ? "Official variant" : "Community house rule"}</span></h4>
      <p>${esc(h.description)}</p>
      <div>${(h.tags || []).map((t) => `<span class="tag">${esc(t)}</span>`).join("")} <a href="${esc(h.url)}" target="_blank" rel="noopener">Source</a>${vbadge(h)}</div></li>`).join("")}</ul>`;
  }
  function detailHTML(g) {
    const L = g.links || {};
    const t = timeText(g);
    const statsDl = [
      [playersText(g), "players"], [g.bestPlayers || "—", "best at"], [t || "—", "play time"],
      [g.weight ? g.weight.toFixed(2) : "—", "weight / 5"], [g.minAge ? g.minAge + "+" : "—", "age"], [g.bggRating ? g.bggRating.toFixed(1) : "—", "BGG rating"],
    ].map(([v, l]) => `<div><dt>${l}</dt><dd>${esc(v)}</dd></div>`).join("");
    const anyBgg = [L.manual, ...(L.errata || []), ...(L.guides || [])].some((l) => l && isBgg(l.url));
    const errata = (L.errata || []).map((e) => linkRow("Errata / FAQ", e, ` <span class="badge ${e.official ? "badge--ok" : "badge--comm"}">${e.official ? "Official" : "Community"}</span>`)).join("");
    const guides = (L.guides || []).map((x) => linkRow("Guide", x)).join("");
    const exps = (g.expansions || []).map((e) => `<li class="exp"><img src="${esc(e.image.local || e.image.remote)}" alt="Box art for ${esc(e.name)}" loading="lazy">
        <div><h4>${esc(e.name)}</h4><p class="d-desc" style="font-size:.95rem">${esc(e.shortDescription || "")}</p>
        <ul class="links">${linkRow("Rules", e.links && e.links.manual)}${e.video ? linkRow("Video", { url: e.video.url, title: e.video.title + " · " + e.video.channel, verified: e.video.verified }) : ""}
        ${linkRow("BGG", { url: e.bggUrl, title: "BoardGameGeek page" })}</ul></div></li>`).join("");
    const rel = (g.relatedOwnedIds || []).map((id) => byId.get(id)).filter(Boolean).map((r) => `<a href="#game/${r._slug}"><img src="${esc(r.image.local || r.image.remote)}" alt="Box art for ${esc(r.name)}" loading="lazy">${esc(r.name)}</a>`).join("");
    const mistakes = (g.rulesMistakes || []).map((m) => `<li><p>${esc(m.text)}</p><a href="${esc(m.url)}" target="_blank" rel="noopener">Source</a>${vbadge(m)}</li>`).join("");
    return `
      <header class="d-head" style="--h:${hue(g.bggId)}">
        <button type="button" class="d-close" aria-label="Close details">${ICON.close}</button>
        <img src="${esc(g.image.local || g.image.remote)}" alt="Box art for ${esc(g.name)}">
        <div>
          <p class="d-kicker">${g.year || ""}${g.publisher ? " · " + esc(g.publisher) : ""}</p>
          <h2 class="d-title" id="dTitle">${esc(g.name)}</h2>
          <p class="d-sub">${g.edition ? esc(g.edition) : ""}${g.designers && g.designers.length ? (g.edition ? " · " : "") + "by " + esc(g.designers.join(", ")) : ""}</p>
          <dl class="d-stats">${statsDl}</dl>
        </div>
      </header>
      <div class="d-body">
        <section class="d-sec">
          ${g.shortDescription ? `<p class="d-desc">${esc(g.shortDescription)}</p>` : ""}
          <div class="chipline">${(g.categories || []).map((c) => `<span class="tag">${esc(c)}</span>`).join("")}</div>
          <p class="note" style="margin:10px 0 0">Mechanics: ${esc((g.mechanics || []).join(", ") || "—")}</p>
        </section>
        ${g.video ? `<section class="d-sec"><h3>How to play</h3>${videoBlock(g.video, g.name)}</section>` : `<section class="d-sec"><h3>How to play</h3><p class="d-desc">${esc(g.videoMissingReason || "No how-to-play video found yet.")}</p></section>`}
        <section class="d-sec"><h3>Rules &amp; resources</h3>
          <ul class="links">
            ${linkRow("Rulebook", L.manual, L.manual ? ` <span class="badge badge--soft">${esc(SRC[L.manual.source] || "")}</span>` : "")}
            ${errata || '<li><span class="kind">Errata / FAQ</span><span class="note" style="margin:0;flex-basis:auto">None found yet</span></li>'}
            ${guides}
            ${linkRow("Rules forum", L.rulesForum)}
            ${linkRow("Variants", L.variantsForum)}
            ${L.filesPage ? linkRow("All files", { url: L.filesPage, title: "BGG files page" }) : ""}
            ${g.publisherSite ? linkRow("Publisher", { url: g.publisherSite.url, title: g.publisherSite.title }) : ""}
            ${linkRow("BGG", { url: g.bggUrl, title: "BoardGameGeek page" })}
          </ul>
          ${anyBgg || (L.manual && L.manual.source === "bgg_files_page") ? '<p class="note" style="margin:12px 0 0">BGG file downloads need a free BoardGameGeek login.</p>' : ""}
        </section>
        ${(g.houseRules || []).length ? `<section class="d-sec"><h3>House rules &amp; variants</h3>${houseRules(g.houseRules)}</section>` : ""}
        ${mistakes ? `<section class="d-sec"><h3>Rules people often get wrong</h3><ul class="hr-list">${mistakes}</ul></section>` : ""}
        ${exps ? `<section class="d-sec"><h3>Expansions on the shelf</h3><ul class="exp-list">${exps}</ul></section>` : ""}
        ${rel ? `<section class="d-sec"><h3>Related games we own</h3><div class="related">${rel}</div></section>` : ""}
      </div>`;
  }
  function openDetail(g) {
    const dlg = $("#detail"), body = $("#detailBody");
    body.innerHTML = detailHTML(g);
    body.scrollTop = 0;
    body.querySelector(".d-close").addEventListener("click", () => dlg.close());
    body.querySelectorAll(".video button").forEach((b) => b.addEventListener("click", () => {
      const box = b.parentElement, id = box.dataset.yt;
      box.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0" title="${esc(g.name)} how-to-play video" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen loading="lazy"></iframe>`;
    }));
    document.title = `${g.name} · Shea's Game Shelf`;
    if (!dlg.open) dlg.showModal();
    body.querySelector(".d-close").focus({ preventScroll: true });
  }
  function restoreFocus() {
    document.title = "Shea's Game Shelf · The Nelson family board game library";
    if (lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
  }
  function route() {
    const m = location.hash.match(/^#game\/(\d+)/);
    const dlg = $("#detail");
    if (m && byId.has(+m[1])) openDetail(byId.get(+m[1]));
    else if (dlg.open) dlg.close();
  }

  load();
})();
