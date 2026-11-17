(function () {
  try {
    var t = localStorage.getItem("shelf-theme");
    if (t !== "light" && t !== "dark") return;
    document.documentElement.setAttribute("data-theme", t);
    var m = document.querySelector('meta[name="color-scheme"]');
    if (m) m.setAttribute("content", t);
    var c = document.querySelector('meta[name="theme-color"]');
    if (c) c.setAttribute("content", t === "dark" ? "#161310" : "#f4efe6");
  } catch (e) {}
})();
