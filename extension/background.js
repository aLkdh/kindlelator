async function getBaseUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get({ backendUrl: "", backendPort: "8000" }, (items) => {
      const configuredUrl = (items.backendUrl || "").trim();
      if (configuredUrl) {
        resolve(configuredUrl.replace(/\/$/, ""));
        return;
      }

      resolve(`http://127.0.0.1:${items.backendPort || "8000"}`);
    });
  });
}

function captureVisibleTabDataUrl(windowId) {
  return new Promise((resolve, reject) => {
    const callback = (dataUrl) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (!dataUrl) {
        reject(new Error("captureVisibleTab returned no image data."));
        return;
      }
      resolve(dataUrl);
    };

    if (typeof windowId === "number") {
      chrome.tabs.captureVisibleTab(windowId, { format: "png" }, callback);
    } else {
      chrome.tabs.captureVisibleTab({ format: "png" }, callback);
    }
  });
}

async function startCapture(tab) {
  if (!tab || !tab.id) {
    throw new Error("No active tab available for capture.");
  }

  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"],
    });
  } catch (err) {
    console.warn("Could not inject content script:", err);
  }

  const baseUrl = await getBaseUrl();
  chrome.tabs.sendMessage(tab.id, { type: "ocrCaptured" }, () => {
    if (chrome.runtime.lastError) {
      console.warn("ocrCaptured message error:", chrome.runtime.lastError.message);
    }
  });

  try {
    const screenshotUrl = await captureVisibleTabDataUrl(tab.windowId);
    const ocrResponse = await fetch(`${baseUrl}/ocr`, {
      method: "POST",
      body: await buildFormDataFromDataUrl(screenshotUrl),
    });

    if (!ocrResponse.ok) {
      const errorText = `OCR request failed: ${ocrResponse.status} ${ocrResponse.statusText}`;
      throw new Error(errorText);
    }

    const ocrData = await ocrResponse.json();
    chrome.tabs.sendMessage(tab.id, { type: "ocrResult", text: ocrData.text });

    const translateResponse = await fetch(`${baseUrl}/translate`, {
      method: "POST",
    });

    if (!translateResponse.ok) {
      const errorText = `Translate request failed: ${translateResponse.status} ${translateResponse.statusText}`;
      throw new Error(errorText);
    }

    const translateData = await translateResponse.json();
    chrome.tabs.sendMessage(tab.id, { type: "translateResult", text: translateData.text });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("OCR capture error", message);
    chrome.tabs.sendMessage(tab.id, { type: "ocrResult", text: `OCR capture error: ${message}` });
    throw error;
  }
}

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "capture-kindle-screen") {
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  try {
    await startCapture(tab);
  } catch (error) {
    console.error("Command capture failed:", error);
  }
});

chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
  if (message.type === "startCapture") {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    try {
      await startCapture(tab);
      sendResponse({ ok: true });
    } catch (error) {
      sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) });
    }
    return true;
  }
});

async function buildFormDataFromDataUrl(dataUrl) {
  const blob = await (await fetch(dataUrl)).blob();
  const formData = new FormData();
  formData.append("image", blob, "image.png");
  return formData;
}
