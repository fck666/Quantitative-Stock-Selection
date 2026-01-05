<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";

const apiBase =
  (import.meta.env.VITE_API_BASE && import.meta.env.VITE_API_BASE.trim() !== ""
    ? import.meta.env.VITE_API_BASE.replace(/\/$/, "")
    : "") || "";

const form = ref({
  symbol: "AAPL",
  start: "2015-01-01",
  forceRefresh: false,
});

const loading = ref(false);
const error = ref("");
const rateLimited = ref(false);
const noData = ref(false);
const cached = ref(false);
const cacheInfo = ref(null);
const latest = ref(null);
const stats = ref(null);
const series = ref([]);

const chartRef = ref(null);
let chartInstance = null;

const statusHint = computed(() => {
  if (rateLimited.value) return "请求过于频繁，请稍后再试。";
  if (error.value) return error.value;
  if (noData.value) return "暂无返回数据，请检查代码或时间区间。";
  if (cached.value) return "命中缓存，响应更快。如需刷新可勾选强制更新。";
  return "";
});

const statBlocks = computed(() => {
  if (!stats.value) return [];
  const s = stats.value;
  return [
    { label: "1M 收益", value: toPercent(s.return_1m) },
    { label: "3M 收益", value: toPercent(s.return_3m) },
    { label: "1Y 收益", value: toPercent(s.return_1y) },
    { label: "年化波动", value: toPercent(s.annual_vol) },
    { label: "最大回撤", value: toPercent(s.max_drawdown) },
    { label: "MA5", value: toFixed(s.ma5) },
    { label: "MA20", value: toFixed(s.ma20) },
    { label: "MA60", value: toFixed(s.ma60) },
  ];
});

const hasSeries = computed(() => series.value && series.value.length > 0);

const toPercent = (v) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(2)}%`;

const toFixed = (v, digits = 2) =>
  v === null || v === undefined ? "—" : Number(v).toFixed(digits);

const fetchTicker = async () => {
  if (!form.value.symbol.trim()) {
    error.value = "请输入股票代码";
    return;
  }

  loading.value = true;
  rateLimited.value = false;
  error.value = "";
  noData.value = false;

  const url = `${apiBase}/ticker/${encodeURIComponent(
    form.value.symbol.trim()
  )}?start=${encodeURIComponent(form.value.start)}&force_refresh=${
    form.value.forceRefresh
  }`;

  try {
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    const payload = await res.json().catch(() => null);

    if (res.status === 429) {
      rateLimited.value = true;
      error.value =
        payload?.detail || "请求受到限频保护，请稍后重试或放慢请求频率。";
      return;
    }

    if (!res.ok) {
      error.value =
        payload?.detail || `请求失败 (${res.status})，请稍后再试。`;
      return;
    }

    series.value = payload?.series ?? [];
    stats.value = payload?.stats ?? null;
    latest.value = payload?.latest ?? null;
    cached.value = Boolean(payload?.cached);
    cacheInfo.value = payload?.cache_path
      ? {
        path: payload.cache_path,
        ttlHours: payload.cache_ttl_hours,
      }
      : null;
    noData.value = !series.value.length;
    updateChart();
  } catch (err) {
    error.value = err?.message || "无法连接到后端服务。";
  } finally {
    loading.value = false;
  }
};

const updateChart = () => {
  if (!chartRef.value) return;
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }

  if (!hasSeries.value) {
    chartInstance?.clear();
    return;
  }

  const dates = series.value.map((d) => d.date);
  const option = {
    backgroundColor: "#ffffff",
    grid: { left: 60, right: 40, top: 50, bottom: 80 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#0f172a",
      textStyle: { color: "#fff" },
    },
    legend: {
      data: ["收盘", "MA5", "MA20", "MA60", "成交量"],
      top: 10,
    },
    dataZoom: [
      { type: "inside", start: 60, end: 100 },
      { type: "slider", start: 60, end: 100, bottom: 20 },
    ],
    xAxis: {
      type: "category",
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "#cbd5e1" } },
    },
    yAxis: [
      {
        type: "value",
        name: "价格",
        scale: true,
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        splitLine: { lineStyle: { color: "#e2e8f0" } },
      },
      {
        type: "value",
        name: "成交量",
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "收盘",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: series.value.map((d) => d.close),
        lineStyle: { width: 2.5, color: "#2563eb" },
      },
      {
        name: "MA5",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: series.value.map((d) => d.ma5),
        lineStyle: { color: "#22c55e", width: 2 },
      },
      {
        name: "MA20",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: series.value.map((d) => d.ma20),
        lineStyle: { color: "#f97316", width: 2 },
      },
      {
        name: "MA60",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: series.value.map((d) => d.ma60),
        lineStyle: { color: "#6b7280", width: 2 },
      },
      {
        name: "成交量",
        type: "bar",
        yAxisIndex: 1,
        data: series.value.map((d) => d.volume),
        itemStyle: { color: "rgba(14,165,233,0.35)" },
      },
    ],
  };

  chartInstance.setOption(option, true);
};

const resetZoom = () => {
  if (!chartInstance) return;
  chartInstance.dispatchAction({
    type: "dataZoom",
    start: 0,
    end: 100,
  });
};

const handleResize = () => {
  chartInstance?.resize();
};

onMounted(() => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value);
  }
  window.addEventListener("resize", handleResize);
  fetchTicker();
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
});

watch(
  () => series.value,
  () => updateChart(),
  { deep: true }
);
</script>

<template>
  <div class="container">
    <header class="section-title" style="margin-bottom: 14px">
      <div>
        <p class="badge info">前后端分离 · Vue 3 + ECharts</p>
        <h1 style="margin: 6px 0 0; font-size: 28px">
          Quantitative Stock Selection
        </h1>
        <p style="margin: 4px 0; color: #475569">
          通过后端 /ticker/{symbol} API 获取分析结果，并展示行情、均线和关键指标。
        </p>
      </div>
      <button class="secondary" type="button" @click="resetZoom" :disabled="!hasSeries || loading">
        重置缩放
      </button>
    </header>

    <div class="grid two" style="margin-bottom: 16px">
      <section class="card">
        <div class="section-title">
          <h2>请求参数</h2>
          <span class="tag">API 基址：{{ apiBase || "/" }}</span>
        </div>
        <form class="grid two" style="margin-top: 12px; gap: 14px" @submit.prevent="fetchTicker">
          <div>
            <label for="symbol">股票代码</label>
            <input
              id="symbol"
              v-model="form.symbol"
              placeholder="如：AAPL"
              autocomplete="off"
            />
          </div>
          <div>
            <label for="start">起始日期</label>
            <input id="start" type="date" v-model="form.start" />
          </div>
          <div style="display: flex; align-items: center; gap: 10px">
            <input
              id="forceRefresh"
              v-model="form.forceRefresh"
              type="checkbox"
              style="width: auto"
            />
            <label for="forceRefresh" style="margin: 0">强制刷新缓存</label>
          </div>
          <div style="display: flex; justify-content: flex-start; align-items: center; gap: 10px">
            <button class="primary" type="submit" :disabled="loading">
              <span v-if="loading">加载中...</span>
              <span v-else>获取数据</span>
            </button>
          </div>
        </form>
        <div v-if="statusHint" class="state-banner" :class="{
          info: cached && !error && !rateLimited,
          error: error || rateLimited,
          success: !error && !rateLimited && cached,
        }">
          {{ statusHint }}
        </div>
        <div v-if="cacheInfo" style="margin-top: 10px; color: #475569; font-size: 14px">
          缓存路径：{{ cacheInfo.path }} · TTL：{{ cacheInfo.ttlHours }} 小时
        </div>
      </section>

      <section class="card">
        <div class="section-title">
          <h2>最新行情</h2>
          <span class="tag" v-if="latest">
            {{ latest.date }} · 收盘 {{ toFixed(latest.close) }}
          </span>
        </div>
        <div class="grid three" style="margin-top: 14px">
          <article class="stat-card" v-for="stat in statBlocks" :key="stat.label">
            <h4>{{ stat.label }}</h4>
            <div class="value">{{ stat.value }}</div>
          </article>
        </div>
        <div v-if="noData" class="state-banner info" style="margin-top: 12px">
          暂无数据可展示，请更换日期或代码。
        </div>
      </section>
    </div>

    <section class="card">
      <div class="section-title">
        <h2>行情与均线</h2>
        <div class="legend-line">
          <span style="background: #2563eb"></span>收盘
          <span style="background: #22c55e"></span>MA5
          <span style="background: #f97316"></span>MA20
          <span style="background: #6b7280"></span>MA60
        </div>
      </div>
      <div class="chart-shell" ref="chartRef"></div>
      <div style="margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap">
        <span class="badge info">支持滚轮/框选缩放</span>
        <span class="badge success">点击「重置缩放」恢复全局</span>
        <span v-if="loading" class="badge warning">加载中...</span>
      </div>
      <div v-if="error && !rateLimited" class="state-banner error" style="margin-top: 12px">
        {{ error }}
      </div>
      <div v-if="rateLimited" class="state-banner warning" style="margin-top: 12px">
        当前请求受到限频，请稍后再试或减少刷新频率。
      </div>
    </section>
  </div>
</template>
