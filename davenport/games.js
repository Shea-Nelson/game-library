import { renderPage } from "./shelf/doc.js";

const data = await fetch(new URL("data/games.json", import.meta.url).href).then((r) => {
  if (!r.ok) throw new Error("games");
  return r.json();
});

const app = document.querySelector("#app");
const host = document.createElement("div");
app.replaceChildren(host);
renderPage(data.tree, host);

function range(s) {
  const plus = s.includes("+");
  const nums = [...s.matchAll(/\d+/g)].map((m) => parseInt(m[0], 10));
  if (!nums.length) return null;
  return { min: nums[0], max: plus ? 99 : nums[nums.length - 1] };
}
function fits(players, n) {
  if (n === "any") return true;
  const r = range(players);
  if (!r) return true;
  const want = Number(n);
  return r.min <= want && want <= r.max;
}
function read(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v == null ? fallback : JSON.parse(v);
  } catch (e) { return fallback; }
}

const tables = [...document.querySelectorAll("table.data")];
const gameTables = tables.filter((t) => {
  const heads = [...t.querySelectorAll("th")].map((th) => th.textContent);
  return heads.includes("Players") && heads.includes("Game");
});

const bar = document.createElement("div");
bar.className = "seg noprint";
bar.setAttribute("role", "group");
bar.setAttribute("aria-label", "Player count");
const choices = [["any", "Any count"], ["2", "Fits 2"], ["4", "Fits 4"], ["6", "Fits 6"], ["8", "Fits 8"]];
let mode = read("games-players", "any");
if (!choices.some(([v]) => v === mode)) mode = "any";
const notes = read("games-notes", {});
const live = document.createElement("p");
live.className = "note";
live.setAttribute("aria-live", "polite");

function apply() {
  let shown = 0;
  let total = 0;
  gameTables.forEach((table) => {
    const heads = [...table.querySelectorAll("th")].map((th) => th.textContent);
    const pi = heads.indexOf("Players");
    table.querySelectorAll("tbody tr").forEach((tr) => {
      total += 1;
      const ok = fits(tr.cells[pi].textContent, mode);
      tr.hidden = !ok;
      if (ok) shown += 1;
    });
  });
  live.textContent = "Showing " + shown + " of " + total + " games. Notes stay on this device and are not a packing list.";
  localStorage.setItem("games-players", JSON.stringify(mode));
  [...bar.querySelectorAll("button")].forEach((b) => b.setAttribute("aria-pressed", b.dataset.value === mode ? "true" : "false"));
}

choices.forEach(([value, label]) => {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip";
  b.dataset.value = value;
  b.textContent = label;
  b.addEventListener("click", () => { mode = value; apply(); });
  bar.append(b);
});

gameTables.forEach((table) => {
  const th = document.createElement("th");
  th.scope = "col";
  th.textContent = "Your note";
  table.querySelector("thead tr").append(th);
  table.querySelectorAll("tbody tr").forEach((tr) => {
    const name = tr.cells[0].textContent;
    const td = document.createElement("td");
    td.dataset.label = "Your note";
    const label = document.createElement("label");
    label.className = "check noprint";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = !!notes[name];
    input.addEventListener("change", () => {
      const all = read("games-notes", {});
      all[name] = input.checked;
      localStorage.setItem("games-notes", JSON.stringify(all));
    });
    label.append(input, document.createTextNode(" On my list"));
    td.append(label);
    tr.append(td);
  });
});

const first = gameTables[0];
if (first) {
  const wrap = first.closest(".table-wrap");
  const intro = document.createElement("p");
  intro.className = "note";
  intro.textContent = "Filter uses the published player counts below. A check is only a note on this device.";
  wrap.before(bar, intro, live);
  apply();
}
