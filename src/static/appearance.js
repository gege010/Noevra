/* Resolve non-secret appearance preferences before the first paint. */
(function () {
  let theme = "dark";
  try {
    const saved = JSON.parse(localStorage.getItem("scholar_preferences") || "{}");
    if (["light", "dark", "system"].includes(saved.theme)) theme = saved.theme;
  } catch {
    // Storage is optional; the default workspace remains usable.
  }
  if (theme === "system")
    theme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]').content =
    theme === "dark" ? "#17191b" : "#f7f8f7";
})();
