/* Optional third-party features. Never send local previews to production services. */
(() => {
  "use strict";
  const section = document.querySelector(".engagement");
  if (!section) return;
  const config = section.dataset;
  const canonical = new URL(config.canonical);
  const pageviewsStatus = section.querySelector("[data-pageviews-status]");
  const commentsStatus = section.querySelector("[data-giscus-status]");
  const production = location.origin === canonical.origin;
  const theme = () => document.body.dataset.mdColorScheme === "slate" ? "dark" : "light";

  // Keep the authored article/book unchanged; only move the template's counter.
  const counter = section.querySelector(".pageviews");
  const title = document.querySelector(".md-content__inner h1");
  if (counter && title) title.insertAdjacentElement("afterend", counter);

  if (pageviewsStatus) {
    if (!production) {
      pageviewsStatus.textContent = "浏览量：本地预览不计数";
    } else if (location.search || location.pathname !== canonical.pathname) {
      // Busuanzi uses a full Referer. Do not leak query strings, especially the
      // temporary ?giscus= OAuth session, or split counts across index.html URLs.
      pageviewsStatus.textContent = "浏览量：带参数或非标准地址不计数";
    } else {
      const value = document.getElementById("busuanzi_value_page_pv");
      const container = document.getElementById("busuanzi_container_page_pv");
      pageviewsStatus.textContent = "浏览量：加载中…";
      let timer;
      const observer = new MutationObserver(() => {
        if (/^\d+$/.test(value.textContent.trim())) {
          clearTimeout(timer);
          pageviewsStatus.hidden = true;
          observer.disconnect();
        }
      });
      observer.observe(value, { childList: true, subtree: true, characterData: true });
      const failed = () => {
        container.style.display = "none";
        pageviewsStatus.hidden = false;
        pageviewsStatus.textContent = "浏览量：暂不可用";
      };
      timer = setTimeout(failed, 12000);
      const script = document.createElement("script");
      script.src = "https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js";
      script.async = true;
      script.referrerPolicy = "no-referrer-when-downgrade";
      script.onerror = () => { clearTimeout(timer); failed(); };
      document.head.appendChild(script);
    }
  }

  if (config.giscusEnabled !== "true" || !config.repoId || !config.categoryId) return;
  if (!production) {
    commentsStatus.textContent = "本地预览不连接评论服务；请在正式站点评论或点赞。";
    return;
  }

  const container = section.querySelector(".giscus");
  const failed = () => {
    commentsStatus.hidden = false;
    commentsStatus.textContent = "评论区暂不可用，请稍后刷新重试。";
  };
  const timer = setTimeout(failed, 20000);
  window.addEventListener("message", (event) => {
    const frame = container.querySelector("iframe.giscus-frame");
    if (event.origin !== "https://giscus.app" || !frame || event.source !== frame.contentWindow) return;
    const data = event.data && event.data.giscus;
    if (!data || typeof data !== "object") return;
    clearTimeout(timer);
    if (data.error) failed();
    else if (data.resizeHeight || "discussion" in data) commentsStatus.hidden = true;
  });
  const script = document.createElement("script");
  script.src = "https://giscus.app/client.js";
  script.async = true;
  script.crossOrigin = "anonymous";
  const attributes = {
    repo: config.repo, "repo-id": config.repoId,
    category: config.category, "category-id": config.categoryId,
    // A canonical pathname keeps query strings and index.html aliases out of keys.
    mapping: "specific", term: canonical.pathname, strict: "1",
    "reactions-enabled": "1", "emit-metadata": "1",
    "input-position": "top", theme: theme(), lang: "zh-CN",
    loading: "eager"
  };
  Object.entries(attributes).forEach(([key, value]) => script.setAttribute(`data-${key}`, value));
  script.onerror = () => { clearTimeout(timer); failed(); };
  commentsStatus.textContent = "评论区加载中…";
  container.appendChild(script);

  new MutationObserver(() => {
    const frame = container.querySelector("iframe.giscus-frame");
    if (frame) frame.contentWindow.postMessage({ giscus: { setConfig: { theme: theme() } } }, "https://giscus.app");
  }).observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
})();
