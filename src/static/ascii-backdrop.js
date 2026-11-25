/* Move only the decorative layer. Pointer input never moves workspace controls. */
const asciiHome = document.getElementById("homeView");
const asciiBackdrop = asciiHome.querySelector(".ascii-backdrop");
const asciiMotion = matchMedia("(prefers-reduced-motion: reduce)");

asciiHome.addEventListener("pointermove", (event) => {
  if (asciiMotion.matches || document.documentElement.dataset.reduceMotion === "true") return;
  const bounds = asciiHome.getBoundingClientRect();
  const x = (event.clientX - bounds.left) / bounds.width - 0.5;
  const y = (event.clientY - bounds.top) / bounds.height - 0.5;
  asciiBackdrop.style.setProperty("--ascii-x", `${x * 56}px`);
  asciiBackdrop.style.setProperty("--ascii-y", `${y * 32}px`);
}, { passive: true });

asciiHome.addEventListener("pointerleave", () => {
  asciiBackdrop.style.removeProperty("--ascii-x");
  asciiBackdrop.style.removeProperty("--ascii-y");
});
