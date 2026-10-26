/* Assets and fonts are hosted with the site; no external font/CDN dependency. */
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
    tags: "ams"
  },
  options: { ignoreHtmlClass: ".*|", processHtmlClass: "arithmatex" },
  chtml: { displayAlign: "center" }
};
