(function () {
  const state = {
    activeJob: null,
    pollTimer: null,
    selectedReport: null,
    selectedModel: "models/cantilever.yaml",
  };

  const projectName = document.getElementById("project-name");
  const projectTree = document.getElementById("project-tree");
  const viewerFrame = document.getElementById("viewer-frame");
  const jobLog = document.getElementById("job-log");
  const jobStatus = document.getElementById("job-status");
  const modelPath = document.getElementById("model-path");
  const measurementPath = document.getElementById("measurement-path");

  function queryParams() {
    return new URLSearchParams(window.location.search);
  }

  function viewerUrl(reportPath, modelPathValue) {
    const params = new URLSearchParams();
    if (reportPath) params.set("file", reportPath);
    if (modelPathValue) params.set("model", modelPathValue);
    const suffix = params.toString();
    return `/index.html${suffix ? `?${suffix}` : ""}`;
  }

  async function api(path, options) {
    const response = await fetch(path, options);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    return payload;
  }

  function appendLog(text) {
    jobLog.textContent = `${jobLog.textContent}\n${text}`.trim();
    jobLog.scrollTop = jobLog.scrollHeight;
  }

  function setStatus(status) {
    if (!status) {
      jobStatus.textContent = "";
      return;
    }
    jobStatus.innerHTML = `<span class="status-pill ${status}">${status}</span>`;
  }

  async function loadProject() {
    const info = await api("/api/project");
    projectName.textContent = info.name || "OpenFEMLab Project";
    if (info.paths && info.paths.models) {
      const sample = `${info.paths.models}/cantilever.yaml`;
      if (!modelPath.value) modelPath.value = sample;
    }
  }

  async function loadTree(relative) {
    const listing = await api(`/api/list?path=${encodeURIComponent(relative || ".")}`);
    projectTree.innerHTML = "";
    if (listing.type === "file") {
      renderFileButton(listing.path, listing.name);
      return;
    }
    (listing.entries || []).forEach((entry) => {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.textContent = entry.name;
      button.className = entry.type === "directory" ? "dir" : "file";
      button.addEventListener("click", () => {
        document.querySelectorAll("#project-tree button").forEach((node) => {
          node.classList.remove("active");
        });
        button.classList.add("active");
        if (entry.type === "directory") {
          loadTree(entry.path);
          return;
        }
        openFile(entry.path);
      });
      item.appendChild(button);
      projectTree.appendChild(item);
    });
  }

  function renderFileButton(path, name) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.textContent = name;
    button.className = "file active";
    button.addEventListener("click", () => openFile(path));
    item.appendChild(button);
    projectTree.appendChild(item);
  }

  function openFile(path) {
    const lower = path.toLowerCase();
    if (lower.endsWith(".yaml") || lower.endsWith(".yml") || lower.endsWith(".json")) {
      if (lower.includes("models/") || lower.endsWith(".yaml") || lower.endsWith(".yml")) {
        if (!lower.endsWith(".json")) {
          modelPath.value = path;
          state.selectedModel = path;
        }
      }
    }
    if (lower.endsWith(".json")) {
      state.selectedReport = path;
      viewerFrame.src = viewerUrl(path, state.selectedModel || modelPath.value);
      appendLog(`已打开报告：${path}`);
    }
  }

  async function runWorkflow(workflow, extra) {
    const payload = Object.assign(
      {
        workflow,
        model: modelPath.value,
        measurement: measurementPath.value,
      },
      extra || {}
    );
    document.querySelectorAll("[data-workflow]").forEach((button) => {
      button.classList.add("running");
    });
    jobLog.textContent = `启动工作流：${workflow}\n`;
    setStatus("running");
    let job;
    try {
      job = await api("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (error) {
      appendLog(`错误：${error.message}`);
      setStatus("failed");
      clearRunning();
      throw error;
    }
    state.activeJob = job.id;
    await waitForJob(job.id, job.outputs || []);
  }

  function waitForJob(jobId, outputs) {
    return new Promise((resolve, reject) => {
      if (state.pollTimer) window.clearInterval(state.pollTimer);
      state.pollTimer = window.setInterval(async () => {
        try {
          const job = await api(`/api/job?id=${encodeURIComponent(jobId)}`);
          jobLog.textContent = job.log.join("\n") || "(无输出)";
          jobLog.scrollTop = jobLog.scrollHeight;
          if (job.status === "running") {
            setStatus("running");
            return;
          }
          window.clearInterval(state.pollTimer);
          state.pollTimer = null;
          clearRunning();
          setStatus(job.status);
          if (job.status === "success") {
            const report = outputs.find((path) => path.endsWith(".json")) || outputs[0];
            if (report) {
              state.selectedReport = report;
              viewerFrame.src = viewerUrl(report, modelPath.value);
            }
            loadTree(".");
            resolve(job);
            return;
          }
          reject(new Error(job.error || "job failed"));
        } catch (error) {
          window.clearInterval(state.pollTimer);
          clearRunning();
          setStatus("failed");
          reject(error);
        }
      }, 500);
    });
  }

  function clearRunning() {
    document.querySelectorAll("[data-workflow]").forEach((button) => {
      button.classList.remove("running");
    });
  }

  document.querySelectorAll("[data-workflow]").forEach((button) => {
    button.addEventListener("click", () => runWorkflow(button.dataset.workflow));
  });

  document.getElementById("refresh-tree").addEventListener("click", () => loadTree("."));

  document.getElementById("run-pipeline").addEventListener("click", async () => {
    try {
      await runWorkflow("modal", { output: "reports/modes.json" });
      await runWorkflow("correlate", { output: "reports/corr.json" });
    } catch (error) {
      appendLog(`闭环失败：${error.message}`);
    }
  });

  const presetFile = queryParams().get("file");
  const presetModel = queryParams().get("model");
  if (presetModel) {
    modelPath.value = presetModel;
    state.selectedModel = presetModel;
  }
  if (presetFile) {
    state.selectedReport = presetFile;
    viewerFrame.src = viewerUrl(presetFile, state.selectedModel);
  }

  loadProject()
    .then(() => loadTree("."))
    .catch((error) => {
      projectName.textContent = "项目加载失败";
      appendLog(error.message);
    });
})();
