const PANEL_ID = "kindlelator-ocr-sidebar";

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "ocrCaptured") {
    showCaptureNotification("Captured...");
  }

  if (message.type === "ocrResult") {
    showSidebar(message.text, null, "OCR completed");
  }

  if (message.type === "translateResult") {
    showSidebar(null, message.text, "Translation completed");
  }
});

function showSidebar(ocrText, translatedText = null, status = "") {
  let panel = document.getElementById(PANEL_ID);
  const saved = window.localStorage.getItem(`${PANEL_ID}-collapsed`);
  const collapsedInitial = saved === "true";

  if (!panel) {
    panel = document.createElement("div");
    panel.id = PANEL_ID;
    panel.style.position = "fixed";
    panel.style.top = "0";
    panel.style.right = "0";
    panel.style.width = collapsedInitial ? "48px" : "360px";
    panel.style.height = "100vh";
    panel.style.background = "rgba(255, 255, 255, 0.96)";
    panel.style.borderLeft = "1px solid #ccc";
    panel.style.boxShadow = "-4px 0 12px rgba(0, 0, 0, 0.12)";
    panel.style.zIndex = "2147483647";
    panel.style.overflow = "hidden";
    panel.style.transition = "width 200ms ease";
    panel.style.fontFamily = "Segoe UI, sans-serif";
    panel.style.color = "#111";

    // Header (always visible)
    const header = document.createElement("div");
    header.id = `${PANEL_ID}-header`;
    header.style.display = "flex";
    header.style.alignItems = "center";
    header.style.justifyContent = "space-between";
    header.style.padding = "10px";
    header.style.borderBottom = "1px solid #eee";
    header.style.background = "transparent";

    const title = document.createElement("div");
    title.id = `${PANEL_ID}-title`;
    title.textContent = "Kindlelator";
    title.style.fontWeight = "700";
    title.style.fontSize = "13px";
    title.style.marginRight = "8px";
    header.appendChild(title);

    const controls = document.createElement("div");
    controls.style.display = "flex";
    controls.style.gap = "6px";

    const toggleBtn = document.createElement("button");
    toggleBtn.id = `${PANEL_ID}-toggle`;
    toggleBtn.textContent = collapsedInitial ? ">" : "‹";
    toggleBtn.title = collapsedInitial ? "펼치기" : "접기";
    toggleBtn.style.padding = "6px 8px";
    toggleBtn.style.border = "1px solid #ddd";
    toggleBtn.style.background = "#fff";
    toggleBtn.style.cursor = "pointer";
    toggleBtn.addEventListener("click", () => toggleCollapse(panel));
    controls.appendChild(toggleBtn);

    const closeBtn = document.createElement("button");
    closeBtn.textContent = "✕";
    closeBtn.title = "닫기";
    closeBtn.style.padding = "6px 8px";
    closeBtn.style.border = "1px solid #ddd";
    closeBtn.style.background = "#fff";
    closeBtn.style.cursor = "pointer";
    closeBtn.addEventListener("click", () => panel.remove());
    controls.appendChild(closeBtn);

    header.appendChild(controls);
    panel.appendChild(header);

    // Content container (hidden when collapsed)
    const contentWrap = document.createElement("div");
    contentWrap.id = `${PANEL_ID}-content`;
    contentWrap.style.padding = "14px";
    contentWrap.style.overflowY = "auto";
    contentWrap.style.height = "calc(100vh - 52px)";

    const statusLine = document.createElement("div");
    statusLine.id = `${PANEL_ID}-status`;
    statusLine.style.marginBottom = "12px";
    statusLine.style.color = "#444";
    statusLine.style.fontSize = "13px";
    contentWrap.appendChild(statusLine);

    const translateLabel = document.createElement("div");
    translateLabel.textContent = "번역 결과";
    translateLabel.style.fontSize = "14px";
    translateLabel.style.fontWeight = "700";
    translateLabel.style.margin = "6px 0 6px 0";
    contentWrap.appendChild(translateLabel);

    const translateContent = document.createElement("pre");
    translateContent.id = `${PANEL_ID}-translate-content`;
    translateContent.style.whiteSpace = "pre-wrap";
    translateContent.style.wordBreak = "break-word";
    translateContent.style.fontSize = "14px";
    translateContent.style.lineHeight = "1.5";
    translateContent.style.margin = "0";
    translateContent.style.minHeight = "80px";
    translateContent.style.padding = "10px";
    translateContent.style.background = "#fafafa";
    translateContent.style.border = "1px solid #ddd";
    translateContent.style.borderRadius = "6px";
    contentWrap.appendChild(translateContent);

    panel.appendChild(contentWrap);
    document.body.appendChild(panel);
  }

  // Apply collapsed state if needed
  const isCollapsed = window.localStorage.getItem(`${PANEL_ID}-collapsed`) === "true";
  setCollapsed(panel, isCollapsed === true || isCollapsed === "true");

  const statusLine = document.getElementById(`${PANEL_ID}-status`);
  if (statusLine) {
    statusLine.textContent = status;
  }

  const translateContent = document.getElementById(`${PANEL_ID}-translate-content`);
  if (translateContent) {
    translateContent.textContent = translatedText || "번역 결과를 기다리는 중입니다...";
  }
}

function setCollapsed(panel, collapsed) {
  const toggleBtn = panel.querySelector(`#${PANEL_ID}-toggle`);
  const contentWrap = panel.querySelector(`#${PANEL_ID}-content`);
  const headerEl = panel.querySelector(`#${PANEL_ID}-header`);
  const titleEl = panel.querySelector(`#${PANEL_ID}-title`);
  if (collapsed) {
    panel.style.width = "48px";
    if (contentWrap) contentWrap.style.display = "none";
    if (toggleBtn) { toggleBtn.textContent = ">"; toggleBtn.title = "펼치기"; }
    if (titleEl) titleEl.style.display = "none";
    if (headerEl) headerEl.style.justifyContent = "center";
  } else {
    panel.style.width = "360px";
    if (contentWrap) contentWrap.style.display = "block";
    if (toggleBtn) { toggleBtn.textContent = "‹"; toggleBtn.title = "접기"; }
    if (titleEl) titleEl.style.display = "block";
    if (headerEl) headerEl.style.justifyContent = "space-between";
  }
  window.localStorage.setItem(`${PANEL_ID}-collapsed`, collapsed ? "true" : "false");
}

function toggleCollapse(panel) {
  const cur = window.localStorage.getItem(`${PANEL_ID}-collapsed`) === "true";
  setCollapsed(panel, !cur);
}

function showCaptureNotification(message) {
  const noticeId = `${PANEL_ID}-capture-notice`;
  let notice = document.getElementById(noticeId);
  if (!notice) {
    notice = document.createElement("div");
    notice.id = noticeId;
    notice.style.position = "fixed";
    notice.style.top = "16px";
    notice.style.right = "16px";
    notice.style.padding = "10px 14px";
    notice.style.background = "rgba(0, 0, 0, 0.78)";
    notice.style.color = "#fff";
    notice.style.borderRadius = "8px";
    notice.style.boxShadow = "0 4px 16px rgba(0, 0, 0, 0.24)";
    notice.style.zIndex = "2147483647";
    notice.style.fontSize = "13px";
    notice.style.fontFamily = "Segoe UI, sans-serif";
    document.body.appendChild(notice);
  }

  notice.textContent = message;
  notice.style.opacity = "1";
  window.setTimeout(() => {
    if (notice) {
      notice.style.transition = "opacity 0.3s ease";
      notice.style.opacity = "0";
      window.setTimeout(() => notice?.remove(), 300);
    }
  }, 1400);
}
