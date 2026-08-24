// PDF to Markdown - privacy-first client

(function () {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const uploadSection = document.getElementById("upload-section");
  const errorSection = document.getElementById("error-section");
  const errorMessage = document.getElementById("error-message");
  const progressSection = document.getElementById("progress-section");
  const progressBar = document.getElementById("progress-bar");
  const progressText = document.getElementById("progress-text");
  const previewSection = document.getElementById("preview-section");
  const markdownPreview = document.getElementById("markdown-preview");
  const downloadBtn = document.getElementById("download-btn");
  const resetBtn = document.getElementById("reset-btn");
  const errorResetBtn = document.getElementById("error-reset-btn");
  const confidenceWarnings = document.getElementById("confidence-warnings");
  const healthBanner = document.getElementById("health-banner");
  const privacyNote = document.getElementById("privacy-note");

  // Remove legacy persistent metadata. Results are never stored in the browser.
  localStorage.removeItem("jobs");
  localStorage.removeItem("currentJobId");

  let jobs = loadSessionJobs();
  checkHealth();
  restoreJobs();

  function loadSessionJobs() {
    try {
      const parsed = JSON.parse(sessionStorage.getItem("jobs") || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      sessionStorage.removeItem("jobs");
      return [];
    }
  }

  async function restoreJobs() {
    if (jobs.length === 0) return;

    const restored = [];
    for (const job of jobs) {
      try {
        const resp = await fetch(`/api/jobs/${job.id}/status`, {
          cache: "no-store",
        });
        if (!resp.ok) continue;
        const data = await resp.json();
        restored.push({
          ...job,
          fileName: data.file_name,
          status: data.status,
          current_page: data.current_page,
          total_pages: data.total_pages,
          active_page: data.active_page,
          stage: data.stage,
          error_message: data.error_message,
        });
      } catch {
        restored.push(job);
      }
    }

    jobs = restored;
    saveJobs();
    if (jobs.length === 0) {
      resetInterface();
      return;
    }

    showProgress();
    jobs.forEach((job) => {
      if (job.status === "queued" || job.status === "processing") {
        subscribeProgress(job.id);
      }
    });
    checkAllDone();
  }

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });
  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
    handleFiles(event.dataTransfer.files);
  });
  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => handleFiles(fileInput.files));

  function handleFiles(fileList) {
    if (fileList.length > 1) uploadFiles(fileList);
    else if (fileList.length === 1) uploadFile(fileList[0]);
  }

  downloadBtn.addEventListener("click", () => {
    const completedIds = jobs
      .filter((job) => job.status === "completed")
      .map((job) => job.id);
    if (completedIds.length === 1) {
      window.location.href = `/api/jobs/${completedIds[0]}/download`;
    } else if (completedIds.length > 1) {
      const params = completedIds.map((id) => `job_ids=${id}`).join("&");
      window.location.href = `/api/jobs/batch/download?${params}`;
    }
  });
  resetBtn.addEventListener("click", resetAllJobs);
  errorResetBtn.addEventListener("click", resetAllJobs);

  async function uploadFile(file) {
    await resetAllJobs(false);
    hideError();
    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch("/api/upload", { method: "POST", body: formData });
      if (!resp.ok) {
        const err = await resp.json();
        showError(err.detail || "Upload failed.");
        return;
      }
      const data = await resp.json();
      jobs = [{ id: data.job_id, fileName: file.name, status: "queued" }];
      saveJobs();
      showProgress();
      subscribeProgress(data.job_id);
    } catch {
      showError("Upload failed. Please verify that the local server is running.");
    }
  }

  async function uploadFiles(fileList) {
    await resetAllJobs(false);
    hideError();
    const formData = new FormData();
    for (const file of fileList) formData.append("files", file);

    try {
      const resp = await fetch("/api/upload/batch", {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json();
        showError(err.detail || "Upload failed.");
        return;
      }
      const data = await resp.json();
      jobs = data.job_ids.map((id, index) => ({
        id,
        fileName: fileList[index].name,
        status: "queued",
      }));
      saveJobs();
      showProgress();
      jobs.forEach((job) => subscribeProgress(job.id));
    } catch {
      showError("Upload failed. Please verify that the local server is running.");
    }
  }

  function subscribeProgress(jobId) {
    const es = new EventSource(`/api/jobs/${jobId}/progress`);
    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      updateJobStatus(jobId, data);
      if (data.status === "completed" || data.status === "failed") {
        es.close();
        checkAllDone();
      }
    };
    es.onerror = async () => {
      es.close();
      await reconcileJob(jobId);
    };
  }

  async function reconcileJob(jobId) {
    try {
      const resp = await fetch(`/api/jobs/${jobId}/status`, { cache: "no-store" });
      if (resp.status === 404) {
        jobs = jobs.filter((job) => job.id !== jobId);
        saveJobs();
        showError("The previous local job no longer exists. Start a new conversion.");
        return;
      }
      if (!resp.ok) throw new Error("status unavailable");
      const data = await resp.json();
      updateJobStatus(jobId, data);
      if (data.status === "queued" || data.status === "processing") {
        setTimeout(() => subscribeProgress(jobId), 1000);
      } else {
        checkAllDone();
      }
    } catch {
      showError("Connection to the local server was interrupted.");
    }
  }

  function updateJobStatus(jobId, data) {
    const job = jobs.find((item) => item.id === jobId);
    if (!job) return;
    job.status = data.status;
    job.current_page = data.current_page || 0;
    job.total_pages = data.total_pages || 0;
    job.active_page = data.active_page || 0;
    job.stage = data.stage || "queued";
    job.error_message = data.error_message || null;
    saveJobs();
    renderProgress();
  }

  function renderProgress() {
    if (jobs.length === 1) {
      const job = jobs[0];
      const current = job.current_page || 0;
      const total = job.total_pages || 1;
      const active = job.active_page || Math.min(current + 1, total);
      progressBar.style.width = `${Math.round((current / total) * 100)}%`;
      const labels = {
        queued: "Waiting for the local CPU worker...",
        extracting: `Reading page ${active} of ${total} locally...`,
        ocr: `Local OCR on page ${active} of ${total}...`,
        assembling: "Assembling Markdown in memory...",
      };
      progressText.textContent = labels[job.stage] || "Preparing...";
    } else {
      const done = jobs.filter(
        (job) => job.status === "completed" || job.status === "failed"
      ).length;
      progressBar.style.width = `${Math.round((done / jobs.length) * 100)}%`;
      progressText.textContent = `Completed ${done} of ${jobs.length} files; OCR runs one at a time.`;
    }
  }

  function checkAllDone() {
    if (jobs.length === 0) return;
    const allDone = jobs.every(
      (job) => job.status === "completed" || job.status === "failed"
    );
    if (!allDone) return;

    const completed = jobs.filter((job) => job.status === "completed");
    const failures = jobs.filter((job) => job.status === "failed");
    if (failures.length > 0) {
      const details = failures
        .map((job) => `${job.fileName}: ${job.error_message || "conversion failed"}`)
        .join("\n");
      if (completed.length === 0) {
        showError(details);
        return;
      }
      confidenceWarnings.textContent = details;
    }
    if (completed.length === 1) showPreview(completed[0].id);
    else showBatchResults();
  }

  async function showPreview(jobId) {
    try {
      const resp = await fetch(`/api/jobs/${jobId}/preview`, { cache: "no-store" });
      if (!resp.ok) throw new Error("preview unavailable");
      const data = await resp.json();
      markdownPreview.textContent = data.content;
      confidenceWarnings.innerHTML = "";
      for (const warning of data.confidence_warnings || []) {
        const div = document.createElement("div");
        div.className = "warning";
        div.textContent = `Page ${warning.page}: ${warning.warning}`;
        confidenceWarnings.appendChild(div);
      }
      showPreviewSection();
      downloadBtn.textContent = "Download .md";
    } catch {
      showError("The Markdown preview is no longer available in local memory.");
    }
  }

  function showBatchResults() {
    const completed = jobs.filter((job) => job.status === "completed");
    markdownPreview.innerHTML = completed
      .map(
        (job) => `<div class="batch-result">
          <span>${escapeHtml(job.fileName)}</span>
          <a href="/api/jobs/${job.id}/download" class="btn btn-small">Download</a>
        </div>`
      )
      .join("");
    showPreviewSection();
    downloadBtn.textContent = "Download All (.zip)";
  }

  function showPreviewSection() {
    uploadSection.classList.add("hidden");
    progressSection.classList.add("hidden");
    errorSection.classList.add("hidden");
    previewSection.classList.remove("hidden");
  }

  function showProgress() {
    uploadSection.classList.add("hidden");
    previewSection.classList.add("hidden");
    errorSection.classList.add("hidden");
    progressSection.classList.remove("hidden");
    renderProgress();
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorSection.classList.remove("hidden");
    progressSection.classList.add("hidden");
    previewSection.classList.add("hidden");
    uploadSection.classList.remove("hidden");
  }

  function hideError() {
    errorSection.classList.add("hidden");
    errorMessage.textContent = "";
  }

  function saveJobs() {
    sessionStorage.setItem("jobs", JSON.stringify(jobs));
  }

  async function resetAllJobs(showUpload = true) {
    const ids = jobs.map((job) => job.id);
    jobs = [];
    sessionStorage.removeItem("jobs");
    await Promise.allSettled(
      ids.map((id) => fetch(`/api/jobs/${id}`, { method: "DELETE" }))
    );
    if (showUpload) resetInterface();
  }

  function resetInterface() {
    fileInput.value = "";
    markdownPreview.textContent = "";
    confidenceWarnings.textContent = "";
    progressBar.style.width = "0%";
    hideError();
    progressSection.classList.add("hidden");
    previewSection.classList.add("hidden");
    uploadSection.classList.remove("hidden");
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

  async function checkHealth() {
    try {
      const resp = await fetch("/api/health", { cache: "no-store" });
      const data = await resp.json();
      healthBanner.classList.remove("hidden", "success");
      if (data.status === "healthy" && data.privacy_mode === "local-only") {
        healthBanner.textContent = `Privacy mode active: ${data.model} runs only on this computer.`;
        healthBanner.classList.add("success");
        privacyNote.textContent =
          "I documenti restano in memoria e vengono elaborati esclusivamente sul dispositivo.";
      } else {
        healthBanner.textContent =
          data.error_message ||
          "Local OCR is unavailable. PDFs with an existing text layer can still be converted.";
        if (data.privacy_mode !== "local-only") {
          privacyNote.textContent =
            "Attenzione: è stato abilitato esplicitamente un endpoint OCR remoto.";
        }
      }
    } catch {
      healthBanner.textContent = "Could not connect to the local server.";
      healthBanner.classList.remove("hidden", "success");
    }
  }
})();
