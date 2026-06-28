(function () {
  const cfg = window.ACADEMIA_PLAYER_CONFIG || {};
  const container = document.getElementById("academia-player-container");
  const watermark = document.getElementById("academia-watermark");
  const titleEl = document.getElementById("academia-current-title");
  const items = Array.from(document.querySelectorAll(".video-item"));
  if (!container) return;

  const state = {
    playback: null,
    currentVideoId: cfg.initialVideoId || null,
    secondsSinceHeartbeat: 0,
    heartbeatTimer: null,
    refreshTimer: null,
    watermarkTimer: null,
    tickTimer: null,
  };

  function csrfToken() {
    return cfg.csrfToken || "";
  }

  function setLoading(message) {
    container.innerHTML = `<div class="d-flex align-items-center justify-content-center h-100 text-white-50">${message}</div>`;
  }

  function setActiveItem(videoId) {
    items.forEach((item) => {
      item.classList.toggle("active", Number(item.dataset.videoId) === Number(videoId));
    });
  }

  function moveWatermark() {
    if (!watermark) return;
    watermark.style.top = `${5 + Math.random() * 80}%`;
    watermark.style.left = `${5 + Math.random() * 70}%`;
  }

  async function loadPlayback(videoId) {
    if (!videoId) return;
    setLoading("Cargando video...");
    setActiveItem(videoId);
    try {
      const resp = await fetch(`${cfg.apiBaseUrl}/videos/${videoId}/reproducir/`, {
        credentials: "include",
        headers: { "X-CSRFToken": csrfToken() },
      });
      if (!resp.ok) {
        const payload = await resp.json().catch(() => ({}));
        throw new Error(payload.detail || "No se pudo cargar el video");
      }
      const data = await resp.json();
      state.playback = data;
      state.currentVideoId = videoId;
      state.secondsSinceHeartbeat = 0;
      titleEl.textContent = data.titulo || "Video";
      container.innerHTML = `
        <iframe
          key="${data.embed_url}"
          src="${data.embed_url}"
          title="${data.titulo}"
          loading="lazy"
          allow="autoplay; fullscreen"
          allowfullscreen
          style="position:absolute;inset:0;width:100%;height:100%;border:0;"
        ></iframe>
      `;
      if (!document.getElementById("academia-watermark")) {
        const w = document.createElement("div");
        w.id = "academia-watermark";
        w.className = "player-watermark";
        w.textContent = cfg.userLabel || "";
        container.appendChild(w);
      }
      scheduleRefresh(data.expires);
      moveWatermark();
    } catch (err) {
      container.innerHTML = `<div class="d-flex align-items-center justify-content-center h-100 text-white-50">${err.message}</div>`;
    }
  }

  function scheduleRefresh(expires) {
    clearTimeout(state.refreshTimer);
    const now = Math.floor(Date.now() / 1000);
    const margin = 60;
    const ms = Math.max((expires - now - margin) * 1000, 5000);
    state.refreshTimer = setTimeout(() => {
      if (state.currentVideoId) loadPlayback(state.currentVideoId);
    }, ms);
  }

  async function sendHeartbeat() {
    if (!state.currentVideoId || document.hidden || state.secondsSinceHeartbeat <= 0) return;
    const segundos = state.secondsSinceHeartbeat;
    state.secondsSinceHeartbeat = 0;
    try {
      await fetch(`${cfg.apiBaseUrl}/videos/${state.currentVideoId}/heartbeat/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify({
          video_id: state.currentVideoId,
          segundos_reproducidos: segundos,
        }),
      });
    } catch (e) {
      // Se reintenta en el siguiente ciclo.
    }
  }

  items.forEach((item) => {
    item.addEventListener("click", () => {
      const vid = Number(item.dataset.videoId);
      if (vid) loadPlayback(vid);
    });
  });

  state.tickTimer = setInterval(() => {
    if (!document.hidden) state.secondsSinceHeartbeat += 1;
  }, 1000);

  state.heartbeatTimer = setInterval(sendHeartbeat, 30000);
  state.watermarkTimer = setInterval(moveWatermark, 8000);

  window.addEventListener("beforeunload", () => {
    sendHeartbeat();
  });

  if (state.currentVideoId) {
    loadPlayback(state.currentVideoId);
  } else if (items.length) {
    loadPlayback(items[0].dataset.videoId);
  } else {
    setLoading("No hay videos disponibles");
  }
})();
