// Global utilities. HTMX + Alpine + KaTeX + highlight.js load via CDN in base.html.
// We add tiny helpers here:
//   - Re-run KaTeX / hljs after HTMX swaps so newly-inserted content renders math/code.
//   - Auto-dismiss flash messages after a delay.

document.addEventListener("htmx:afterSwap", (evt) => {
  if (window.renderMathInElement) {
    window.renderMathInElement(evt.target, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$",  right: "$",  display: false },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
      ],
      throwOnError: false,
    });
  }
  if (window.hljs) {
    evt.target.querySelectorAll("pre code").forEach((b) => window.hljs.highlightElement(b));
  }
});

// Auto-dismiss flash messages.
window.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 6000);
  });
});
