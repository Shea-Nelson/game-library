/* Injects the shared site header. Pages set data-root to the relative path of this repo's root (for shelf/ assets). */
const SITE = "https://shea-nelson.github.io/";
/* Each app lives in its own repo now, so the links are absolute. */
const LINKS = [
  [SITE + "workout-app/", "Workout", "workout"],
  [SITE + "kitchen/recipes/", "Recipes", "recipes"],
  [SITE + "kitchen/planner/", "Planner", "planner"],
  [SITE + "bible-study/bible/", "Bible", "bible"],
  [SITE + "grok-lessons/", "Lessons", "lesson"],
  [SITE + "family-time/", "Family", "family"],
  [SITE + "game-library/", "Games", "games"],
  [SITE, "All pages", "hub"],
];

function currentKey() {
  const path = location.pathname.replace(/\/index\.html$/, "/");
  if (/^\/bible-study(\/|$)/.test(path)) return "bible";
  if (/^\/grok-lessons(\/|$)/.test(path)) return "lesson";
  if (/^\/family-time(\/|$)/.test(path)) return "family";
  if (/^\/game-library(\/|$)/.test(path)) return "games";
  if (/^\/kitchen\/recipes(\/|$)/.test(path)) return "recipes";
  if (/^\/kitchen\/planner(\/|$)/.test(path)) return "planner";
  if (/^\/workout-app(\/|$)/.test(path)) return "workout";
  return "hub";
}

function resolvedDark() {
  const explicit = document.documentElement.getAttribute("data-theme");
  if (explicit === "dark") return true;
  if (explicit === "light") return false;
  return matchMedia("(prefers-color-scheme: dark)").matches;
}

function syncThemeControl() {
  const dark = resolvedDark();
  const btn = document.querySelector(".theme-btn");
  const color = document.querySelector('meta[name="theme-color"]');
  if (color) color.setAttribute("content", dark ? "#161310" : "#f4efe6");
  if (!btn) return;
  btn.setAttribute("aria-pressed", dark ? "true" : "false");
  btn.textContent = dark ? "Light" : "Dark";
  btn.setAttribute("aria-label", dark ? "Switch to light colors" : "Switch to dark colors");
}

function applyTheme(next, persist) {
  const meta = document.querySelector('meta[name="color-scheme"]');
  if (next === "light" || next === "dark") {
    document.documentElement.setAttribute("data-theme", next);
    if (meta) meta.setAttribute("content", next);
  } else {
    document.documentElement.removeAttribute("data-theme");
    if (meta) meta.setAttribute("content", "light dark");
  }
  if (persist !== false) {
    try {
      if (next === "light" || next === "dark") localStorage.setItem("shelf-theme", next);
      else localStorage.removeItem("shelf-theme");
    } catch (e) {}
  }
  syncThemeControl();
}

function buildHeader() {
  const root = document.body.dataset.root || "./";
  const here = currentKey();
  const header = document.createElement("header");
  header.className = "site";
  const brand = document.createElement("a");
  brand.className = "brand";
  brand.href = SITE;
  const img = document.createElement("img");
  img.src = root + "shelf/favicon.svg";
  img.alt = "";
  img.width = 28;
  img.height = 28;
  const name = document.createElement("span");
  name.textContent = "Pages";
  brand.append(img, name);
  const nav = document.createElement("nav");
  nav.setAttribute("aria-label", "Pages on this site");
  for (const [href, label, key] of LINKS) {
    const a = document.createElement("a");
    a.href = href;
    a.textContent = label;
    if (key === here) a.setAttribute("aria-current", "page");
    nav.append(a);
  }
  const ext = document.createElement("a");
  ext.href = "https://shea-nelson.github.io/davenport-table/";
  ext.target = "_blank";
  ext.rel = "noopener noreferrer";
  ext.textContent = "Davenport";
  const sr = document.createElement("span");
  sr.className = "sr";
  sr.textContent = " (opens in a new tab)";
  ext.append(sr);
  nav.append(ext);
  const theme = document.createElement("button");
  theme.type = "button";
  theme.className = "theme-btn";
  theme.addEventListener("click", () => {
    applyTheme(resolvedDark() ? "light" : "dark");
  });
  header.append(brand, nav, theme);
  return header;
}

const skip = document.querySelector(".skip");
const header = buildHeader();
if (skip) skip.after(header);
else document.body.prepend(header);
applyTheme(document.documentElement.getAttribute("data-theme"), false);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if (!document.documentElement.getAttribute("data-theme")) syncThemeControl();
});
window.addEventListener("storage", (e) => {
  if (e.key !== "shelf-theme") return;
  const next = e.newValue === "light" || e.newValue === "dark" ? e.newValue : null;
  applyTheme(next, false);
});
