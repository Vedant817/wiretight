const pad = (n) => String(n).padStart(2, "0");

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else if (value !== null && value !== undefined) {
      node.setAttribute(key, value);
    }
  }
  for (const child of children) {
    if (child) node.append(child);
  }
  return node;
}

function recipeCard(item, recommended, withWatch) {
  const brief = el("pre", { "data-prompt": "" });
  brief.textContent = item.brief;
  return el("article", { class: recommended ? "recipe is-recommended" : "recipe" }, [
    recommended ? el("p", { class: "recipe-flag", text: "Recommended" }) : null,
    el("h3", { text: item.title }),
    el("p", { class: "recipe-promise", text: item.promise }),
    el("p", { class: "recipe-body", text: item.body }),
    el("div", { class: "prompt" }, [
      brief,
      el("button", { class: "copy-btn", type: "button", "data-copy": "", text: "Copy brief" }),
    ]),
    item.steps && item.steps.length
      ? el("div", { class: "prompt prompt-slim" }, [
          el("pre", {
            "data-prompt": "",
            text: item.steps.map((step, i) => `${i + 1}. ${step}`).join("\n"),
          }),
          el("button", {
            class: "copy-btn",
            type: "button",
            "data-copy": "",
            text: "Copy sequence",
          }),
        ])
      : null,
    withWatch && item.watch && item.watch.length
      ? el("div", { class: "prompt prompt-slim" }, [
          el("pre", {
            "data-prompt": "",
            text: item.watch.map((line) => `- ${line}`).join("\n"),
          }),
          el("button", {
            class: "copy-btn",
            type: "button",
            "data-copy": "",
            text: "Copy watch-outs",
          }),
        ])
      : null,
  ]);
}

function renderRecipes(data, selector, limit) {
  const root = document.querySelector(selector);
  if (!root) return;
  root.replaceChildren();
  const items = Array.isArray(data) ? data : data.items || [];
  const slice = typeof limit === "number" ? items.slice(0, limit) : items;
  const teaser = selector === "#recipe-teaser";
  slice.forEach((item, i) => {
    root.append(recipeCard(item, teaser && i === 0, !teaser));
  });
}

function renderLibrary(data) {
  const root = document.querySelector("#library-list");
  if (!root) return;
  renderRecipes(data, "#library-list");
}

function bindVideo(wrapper) {
  const video = wrapper.querySelector("video");
  const play = wrapper.querySelector(".play");
  if (!video || !play) return;

  const start = () => {
    wrapper.classList.add("is-playing");
    video.setAttribute("controls", "");
    video.play();
  };

  play.addEventListener("click", start);
  video.addEventListener("play", () => wrapper.classList.add("is-playing"));
}

function renderBuilds(builds) {
  const root = document.querySelector("#builds-list");
  if (!root) return;
  root.replaceChildren();

  builds.forEach((build) => {
    const videoWrap = el("div", { class: "video" }, [
      el("img", {
        class: "video-poster",
        src: build.poster,
        alt: "",
      }),
    ]);
    if (build.video) {
      videoWrap.append(
        el("video", {
          preload: "none",
          playsinline: "",
        }),
        el("button", { class: "play", type: "button", "aria-label": `Play ${build.title}` }, [
          el("span", { class: "play-glyph" }),
        ])
      );
      const video = videoWrap.querySelector("video");
      videoWrap.querySelector(".play").addEventListener("click", () => {
        if (!video.getAttribute("src")) video.src = build.video;
        videoWrap.classList.add("is-playing");
        video.setAttribute("controls", "");
        video.play();
      });
      video.addEventListener("play", () => videoWrap.classList.add("is-playing"));
    }

    const script = build.script
      ? el("details", { class: "build-script" }, [
          el("summary", { text: "Script" }),
          el(
            "ol",
            {},
            build.script.map((line) => el("li", { text: line }))
          ),
        ])
      : null;

    const links = el("div", { class: "build-links" }, [
      build.pdf ? el("a", { href: build.pdf, text: "PDF" }) : null,
      build.source
        ? el("a", {
            href: build.source,
            text: "GitHub",
            target: "_blank",
            rel: "noopener noreferrer",
          })
        : el("span", { class: "soon", text: "GitHub soon" }),
      build.replit
        ? el("a", {
            href: build.replit,
            text: "Replit",
            target: "_blank",
            rel: "noopener noreferrer",
          })
        : null,
      typeof build.demo === "string"
        ? el("a", {
            href: build.demo,
            text: "Demo",
            target: "_blank",
            rel: "noopener noreferrer",
          })
        : null,
      (() => {
        const share = el("button", {
          class: "share-btn",
          type: "button",
          text: "Share",
        });
        const url = `https://airwallexdev.com/builds#${build.id}`;
        share.addEventListener("click", async () => {
          try {
            if (navigator.share) {
              await navigator.share({ title: build.title, url });
              return;
            }
          } catch (err) {
            if (err && err.name === "AbortError") return;
          }
          try {
            await navigator.clipboard.writeText(url);
            share.textContent = "Copied";
            setTimeout(() => {
              share.textContent = "Share";
            }, 1600);
          } catch {
            window.prompt("Copy link", url);
          }
        });
        return share;
      })(),
      script,
    ]);

    root.append(
      el("article", { class: "ref-card", id: build.id }, [
        videoWrap,
        el("div", { class: "ref-copy" }, [
          el("h3", { text: build.title }),
          el("p", { class: "recipe-promise", text: build.lede }),
          links,
        ]),
      ])
    );
  });

  requestAnimationFrame(() => requestAnimationFrame(scrollToBuildHash));
}

function scrollToBuildHash() {
  const id = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (!id) return;
  const node = document.getElementById(id);
  if (node) node.scrollIntoView({ block: "start" });
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.append(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  }
}

function bindCopy() {
  document.querySelectorAll("[data-copy]").forEach((button) => {
    if (button.dataset.bound) return;
    button.dataset.bound = "1";
    const label = button.textContent;
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const url = button.dataset.copyMd;
      if (url) {
        let ok = false;
        try {
          const response = await fetch(url);
          if (!response.ok) throw new Error("fetch");
          ok = await copyText((await response.text()).trim());
        } catch {
          ok = false;
        }
        button.textContent = ok ? "Copied" : "Select";
        if (ok) button.classList.add("is-copied");
        window.setTimeout(() => {
          button.textContent = label;
          button.classList.remove("is-copied");
        }, 1600);
        return;
      }
      const box = button.closest(".prompt");
      const source = box ? box.querySelector("[data-prompt]") : document.querySelector("[data-prompt]");
      if (!source) return;
      const ok = await copyText(source.textContent.trim());
      button.textContent = ok ? "Copied" : "Select";
      if (ok) button.classList.add("is-copied");
      window.setTimeout(() => {
        button.textContent = label;
        button.classList.remove("is-copied");
      }, 1600);
    });
  });
}

function sparkCode() {
  const canvas = document.querySelector(".code-spark");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let nodes = [];
  let running = true;
  const gap = 36;

  function place() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    const cols = Math.max(2, Math.floor(w / gap));
    const rows = Math.max(2, Math.floor(h / gap));
    const ox = (w - (cols - 1) * gap) / 2;
    const oy = (h - (rows - 1) * gap) / 2;
    nodes = [];
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        nodes.push({
          x: ox + c * gap,
          y: oy + r * gap,
          phase: Math.random() * Math.PI * 2,
          speed: 0.00035 + Math.random() * 0.0005,
          base: 0.04 + Math.random() * 0.015,
          amp: 0.05 + Math.random() * 0.04,
        });
      }
    }
  }

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    place();
    if (reduced) draw(0);
  }

  function draw(now) {
    const w = window.innerWidth;
    const h = window.innerHeight;
    ctx.clearRect(0, 0, w, h);
    for (const n of nodes) {
      const wave = Math.sin(now * n.speed + n.phase);
      const t = 0.5 + 0.5 * wave;
      const core = n.base + n.amp * t;
      const coral = wave > 0.9;
      const rgb = coral ? "255, 92, 57" : "236, 236, 232";
      if (t > 0.35) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, 1.4 + t * 0.8, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${0.015 + t * 0.035})`;
        ctx.fill();
      }
      ctx.beginPath();
      ctx.arc(n.x, n.y, 0.6, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${rgb}, ${core})`;
      ctx.fill();
    }
  }

  function tick(now) {
    if (!running) return;
    draw(now);
    requestAnimationFrame(tick);
  }

  document.addEventListener("visibilitychange", () => {
    running = !document.hidden;
    if (running && !reduced) requestAnimationFrame(tick);
  });

  window.addEventListener("resize", resize);
  resize();
  if (!reduced) requestAnimationFrame(tick);
}

function bindPromptCollapse() {
  const boxes = document.querySelectorAll(
    ".section-body > .prompt, .concept-body > .prompt, .tool-body > .prompt, .step-card > .prompt, .recipe > .prompt"
  );

  const overflows = (pre) => {
    const max = pre.style.maxHeight;
    pre.style.maxHeight = "none";
    const full = pre.scrollHeight;
    pre.style.maxHeight = max;
    return full > pre.clientHeight + 2;
  };

  const measure = () => {
    boxes.forEach((box) => {
      const pre = box.querySelector("pre");
      if (!pre || box.classList.contains("is-open")) return;
      if (overflows(pre)) box.classList.add("is-long");
      else box.classList.remove("is-long");
    });
  };

  boxes.forEach((box) => {
    const pre = box.querySelector("pre");
    if (!pre || pre.dataset.collapseBound) return;
    pre.dataset.collapseBound = "1";
    box.addEventListener("click", (event) => {
      if (event.target.closest(".copy-btn, a")) return;
      if (box.classList.contains("is-open") || overflows(pre) || box.classList.contains("is-long")) {
        box.classList.toggle("is-open");
      }
    });
  });

  measure();
  window.addEventListener("resize", measure);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);

  document.querySelectorAll("details.tool").forEach((tool) => {
    if (tool.dataset.collapseToggleBound) return;
    tool.dataset.collapseToggleBound = "1";
    tool.addEventListener("toggle", () => {
      if (tool.open) measure();
    });
  });
}

function bindTabs() {
  document.querySelectorAll("[data-tabs]").forEach((root) => {
    const tabs = [...root.querySelectorAll(":scope > .tabs [data-tab]")];
    const panels = [...root.querySelectorAll(":scope > [data-panel]")];
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const id = tab.dataset.tab;
        tabs.forEach((t) => t.classList.toggle("is-on", t === tab));
        panels.forEach((p) => {
          p.hidden = p.dataset.panel !== id;
        });
        bindPromptCollapse();
      });
    });
  });
}

if (location.hash === "#builds" || location.hash === "#library") {
  location.replace("/builds");
}

sparkCode();
bindCopy();
bindPromptCollapse();
bindTabs();
window.addEventListener("hashchange", scrollToBuildHash);

async function load() {
  const needsLibrary = document.querySelector("#library-list, #recipe-list, #recipe-teaser");
  const needsBuilds = document.querySelector("#builds-list");
  if (!needsLibrary && !needsBuilds) return;

  const [library, builds] = await Promise.all([
    fetch("/content/library.json").then((r) => r.json()),
    fetch("/content/builds.json").then((r) => r.json()),
  ]);

  renderLibrary(library);
  renderRecipes(library, "#recipe-list");
  renderRecipes(library, "#recipe-teaser", 2);
  renderBuilds(builds);
  bindCopy();
  bindPromptCollapse();
}

load().catch((err) => {
  const library = document.querySelector("#library-list");
  const builds = document.querySelector("#builds-list");
  const message = "Could not load this section. Refresh.";
  if (library) library.textContent = message;
  if (builds) builds.textContent = message;
  console.error(err);
});
