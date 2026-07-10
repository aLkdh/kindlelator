const captureBtn = document.getElementById("captureBtn");
const savePortBtn = document.getElementById("savePortBtn");
const backendUrlInput = document.getElementById("backendUrlInput");
const statusEl = document.getElementById("status");

function setStatus(text) {
  statusEl.textContent = text;
}

function loadBackendUrl() {
  chrome.storage.local.get({ backendUrl: "", backendPort: "8000" }, (items) => {
    const storedUrl = (items.backendUrl || "").trim();
    if (storedUrl) {
      backendUrlInput.value = storedUrl;
      return;
    }

    backendUrlInput.value = `http://127.0.0.1:${items.backendPort || "8000"}`;
  });
}

savePortBtn.addEventListener("click", () => {
  const url = backendUrlInput.value.trim();

  try {
    const parsed = new URL(url);
    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw new Error("unsupported protocol");
    }
  } catch (error) {
    setStatus("Enter a valid http or https URL.");
    return;
  }

  chrome.storage.local.set({ backendUrl: url }, () => {
    if (chrome.runtime.lastError) {
      setStatus(`Save failed: ${chrome.runtime.lastError.message}`);
      return;
    }

    setStatus(`Backend URL saved: ${url}`);
  });
});

captureBtn.addEventListener("click", () => {
  setStatus("Starting capture...");

  chrome.runtime.sendMessage({ type: "startCapture" }, (response) => {
    if (chrome.runtime.lastError) {
      setStatus(`Error: ${chrome.runtime.lastError.message}`);
      return;
    }

    if (response?.ok) {
      setStatus("Capture request sent. Check the page sidebar for results.");
    } else {
      const errorText = response?.error || "Capture request failed.";
      setStatus(`Capture failed: ${errorText}`);
    }
  });
});

loadBackendUrl();
