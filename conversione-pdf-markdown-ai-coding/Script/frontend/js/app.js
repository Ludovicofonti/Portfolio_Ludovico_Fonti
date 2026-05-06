// PDF to Markdown - App

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
  const confidenceWarnings = document.getElementById("confidence-warnings");
  const healthBanner = document.getElementById("health-banner");

  // Track multiple jobs
  let jobs = JSON.parse(localStorage.getItem("jobs") || "[]");
  // Legacy single job support
  let currentJobId = localStorage.getItem("currentJobId");

  // Health check on load
  checkHealth();

  // Reconnect to active jobs on reload
  if (jobs.length > 0) {
    showBatchProgress();
    jobs.forEach((j) => {
      if (j.status !== "completed" && j.status !== "failed") {
        subscribeProgress(j.id);
      }
    });
  } else if (currentJobId) {
    fetch(`/api/jobs/${currentJobId}/status`)
      .then((r) => {
        if (!r.ok) {
          localStorage.removeItem("currentJobId");
          return;
        }
        return r.json();
      })
      .then((data) => {
        if (!data) return;
        if (data.status === "completed") {
          jobs = [{ id: currentJobId, fileName: data.file_name, status: "completed" }];
          showPreview(currentJobId);
        } else if (data.status === "processing" || data.status === "queued") {
          jobs = [{ id: currentJobId, fileName: data.file_name, status: data.status }];
          showProgress();
          subscribeProgress(currentJobId);
        }
      })
      .catch(() => localStorage.removeItem("currentJobId"));
  }

  // Drag & drop
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    const files = e.dataTransfer.files;
    if (files.length > 1) {
      uploadFiles(files);
    } else if (files.length === 1) {
      uploadFile(files[0]);
    }
  });
  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 1) {
      uploadFiles(fileInput.files);
    } else if (fileInput.files.length === 1) {
      uploadFile(fileInput.files[0]);
    }
  });

  // Download button (single job)
  downloadBtn.addEventListener("click", () => {
    if (jobs.length === 1 && jobs[0].id) {
      window.location.href = `/api/jobs/${jobs[0].id}/download`;
    } else if (jobs.length > 1) {
      const completedIds = jobs
        .filter((j) => j.status === "completed")
        .map((j) => j.id);
      if (completedIds.length > 0) {
        const params = completedIds.map((id) => `job_ids=${id}`).join("&");
        window.location.href = `/api/jobs/batch/download?${params}`;
      }
    } else if (currentJobId) {
      window.location.href = `/api/jobs/${currentJobId}/download`;
    }
  });

  async function uploadFile(file) {
    hideError();
    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json();
        showError(err.detail || "Upload failed.");
        return;
      }
      const data = await resp.json();
      currentJobId = data.job_id;
      localStorage.setItem("currentJobId", currentJobId);
      jobs = [{ id: data.job_id, fileName: file.name, status: "queued" }];
      saveJobs();
      showProgress();
      subscribeProgress(data.job_id);
    } catch (e) {
      showError("Upload failed. Please try again.");
    }
  }

  async function uploadFiles(fileList) {
    hideError();
    const formData = new FormData();
    for (const file of fileList) {
      formData.append("files", file);
    }

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
      jobs = data.job_ids.map((id, i) => ({
        id,
        fileName: fileList[i].name,
        status: "queued",
      }));
      saveJobs();
      showBatchProgress();
      data.job_ids.forEach((id) => subscribeProgress(id));
    } catch (e) {
      showError("Upload failed. Please try again.");
    }
  }

  function subscribeProgress(jobId) {
    const es = new EventSource(`/api/jobs/${jobId}/progress`);
    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      updateJobStatus(jobId, data);
      if (data.status === "completed") {
        es.close();
        checkAllDone();
      } else if (data.status === "failed") {
        es.close();
        updateJobStatus(jobId, { status: "failed" });
        checkAllDone();
      }
    };
    es.onerror = () => {
      es.close();
    };
  }

  function updateJobStatus(jobId, data) {
    const job = jobs.find((j) => j.id === jobId);
    if (job) {
      job.status = data.status;
      job.current_page = data.current_page || 0;
      job.total_pages = data.total_pages || 0;
      saveJobs();
    }
    renderProgress();
  }

  function renderProgress() {
    if (jobs.length === 1) {
      const job = jobs[0];
      const current = job.current_page || 0;
      const total = job.total_pages || 1;
      const pct = total > 0 ? Math.round((current / total) * 100) : 0;
      progressBar.style.width = pct + "%";
      if (total > 0 && current > 0) {
        progressText.textContent = `Processing page ${current} of ${total}`;
      } else {
        progressText.textContent = "Preparing...";
      }
    } else {
      // Batch: show aggregate
      const done = jobs.filter(
        (j) => j.status === "completed" || j.status === "failed"
      ).length;
      const pct = Math.round((done / jobs.length) * 100);
      progressBar.style.width = pct + "%";
      progressText.textContent = `Completed ${done} of ${jobs.length} files`;
    }
  }

  function checkAllDone() {
    const allDone = jobs.every(
      (j) => j.status === "completed" || j.status === "failed"
    );
    if (allDone) {
      const completed = jobs.filter((j) => j.status === "completed");
      if (completed.length === 1) {
        showPreview(completed[0].id);
      } else if (completed.length > 1) {
        showBatchResults();
      } else {
        showError("All conversions failed. Please try again.");
      }
    }
  }

  async function showPreview(jobId) {
    try {
      const resp = await fetch(`/api/jobs/${jobId}/preview`);
      if (!resp.ok) return;
      const data = await resp.json();
      markdownPreview.textContent = data.content;

      confidenceWarnings.innerHTML = "";
      if (data.confidence_warnings && data.confidence_warnings.length > 0) {
        data.confidence_warnings.forEach((w) => {
          const div = document.createElement("div");
          div.className = "warning";
          div.textContent = `Page ${w.page}: ${w.warning}`;
          confidenceWarnings.appendChild(div);
        });
      }

      uploadSection.classList.add("hidden");
      progressSection.classList.add("hidden");
      previewSection.classList.remove("hidden");
      downloadBtn.textContent =
        jobs.length > 1 ? "Download All (.zip)" : "Download .md";
    } catch (e) {
      // ignore
    }
  }

  function showBatchResults() {
    // Show a list of completed files with individual download links
    const completed = jobs.filter((j) => j.status === "completed");
    let html = "";
    completed.forEach((j) => {
      html += `<div class="batch-result">
        <span>${escapeHtml(j.fileName)}</span>
        <a href="/api/jobs/${j.id}/download" class="btn btn-small">Download</a>
      </div>`;
    });
    markdownPreview.innerHTML = html;
    confidenceWarnings.innerHTML = "";

    uploadSection.classList.add("hidden");
    progressSection.classList.add("hidden");
    previewSection.classList.remove("hidden");
    downloadBtn.textContent = "Download All (.zip)";
  }

  function showProgress() {
    uploadSection.classList.add("hidden");
    previewSection.classList.add("hidden");
    errorSection.classList.add("hidden");
    progressSection.classList.remove("hidden");
    progressBar.style.width = "0%";
    progressText.textContent = "Preparing...";
  }

  function showBatchProgress() {
    showProgress();
    renderProgress();
  }

  function showError(msg) {
    errorMessage.textContent = msg;
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
    localStorage.setItem("jobs", JSON.stringify(jobs));
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

  async function checkHealth() {
    try {
      const resp = await fetch("/api/health");
      const data = await resp.json();
      if (data.status === "degraded" || !data.ollama_available) {
        healthBanner.textContent =
          "OCR service is currently unavailable. Please ensure Ollama is running.";
        healthBanner.classList.remove("hidden");
      } else {
        healthBanner.classList.add("hidden");
      }
    } catch {
      healthBanner.textContent = "Could not connect to the server.";
      healthBanner.classList.remove("hidden");
    }
  }
})();