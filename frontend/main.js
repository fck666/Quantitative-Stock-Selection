import Chart from "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js";
import zoomPlugin from "https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js";

Chart.register(zoomPlugin);

const form = document.getElementById("queryForm");
const symbolInput = document.getElementById("symbol");
const startInput = document.getElementById("start");
const apiBaseInput = document.getElementById("apiBase");
const forceRefreshInput = document.getElementById("forceRefresh");
const statusEl = document.getElementById("status");
const cacheInfoEl = document.getElementById("cacheInfo");
const statsGrid = document.getElementById("statsGrid");
const latestInfoEl = document.getElementById("latestInfo");
const chartPlaceholder = document.getElementById("chartPlaceholder");
const errorMsg = document.getElementById("errorMsg");
const resetZoomBtn = document.getElementById("resetZoom");

let priceChart;

function getDefaultApiBase() {
  return `${window.location.origin}/ticker`;
}

function setStatus(text, tone = "muted") {
  statusEl.textContent = text;
  statusEl.className = `status ${tone}`;
}

function setCacheInfo(text) {
  cacheInfoEl.textContent = text;
}

function formatPercent(val) {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  return `${(val * 100).toFixed(2)}%`;
}

function formatNumber(val) {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  return Number(val).toFixed(2);
}

function renderStats(stats) {
  const values = [
    formatPercent(stats.return_1m),
    formatPercent(stats.return_3m),
    formatPercent(stats.return_1y),
    formatPercent(stats.annual_vol),
    formatPercent(stats.max_drawdown),
    formatNumber(stats.ma5),
    formatNumber(stats.ma20),
    formatNumber(stats.ma60),
  ];

  statsGrid.querySelectorAll(".value").forEach((node, idx) => {
    node.textContent = values[idx] ?? "—";
  });
}

function renderLatest(latest, ticker) {
  if (!latest || !latest.date) {
    latestInfoEl.textContent = "暂无最新价格信息。";
    return;
  }
  latestInfoEl.textContent = `${ticker} | 最新 ${latest.date} 收盘价：${formatNumber(latest.close)}`;
}

function renderCache(payload) {
  if (payload.cached) {
    setCacheInfo(
      `命中缓存：${payload.cache_path}（TTL：${payload.cache_ttl_hours} 小时）。如需强制刷新，请勾选“强制刷新”。`
    );
  } else {
    setCacheInfo(
      `未命中缓存，已从后端拉取最新数据。缓存文件：${payload.cache_path}，TTL：${payload.cache_ttl_hours} 小时。`
    );
  }
}

function buildChart(series) {
  const ctx = document.getElementById("priceChart").getContext("2d");
  const labels = series.map((row) => row.date);
  const closeData = series.map((row) => row.close);
  const ma5Data = series.map((row) => row.ma5);
  const ma20Data = series.map((row) => row.ma20);
  const ma60Data = series.map((row) => row.ma60);
  const volumeData = series.map((row) => row.volume);

  const datasets = [
    {
      label: "收盘价",
      data: closeData,
      borderColor: "#2563eb",
      backgroundColor: "rgba(37, 99, 235, 0.05)",
      tension: 0.2,
      pointRadius: 0,
      borderWidth: 2,
      yAxisID: "y",
    },
    {
      label: "MA5",
      data: ma5Data,
      borderColor: "#22c55e",
      backgroundColor: "rgba(34, 197, 94, 0.08)",
      tension: 0.2,
      pointRadius: 0,
      borderWidth: 1.5,
      yAxisID: "y",
    },
    {
      label: "MA20",
      data: ma20Data,
      borderColor: "#f59e0b",
      backgroundColor: "rgba(245, 158, 11, 0.08)",
      tension: 0.2,
      pointRadius: 0,
      borderWidth: 1.4,
      yAxisID: "y",
    },
    {
      label: "MA60",
      data: ma60Data,
      borderColor: "#8b5cf6",
      backgroundColor: "rgba(139, 92, 246, 0.08)",
      tension: 0.2,
      pointRadius: 0,
      borderWidth: 1.4,
      yAxisID: "y",
    },
    {
      type: "bar",
      label: "成交量",
      data: volumeData,
      backgroundColor: "rgba(100, 116, 139, 0.25)",
      borderWidth: 0,
      yAxisID: "y1",
    },
  ];

  return new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          position: "bottom",
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              if (context.dataset.yAxisID === "y1") {
                return `${context.dataset.label}: ${context.raw ?? "—"}`;
              }
              return `${context.dataset.label}: ${formatNumber(context.raw)}`;
            },
          },
        },
        zoom: {
          limits: {
            x: { minRange: 10 },
          },
          pan: {
            enabled: true,
            mode: "x",
          },
          zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: "x",
          },
        },
      },
      scales: {
        x: {
          ticks: { maxRotation: 0, autoSkipPadding: 12 },
        },
        y: {
          title: { display: true, text: "价格" },
          grid: { drawOnChartArea: true },
        },
        y1: {
          title: { display: true, text: "成交量" },
          position: "right",
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

function renderChart(series) {
  if (priceChart) {
    priceChart.destroy();
  }

  if (!series || series.length === 0) {
    chartPlaceholder.textContent = "无数据可展示。";
    chartPlaceholder.hidden = false;
    return;
  }

  chartPlaceholder.hidden = true;
  priceChart = buildChart(series);
}

async function fetchTicker(symbol, start, apiBase, forceRefresh) {
  const sanitizedBase = apiBase.replace(/\/$/, "");
  const url = new URL(`${sanitizedBase}/${encodeURIComponent(symbol)}`);
  if (start) {
    url.searchParams.append("start", start);
  }
  if (forceRefresh) {
    url.searchParams.append("force_refresh", "true");
  }

  setStatus("加载中…", "muted");
  errorMsg.hidden = true;
  errorMsg.textContent = "";

  try {
    const res = await fetch(url.toString());
    if (!res.ok) {
      if (res.status === 429) {
        throw new Error("请求过于频繁，触发限频保护，请稍后重试。");
      }
      const detail = await res.text();
      throw new Error(detail || `请求失败，状态码 ${res.status}`);
    }
    const payload = await res.json();
    setStatus("加载完成！", "cache");
    renderCache(payload);
    renderStats(payload.stats ?? {});
    renderLatest(payload.latest, payload.ticker);
    renderChart(payload.series || []);
  } catch (err) {
    setStatus("请求失败", "error");
    errorMsg.hidden = false;
    errorMsg.textContent = err?.message || "获取数据时出现未知错误。";
    renderChart([]);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const symbol = symbolInput.value.trim();
  if (!symbol) {
    setStatus("请输入股票代码。", "error");
    return;
  }

  fetchTicker(symbol, startInput.value, apiBaseInput.value, forceRefreshInput.checked);
});

resetZoomBtn.addEventListener("click", () => {
  if (priceChart) {
    priceChart.resetZoom();
  }
});

window.addEventListener("DOMContentLoaded", () => {
  symbolInput.value = "AAPL";
  apiBaseInput.value = getDefaultApiBase();
});
