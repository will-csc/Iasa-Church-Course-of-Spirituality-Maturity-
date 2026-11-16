(() => {
  const body = document.body;
  const role = body.dataset.role;
  const jitsiRoom = body.dataset.jitsi || "iasa-espiritual-reuniao";
  const isMaster = role === "master";

  let currentPdfUrl = body.dataset.pdfUrl || null;
  let viewPage = parseInt(body.dataset.page || "1", 10) || 1;
  let leaderPage = viewPage;
  let roomLocked = body.dataset.locked === "1";
  let pdfDoc = null;
  let rendering = false;
  let pendingPage = null;
  let highlightsByPage = {};
  let brushOn = false;
  let drawing = false;
  let currentStroke = [];

  const canvas = document.getElementById("pdf-canvas");
  const hlCanvas = document.getElementById("hl-canvas");
  const pdfStack = document.getElementById("pdf-stack");
  const emptyEl = document.getElementById("pdf-empty");
  const lockBadge = document.getElementById("lock-badge");
  const pageInput = document.getElementById("page-input");
  const leaderHint = document.getElementById("leader-hint");
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const btnGoto = document.getElementById("btn-goto");
  const btnFollow = document.getElementById("btn-follow-leader");
  const btnBrush = document.getElementById("btn-brush");
  const btnClearHl = document.getElementById("btn-clear-hl");
  const ctx = canvas.getContext("2d");
  const hlCtx = hlCanvas.getContext("2d");

  if (window["pdfjsLib"]) {
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
  }

  function updateLockBadge() {
    if (!lockBadge) return;
    if (roomLocked) {
      lockBadge.textContent = "Bloqueada";
      lockBadge.classList.add("locked");
      lockBadge.classList.remove("open");
    } else {
      lockBadge.textContent = "Aberta";
      lockBadge.classList.add("open");
      lockBadge.classList.remove("locked");
    }
  }

  function updateLeaderHint() {
    if (!leaderHint) return;
    leaderHint.textContent = `Apóstolo na pág. ${leaderPage}`;
    leaderHint.classList.toggle("behind", viewPage !== leaderPage);
  }

  function syncPageInput() {
    if (pageInput) pageInput.value = String(viewPage);
  }

  function pageKey(page) {
    return String(page);
  }

  function drawStroke(points, preview) {
    if (!points || points.length < 2) return;
    const w = hlCanvas.width;
    const h = hlCanvas.height;
    if (!w || !h) return;

    hlCtx.save();
    hlCtx.lineCap = "round";
    hlCtx.lineJoin = "round";
    hlCtx.strokeStyle = preview
      ? "rgba(255, 214, 0, 0.55)"
      : "rgba(255, 214, 0, 0.45)";
    hlCtx.lineWidth = Math.max(10, Math.min(w, h) * 0.018);
    hlCtx.beginPath();
    hlCtx.moveTo(points[0].x * w, points[0].y * h);
    for (let i = 1; i < points.length; i++) {
      hlCtx.lineTo(points[i].x * w, points[i].y * h);
    }
    hlCtx.stroke();
    hlCtx.restore();
  }

  function redrawHighlights() {
    const w = canvas.width;
    const h = canvas.height;
    if (!w || !h) return;
    hlCanvas.width = w;
    hlCanvas.height = h;
    hlCanvas.style.width = canvas.style.width || `${w}px`;
    hlCanvas.style.height = canvas.style.height || `${h}px`;
    hlCtx.clearRect(0, 0, w, h);
    const strokes = highlightsByPage[pageKey(viewPage)] || [];
    strokes.forEach((stroke) => drawStroke(stroke, false));
    if (currentStroke.length >= 2) drawStroke(currentStroke, true);
  }

  async function renderPage(pageNum) {
    if (!pdfDoc) return;
    if (rendering) {
      pendingPage = pageNum;
      return;
    }
    rendering = true;
    try {
      const page = await pdfDoc.getPage(pageNum);
      const unscaled = page.getViewport({ scale: 1 });
      const stage = canvas.closest(".pdf-stage");
      const maxWidth = Math.min(900, (stage ? stage.clientWidth : 0) - 16 || 800);
      const scale = maxWidth / unscaled.width;
      const viewport = page.getViewport({ scale });
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      await page.render({ canvasContext: ctx, viewport }).promise;
      pdfStack.classList.remove("hidden");
      emptyEl.classList.add("hidden");
      viewPage = pageNum;
      syncPageInput();
      updateLeaderHint();
      redrawHighlights();
    } catch (err) {
      console.error("Erro ao renderizar PDF:", err);
    } finally {
      rendering = false;
      if (pendingPage !== null && pendingPage !== pageNum) {
        const next = pendingPage;
        pendingPage = null;
        renderPage(next);
      } else {
        pendingPage = null;
      }
    }
  }

  async function loadPdf(url, page) {
    if (!url) {
      pdfDoc = null;
      currentPdfUrl = null;
      pdfStack.classList.add("hidden");
      emptyEl.classList.remove("hidden");
      return;
    }
    currentPdfUrl = url;
    viewPage = page || 1;
    const loadingTask = pdfjsLib.getDocument(url);
    pdfDoc = await loadingTask.promise;
    if (viewPage > pdfDoc.numPages) viewPage = pdfDoc.numPages;
    await renderPage(viewPage);
  }

  function applyHighlights(raw) {
    highlightsByPage = {};
    if (!raw || typeof raw !== "object") return;
    Object.keys(raw).forEach((key) => {
      highlightsByPage[String(key)] = raw[key] || [];
    });
  }

  function applyRoomState(state, opts) {
    if (!state) return;
    const forceFollow = !!(opts && opts.forceFollow);
    roomLocked = !!state.room_locked;
    updateLockBadge();
    leaderPage = state.current_page || 1;
    if (state.highlights) applyHighlights(state.highlights);

    const nextUrl = state.pdf_url || null;

    if (nextUrl !== currentPdfUrl) {
      const openPage = isMaster || forceFollow ? leaderPage : viewPage || leaderPage;
      loadPdf(nextUrl, openPage);
      return;
    }

    if (isMaster || forceFollow) {
      if (leaderPage !== viewPage) {
        renderPage(leaderPage);
        return;
      }
    }

    updateLeaderHint();
    redrawHighlights();
  }

  async function postJson(url, bodyObj) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(bodyObj || {}),
    });
    return res.json();
  }

  function goLocal(page) {
    if (!pdfDoc) return;
    const n = Math.max(1, Math.min(pdfDoc.numPages, parseInt(page, 10) || 1));
    renderPage(n);
  }

  async function setLeaderPage(page) {
    const n = Math.max(1, parseInt(page, 10) || 1);
    if (isMaster) {
      const data = await postJson("/api/room/page", { page: n });
      if (data && data.ok) applyRoomState(data, { forceFollow: true });
      return;
    }
    goLocal(n);
  }

  // Socket.IO
  const socket = io({ transports: ["websocket", "polling"] });
  socket.on("room_update", (state) => applyRoomState(state));
  socket.on("highlight_stroke", (payload) => {
    // Apóstolo já aplica pelo retorno da API; evita traço duplicado
    if (isMaster || !payload || !payload.stroke) return;
    const key = pageKey(payload.page);
    if (!highlightsByPage[key]) highlightsByPage[key] = [];
    highlightsByPage[key].push(payload.stroke);
    if (Number(payload.page) === viewPage) redrawHighlights();
  });
  socket.on("highlight_clear", (payload) => {
    if (isMaster) return;
    if (!payload || payload.page == null) {
      highlightsByPage = {};
    } else {
      delete highlightsByPage[pageKey(payload.page)];
    }
    redrawHighlights();
  });
  socket.on("connect", () => socket.emit("request_state"));

  if (currentPdfUrl) {
    loadPdf(currentPdfUrl, viewPage);
  }
  updateLockBadge();
  updateLeaderHint();

  // Abas mobile
  const tabButtons = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".panel[data-panel]");

  function activateTab(tab) {
    tabButtons.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tab);
    });
    panels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.panel === tab);
    });
    if (tab === "pdf" && pdfDoc) {
      setTimeout(() => renderPage(viewPage), 50);
    }
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });

  // Jitsi
  const jitsiContainer = document.getElementById("jitsi-container");
  if (jitsiContainer) {
    const iframe = document.createElement("iframe");
    const roomName = encodeURIComponent(jitsiRoom);
    iframe.allow = "camera; microphone; fullscreen; display-capture; autoplay";
    iframe.src =
      `https://meet.jit.si/${roomName}` +
      "#config.prejoinConfig.enabled=true&interfaceConfig.DISABLE_JOIN_LEAVE_NOTIFICATIONS=true&config.disableDeepLinking=true";
    iframe.title = "Chamada Jitsi";
    jitsiContainer.appendChild(iframe);
  }

  // Controles de página (todos)
  btnPrev.addEventListener("click", () => {
    if (isMaster) setLeaderPage(viewPage - 1);
    else goLocal(viewPage - 1);
  });
  btnNext.addEventListener("click", () => {
    const max = pdfDoc ? pdfDoc.numPages : viewPage + 1;
    const next = Math.min(max, viewPage + 1);
    if (isMaster) setLeaderPage(next);
    else goLocal(next);
  });
  btnGoto.addEventListener("click", () => {
    if (isMaster) setLeaderPage(pageInput.value);
    else goLocal(pageInput.value);
  });
  pageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      if (isMaster) setLeaderPage(pageInput.value);
      else goLocal(pageInput.value);
    }
  });
  if (btnFollow) {
    btnFollow.addEventListener("click", () => goLocal(leaderPage));
  }

  // Pincel (somente Apóstolo)
  function setBrushMode(on) {
    brushOn = !!on;
    if (btnBrush) btnBrush.classList.toggle("active-tool", brushOn);
    pdfStack.classList.toggle("brush-on", brushOn && isMaster);
  }

  function pointerPos(evt) {
    const rect = hlCanvas.getBoundingClientRect();
    const x = (evt.clientX - rect.left) / rect.width;
    const y = (evt.clientY - rect.top) / rect.height;
    return {
      x: Math.min(1, Math.max(0, x)),
      y: Math.min(1, Math.max(0, y)),
    };
  }

  function onPointerDown(evt) {
    if (!isMaster || !brushOn) return;
    evt.preventDefault();
    hlCanvas.setPointerCapture(evt.pointerId);
    drawing = true;
    currentStroke = [pointerPos(evt)];
  }

  function onPointerMove(evt) {
    if (!drawing) return;
    evt.preventDefault();
    const p = pointerPos(evt);
    const last = currentStroke[currentStroke.length - 1];
    if (last && Math.hypot(p.x - last.x, p.y - last.y) < 0.004) return;
    currentStroke.push(p);
    redrawHighlights();
  }

  async function onPointerUp(evt) {
    if (!drawing) return;
    drawing = false;
    try {
      hlCanvas.releasePointerCapture(evt.pointerId);
    } catch (_) {
      /* ignore */
    }
    const stroke = currentStroke.slice();
    currentStroke = [];
    if (stroke.length < 2) {
      redrawHighlights();
      return;
    }
    const data = await postJson("/api/room/highlight", { page: viewPage, stroke });
    if (data && data.ok && data.highlights) {
      applyHighlights(data.highlights);
    }
    redrawHighlights();
  }

  hlCanvas.addEventListener("pointerdown", onPointerDown);
  hlCanvas.addEventListener("pointermove", onPointerMove);
  hlCanvas.addEventListener("pointerup", onPointerUp);
  hlCanvas.addEventListener("pointercancel", onPointerUp);

  if (btnBrush) {
    btnBrush.addEventListener("click", () => setBrushMode(!brushOn));
  }
  if (btnClearHl) {
    btnClearHl.addEventListener("click", async () => {
      const data = await postJson("/api/room/highlight/clear", { page: viewPage });
      if (data && data.ok) {
        if (data.highlights) applyHighlights(data.highlights);
        else delete highlightsByPage[pageKey(viewPage)];
        redrawHighlights();
      }
    });
  }

  // Master-only admin
  if (isMaster) {
    const btnLock = document.getElementById("btn-lock");
    const btnUnlock = document.getElementById("btn-unlock");
    const btnClear = document.getElementById("btn-clear");
    const pdfInput = document.getElementById("pdf-input");
    const btnCopy = document.getElementById("btn-copy");
    const shareLink = document.getElementById("share-link");

    btnLock.addEventListener("click", async () => {
      const data = await postJson("/api/room/lock", { locked: true });
      if (data && data.ok) applyRoomState(data);
    });
    btnUnlock.addEventListener("click", async () => {
      const data = await postJson("/api/room/lock", { locked: false });
      if (data && data.ok) applyRoomState(data);
    });
    btnClear.addEventListener("click", async () => {
      if (!confirm("Voltar para o PDF padrão do curso?")) return;
      const data = await postJson("/api/room/clear", {});
      if (data && data.ok) applyRoomState(data, { forceFollow: true });
    });

    pdfInput.addEventListener("change", async () => {
      const file = pdfInput.files && pdfInput.files[0];
      if (!file) return;
      const form = new FormData();
      form.append("pdf", file);
      const res = await fetch("/api/room/upload", { method: "POST", body: form });
      const data = await res.json();
      if (!data.ok) {
        alert(data.error || "Falha no envio.");
        return;
      }
      applyRoomState(data, { forceFollow: true });
      pdfInput.value = "";
    });

    btnCopy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(shareLink.value);
        btnCopy.textContent = "Copiado!";
        setTimeout(() => {
          btnCopy.textContent = "Copiar";
        }, 1500);
      } catch {
        shareLink.select();
        document.execCommand("copy");
      }
    });

    const usersList = document.getElementById("users-list");
    const newUserName = document.getElementById("new-user-name");
    const newUserPass = document.getElementById("new-user-pass");
    const btnCreateUser = document.getElementById("btn-create-user");
    const userMsg = document.getElementById("user-msg");

    function renderUsers(names) {
      if (!usersList) return;
      usersList.innerHTML = "";
      if (!names || !names.length) {
        const li = document.createElement("li");
        li.className = "empty";
        li.textContent = "Nenhuma conta ainda.";
        usersList.appendChild(li);
        return;
      }
      names.forEach((name) => {
        const li = document.createElement("li");
        li.dataset.name = name;
        const span = document.createElement("span");
        span.textContent = name;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "secondary btn-del-user";
        btn.dataset.name = name;
        btn.textContent = "Remover";
        li.appendChild(span);
        li.appendChild(btn);
        usersList.appendChild(li);
      });
    }

    if (usersList) {
      usersList.addEventListener("click", async (e) => {
        const btn = e.target.closest(".btn-del-user");
        if (!btn) return;
        const name = btn.dataset.name;
        if (!confirm(`Remover a conta "${name}"?`)) return;
        const data = await postJson("/api/users/delete", { name });
        if (!data.ok) {
          userMsg.textContent = data.error || "Erro ao remover.";
          return;
        }
        userMsg.textContent = "Conta removida.";
        renderUsers(data.users || []);
      });
    }

    if (btnCreateUser) {
      btnCreateUser.addEventListener("click", async () => {
        const name = (newUserName.value || "").trim();
        const password = newUserPass.value || "";
        const data = await postJson("/api/users", { name, password });
        if (!data.ok) {
          userMsg.textContent = data.error || "Erro ao criar.";
          return;
        }
        userMsg.textContent = "Conta criada.";
        newUserName.value = "";
        newUserPass.value = "";
        renderUsers(data.users || []);
      });
    }
  }

  window.addEventListener("resize", () => {
    if (pdfDoc) renderPage(viewPage);
  });
})();
