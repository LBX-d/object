<template>
  <el-card shadow="hover">
    <template #header>
      <div class="card-title">📊 统计分析</div>
    </template>
    <el-row :gutter="12">
      <el-col :span="8">
        <div ref="gaugeRef" class="chart-box"></div>
      </el-col>
      <el-col :span="8">
        <div ref="pieRef" class="chart-box"></div>
      </el-col>
      <el-col :span="8">
        <div ref="lineRef" class="chart-box"></div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup>
/**
 * 统计图表组件：三个 ECharts 图
 * - 合格率环形仪表盘（gauge）
 * - 缺陷类型分布饼图（pie）
 * - 近七天检测趋势折线图（line）
 */
import * as echarts from 'echarts'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { DEFECT_COLORS } from '../constants'

const props = defineProps({
  /** 后端统计总览数据（StatisticsResponse 结构） */
  statisticsData: { type: Object, default: null },
})

const gaugeRef = ref(null)
const pieRef = ref(null)
const lineRef = ref(null)
let charts = []

/** 合格率环形仪表盘 */
function renderGauge(el, data) {
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: '检测合格率', left: 'center', top: 4, textStyle: { fontSize: 13, color: '#303133' } },
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 100,
        radius: '95%',
        center: ['50%', '68%'],
        progress: { show: true, width: 14, itemStyle: { color: '#409eff' } },
        axisLine: { lineStyle: { width: 14, color: [[1, '#e5e9f2']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        detail: {
          valueAnimation: true,
          formatter: '{value}%',
          fontSize: 24,
          fontWeight: 'bold',
          color: '#303133',
          offsetCenter: [0, '45%'],
        },
        data: [{ value: +(data.pass_rate * 100).toFixed(1) }],
      },
    ],
  })
  return chart
}

/** 缺陷类型分布饼图 */
function renderPie(el, data) {
  const entries = Object.entries(data.defect_distribution || {})
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: '缺陷类型分布', left: 'center', top: 4, textStyle: { fontSize: 13, color: '#303133' } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} 处 ({d}%)' },
    legend: { bottom: 0, type: 'scroll', itemWidth: 12, itemHeight: 12, textStyle: { fontSize: 11 } },
    series: [
      {
        type: 'pie',
        radius: ['32%', '62%'],
        center: ['50%', '46%'],
        avoidLabelOverlap: true,
        label: { fontSize: 11, formatter: '{b}\n{c}处' },
        data: entries.map(([name, value]) => ({
          name,
          value,
          itemStyle: { color: DEFECT_COLORS[name] || '#909399' },
        })),
      },
    ],
  })
  return chart
}

/** 近七天检测趋势折线图 */
function renderLine(el, data) {
  const trend = data.daily_trend || []
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: '近七天检测趋势', left: 'center', top: 4, textStyle: { fontSize: 13, color: '#303133' } },
    tooltip: { trigger: 'axis' },
    grid: { left: 36, right: 16, top: 38, bottom: 26 },
    xAxis: {
      type: 'category',
      data: trend.map((d) => d.date.slice(5)),
      axisLabel: { fontSize: 11 },
    },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { fontSize: 11 } },
    series: [
      {
        type: 'line',
        smooth: true,
        symbolSize: 6,
        lineStyle: { color: '#409eff', width: 2 },
        itemStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64,158,255,0.12)' },
        data: trend.map((d) => d.count),
      },
    ],
  })
  return chart
}

function renderAll() {
  const data = props.statisticsData
  if (!data) return
  nextTick(() => {
    charts.forEach((c) => c.dispose())
    charts = []
    if (gaugeRef.value) charts.push(renderGauge(gaugeRef.value, data))
    if (pieRef.value) charts.push(renderPie(pieRef.value, data))
    if (lineRef.value) charts.push(renderLine(lineRef.value, data))
  })
}

function handleResize() {
  charts.forEach((c) => c.resize())
}

onMounted(() => {
  renderAll()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  charts.forEach((c) => c.dispose())
})

// 统计数据变化时重绘
watch(() => props.statisticsData, renderAll, { deep: true })
</script>

<style scoped>
.chart-box { height: 220px; width: 100%; }
</style>
