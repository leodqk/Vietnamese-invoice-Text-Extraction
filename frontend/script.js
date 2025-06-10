// Configuration
const API_BASE_URL = "http://localhost:8000";
let currentFileId = null;
let currentResults = null;

// DOM Elements
const fileInput = document.getElementById("file-input");
const uploadArea = document.getElementById("upload-area");
const fileInfo = document.getElementById("file-info");
const methodSection = document.getElementById("method-section");
const resultsSection = document.getElementById("results-section");
const loadingOverlay = document.getElementById("loading-overlay");
// healthStatus removed to prevent reload issues

// Initialize
document.addEventListener("DOMContentLoaded", function () {
  initializeEventListeners();
});

// Prevent any unintended page reloads
window.addEventListener("beforeunload", function (e) {
  console.log("beforeunload event triggered");
});

// Catch all unhandled errors
window.addEventListener("error", function (e) {
  console.error("Global error caught:", e.error);
  e.preventDefault();
  return false;
});

// Catch all unhandled promise rejections
window.addEventListener("unhandledrejection", function (e) {
  console.error("Unhandled promise rejection:", e.reason);
  e.preventDefault();
  return false;
});

function initializeEventListeners() {
  // File input change
  if (fileInput) {
    fileInput.addEventListener("change", handleFileSelect);
  }

  // Drag and drop
  if (uploadArea) {
    uploadArea.addEventListener("dragover", handleDragOver);
    uploadArea.addEventListener("dragleave", handleDragLeave);
    uploadArea.addEventListener("drop", handleDrop);
  }

  // Method selection
  document.querySelectorAll('input[name="method"]').forEach((radio) => {
    radio.addEventListener("change", handleMethodChange);
  });

  // Extract button
  const extractBtn = document.getElementById("extract-btn");
  if (extractBtn) {
    console.log("Extract button found, adding event listener"); // Debug log
    extractBtn.addEventListener("click", handleExtractText);
  } else {
    console.log("Extract button NOT found!"); // Debug log
  }

  // Cleanup button
  if (document.getElementById("cleanup-btn")) {
    document
      .getElementById("cleanup-btn")
      .addEventListener("click", handleCleanup);
  }

  // Tab switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", handleTabSwitch);
  });

  // Choose file button
  const chooseFileBtn = document.getElementById("choose-file-btn");
  if (chooseFileBtn) {
    chooseFileBtn.addEventListener("click", function (e) {
      e.preventDefault();
      document.getElementById("file-input").click();
    });
  }

  // Reset button
  const resetBtn = document.getElementById("reset-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", function (e) {
      e.preventDefault();
      resetForm();
    });
  }

  // Copy buttons
  document.querySelectorAll(".btn-copy").forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const target = this.getAttribute("data-copy-target");
      if (target) {
        copyToClipboard(target);
      }
    });
  });
}

// Health check removed to prevent reload issues

// File handling
function handleFileSelect(event) {
  event.preventDefault();
  const file = event.target.files[0];
  if (file) {
    processFile(file);
  }
}

function handleDragOver(event) {
  event.preventDefault();
  if (uploadArea) {
    uploadArea.classList.add("dragover");
  }
}

function handleDragLeave(event) {
  event.preventDefault();
  if (uploadArea) {
    uploadArea.classList.remove("dragover");
  }
}

function handleDrop(event) {
  event.preventDefault();
  if (uploadArea) {
    uploadArea.classList.remove("dragover");
  }

  const files = event.dataTransfer.files;
  if (files.length > 0) {
    processFile(files[0]);
  }
}

async function processFile(file) {
  // Validate file type
  if (!file.type.startsWith("image/")) {
    showToast("Vui lòng chọn file hình ảnh!", "error");
    return;
  }

  // Validate file size (max 10MB)
  if (file.size > 10 * 1024 * 1024) {
    showToast("File quá lớn! Vui lòng chọn file nhỏ hơn 10MB.", "error");
    return;
  }

  showLoading("Đang upload file...");

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/upload-image`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (data.status === "success") {
      currentFileId = data.file_id;
      displayFileInfo(data, file);
      showMethodSection();
      showToast("Upload file thành công!", "success");
    } else {
      throw new Error(data.detail || "Upload failed");
    }
  } catch (error) {
    console.error("Upload error:", error);
    showToast(`Lỗi upload: ${error.message}`, "error");
  } finally {
    hideLoading();
  }
}

function displayFileInfo(data, file) {
  // Show file preview
  const reader = new FileReader();
  reader.onload = function (e) {
    const previewImg = document.getElementById("preview-image");
    if (previewImg) {
      previewImg.src = e.target.result;
    }
  };
  reader.readAsDataURL(file);

  // Update file details
  const fileName = document.getElementById("file-name");
  if (fileName) fileName.textContent = data.original_filename;

  const fileSize = document.getElementById("file-size");
  if (fileSize)
    fileSize.textContent = `Kích thước: ${formatFileSize(data.file_size)}`;

  const fileDimensions = document.getElementById("file-dimensions");
  if (fileDimensions) {
    fileDimensions.textContent = `Kích thước ảnh: ${data.image_dimensions.width} x ${data.image_dimensions.height}px`;
  }

  const fileId = document.getElementById("file-id");
  if (fileId) fileId.textContent = data.file_id;

  // Show file info
  if (fileInfo) {
    fileInfo.style.display = "block";
  }
}

function showMethodSection() {
  if (methodSection) {
    methodSection.style.display = "block";
    // Removed scrollIntoView to prevent any navigation issues
  }
}

// Method handling
function handleMethodChange(event) {
  event.preventDefault();
  const method = event.target.value;
  const normalOptions = document.getElementById("normal-options");
  const advanceOptions = document.getElementById("advance-options");

  if (method === "normal") {
    if (normalOptions) normalOptions.style.display = "block";
    if (advanceOptions) advanceOptions.style.display = "none";
  } else {
    if (normalOptions) normalOptions.style.display = "none";
    if (advanceOptions) advanceOptions.style.display = "block";
  }
}

// Text extraction
async function handleExtractText(event) {
  console.log("handleExtractText called", event);

  if (event) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
  }

  console.log("currentFileId:", currentFileId);

  if (!currentFileId) {
    showToast("Vui lòng upload file trước!", "error");
    return;
  }

  const methodRadio = document.querySelector('input[name="method"]:checked');
  if (!methodRadio) {
    showToast("Vui lòng chọn phương pháp trích xuất!", "error");
    return;
  }

  const method = methodRadio.value;
  console.log("Selected method:", method);

  showLoading("Đang trích xuất văn bản...");

  try {
    const formData = new FormData();
    formData.append("file_id", currentFileId);
    formData.append("method", method);

    if (method === "normal") {
      const saveCoordinates = document.getElementById("save-coordinates");
      const doRetrieve = document.getElementById("do-retrieve");
      const findBestRotation = document.getElementById("find-best-rotation");

      formData.append(
        "save_coordinates",
        saveCoordinates ? saveCoordinates.checked : false
      );
      formData.append("do_retrieve", doRetrieve ? doRetrieve.checked : false);
      formData.append(
        "find_best_rotation",
        findBestRotation ? findBestRotation.checked : false
      );
    } else {
      const customPrompt = document.getElementById("custom-prompt");
      if (customPrompt && customPrompt.value.trim()) {
        formData.append("custom_prompt", customPrompt.value.trim());
      }
    }

    const response = await fetch(`${API_BASE_URL}/extract-text`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log("API Response:", data); // Debug log

    if (data.status === "success") {
      console.log("Processing successful response...");
      currentResults = data;
      displayResults(data);
      showToast("Trích xuất văn bản thành công!", "success");
      console.log("handleExtractText completed successfully");
    } else {
      throw new Error(data.detail || "Extraction failed");
    }
  } catch (error) {
    console.error("Extraction error:", error);
    showToast(`Lỗi trích xuất: ${error.message}`, "error");
  } finally {
    console.log("Finally block - hiding loading");
    hideLoading();
    console.log("handleExtractText function finished");
  }

  return false; // Ensure no form submission
}

function displayResults(data) {
  console.log("Displaying results:", data); // Debug log

  // Update result info
  const resultMethod = document.getElementById("result-method");
  if (resultMethod) {
    resultMethod.textContent =
      data.method === "normal" ? "Normal Method" : "Advance Method";
  }

  const processingTime = document.getElementById("processing-time");
  if (processingTime) {
    processingTime.textContent = `${data.processing_info.processing_time}s`;
  }

  const resultFileSize = document.getElementById("result-file-size");
  if (resultFileSize) {
    resultFileSize.textContent = formatFileSize(
      data.processing_info.file_info.file_size
    );
  }

  // Display extracted text
  const extractedTextElement = document.getElementById("extracted-text");
  if (extractedTextElement) {
    if (data.method === "normal") {
      // Normal method results
      const textsArray = data.extracted_texts || [];
      const extractedText = textsArray.join("\n");
      extractedTextElement.value = extractedText;

      // Show coordinates tab if available
      const coordinatesTab = document.getElementById("coordinates-tab");
      const coordinatesData = document.getElementById("coordinates-data");
      if (data.coordinates && data.coordinates.length > 0) {
        if (coordinatesTab) coordinatesTab.style.display = "block";
        if (coordinatesData) {
          coordinatesData.textContent = JSON.stringify(
            data.coordinates,
            null,
            2
          );
        }
      }

      // Show retrieval tab if available
      const retrievalTab = document.getElementById("retrieval-tab");
      const retrievalData = document.getElementById("retrieval-data");
      if (
        data.retrieval_results &&
        Object.keys(data.retrieval_results).length > 0
      ) {
        if (retrievalTab) retrievalTab.style.display = "block";
        if (retrievalData) {
          retrievalData.textContent = JSON.stringify(
            data.retrieval_results,
            null,
            2
          );
        }
      }
    } else {
      // Advance method results
      extractedTextElement.value = data.extracted_text || "";

      // Hide tabs that are not relevant for advance method
      const coordinatesTab = document.getElementById("coordinates-tab");
      const retrievalTab = document.getElementById("retrieval-tab");
      if (coordinatesTab) coordinatesTab.style.display = "none";
      if (retrievalTab) retrievalTab.style.display = "none";
    }
  }

  // Show results section
  if (resultsSection) {
    resultsSection.style.display = "block";
    console.log("Results section displayed successfully");
    // Removed scrollIntoView to prevent any navigation issues
  }

  console.log("displayResults completed");
}

// Tab handling
function handleTabSwitch(event) {
  event.preventDefault();
  const targetTab = event.target.getAttribute("data-tab");
  if (!targetTab) return;

  // Remove active class from all tabs and panels
  document
    .querySelectorAll(".tab-btn")
    .forEach((btn) => btn.classList.remove("active"));
  document
    .querySelectorAll(".tab-panel")
    .forEach((panel) => panel.classList.remove("active"));

  // Add active class to clicked tab and corresponding panel
  event.target.classList.add("active");
  const targetPanel = document.getElementById(`${targetTab}-content`);
  if (targetPanel) {
    targetPanel.classList.add("active");
  }
}

// Cleanup
async function handleCleanup(event) {
  if (event) {
    event.preventDefault();
  }

  if (!currentFileId) {
    showToast("Không có file để dọn dẹp!", "warning");
    return;
  }

  if (!confirm("Bạn có chắc muốn dọn dẹp file này?")) {
    return;
  }

  showLoading("Đang dọn dẹp file...");

  try {
    const response = await fetch(`${API_BASE_URL}/cleanup/${currentFileId}`, {
      method: "DELETE",
    });

    const data = await response.json();

    if (data.status === "success") {
      showToast("Dọn dẹp file thành công!", "success");
      resetForm();
    } else {
      throw new Error(data.detail || "Cleanup failed");
    }
  } catch (error) {
    console.error("Cleanup error:", error);
    showToast(`Lỗi dọn dẹp: ${error.message}`, "error");
  } finally {
    hideLoading();
  }
}

// Reset form
function resetForm() {
  currentFileId = null;
  currentResults = null;

  // Reset file input
  if (fileInput) {
    fileInput.value = "";
  }

  // Hide sections
  if (fileInfo) {
    fileInfo.style.display = "none";
  }
  if (methodSection) {
    methodSection.style.display = "none";
  }
  if (resultsSection) {
    resultsSection.style.display = "none";
  }

  // Reset form values
  const normalMethod = document.getElementById("normal-method");
  if (normalMethod) {
    normalMethod.checked = true;
  }

  const saveCoordinates = document.getElementById("save-coordinates");
  const doRetrieve = document.getElementById("do-retrieve");
  const findBestRotation = document.getElementById("find-best-rotation");
  const customPrompt = document.getElementById("custom-prompt");

  if (saveCoordinates) {
    saveCoordinates.checked = false;
  }
  if (doRetrieve) {
    doRetrieve.checked = false;
  }
  if (findBestRotation) {
    findBestRotation.checked = false;
  }
  if (customPrompt) {
    customPrompt.value = "";
  }

  // Show normal options
  const normalOptions = document.getElementById("normal-options");
  const advanceOptions = document.getElementById("advance-options");
  if (normalOptions) {
    normalOptions.style.display = "block";
  }
  if (advanceOptions) {
    advanceOptions.style.display = "none";
  }

  // Reset tabs
  document
    .querySelectorAll(".tab-btn")
    .forEach((btn) => btn.classList.remove("active"));
  document
    .querySelectorAll(".tab-panel")
    .forEach((panel) => panel.classList.remove("active"));

  const textTab = document.querySelector('[data-tab="text"]');
  const textContent = document.getElementById("text-content");
  if (textTab) {
    textTab.classList.add("active");
  }
  if (textContent) {
    textContent.classList.add("active");
  }

  // Hide optional tabs
  const coordinatesTab = document.getElementById("coordinates-tab");
  const retrievalTab = document.getElementById("retrieval-tab");
  if (coordinatesTab) {
    coordinatesTab.style.display = "none";
  }
  if (retrievalTab) {
    retrievalTab.style.display = "none";
  }

  // Removed scroll to top to prevent any navigation issues
}

// Copy to clipboard
function copyToClipboard(elementId) {
  const element = document.getElementById(elementId);
  if (!element) return;

  const text =
    element.tagName === "TEXTAREA" ? element.value : element.textContent;

  if (navigator.clipboard) {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        showToast("Đã copy vào clipboard!", "success");
      })
      .catch(() => {
        fallbackCopyToClipboard(element);
      });
  } else {
    fallbackCopyToClipboard(element);
  }
}

function fallbackCopyToClipboard(element) {
  try {
    element.select();
    document.execCommand("copy");
    showToast("Đã copy vào clipboard!", "success");
  } catch (error) {
    showToast("Không thể copy vào clipboard!", "error");
  }
}

// Utility functions
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function showLoading(message = "Đang xử lý...") {
  const loadingMessage = document.getElementById("loading-message");
  const loadingOverlay = document.getElementById("loading-overlay");

  if (loadingMessage) {
    loadingMessage.textContent = message;
  }
  if (loadingOverlay) {
    loadingOverlay.style.display = "flex";
  }
}

function hideLoading() {
  const loadingOverlay = document.getElementById("loading-overlay");
  if (loadingOverlay) {
    loadingOverlay.style.display = "none";
  }
}

function showToast(message, type = "info", duration = 3000) {
  const toastContainer = document.getElementById("toast-container");
  if (!toastContainer) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <i class="fas ${getToastIcon(type)}"></i>
            <span>${message}</span>
        </div>
    `;

  toastContainer.appendChild(toast);

  // Auto remove after duration
  setTimeout(() => {
    toast.style.animation = "slideOut 0.3s ease";
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }, duration);
}

function getToastIcon(type) {
  switch (type) {
    case "success":
      return "fa-check-circle";
    case "error":
      return "fa-exclamation-circle";
    case "warning":
      return "fa-exclamation-triangle";
    default:
      return "fa-info-circle";
  }
}
