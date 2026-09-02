<template>
  <div class="dashboard">
    <!-- 顶部系统标题栏 -->
    <div class="page-banner">
      <h2>智能车间产品外观缺陷检测台</h2>
      <p>上传产品外观图像，AI 自动检测表面缺陷并生成检测报告</p>
    </div>

    <el-row :gutter="16">
      <!-- 左栏：上传 + 检测结果 -->
      <el-col :span="14">
        <el-alert
          v-if="backendDown"
          title="无法连接后端服务"
          description="请双击桌面上的【启动缺陷检测系统】图标启动服务，然后点击右侧的“重新连接”按钮。"
          type="error"
          show-icon
          :closable="false"
          class="conn-alert"
        >
          <template #default>
            <el-button size="small" type="primary" @click="initLoad">重新连接</el-button>
          </template>
        </el-alert>
        <el-alert
          v-else-if="connecting"
          title="正在连接后端服务，请稍候..."
          type="info"
          show-icon
          :closable="false"
          class="conn-alert"
        />
        <UploadArea :loading="uploadLoading" @upload="handleUpload" />
        <div class="gap" />
        <ResultDisplay :result="detectResult" :loading="uploadLoading" />
      </el-col>

      <!-- 右栏：统计看板 + 图表 + 最近记录 -->
      <el-col :span="10">
        <!-- 指标卡片 -->
        <el-row :gutter="12">
          <el-col :span="6" v-for="card in statCards" :key="card.label">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </el-card>
          </el-col>
        </el-row>

        <div class="gap" />
        <StatisticsChart :statistics-data="statistics" />

        <div class="gap" />
        <RecordTable
          :records="records"
          :total="recordsTotal"
          :page="page"
          :size="size"
          :loading="recordsLoading"
          @page-change="onPageChange"
          @row-click="openDetail"
        />
      </el-col>
    </el-row>

    <!-- 记录详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="检测记录详情"
      width="760px"
      top="6vh"
    >
      <div v-if="detailData" v-loading="detailLoading">
        <el-row :gutter="12" class="detail-imgs">
          <el-col :span="12">
            <div class="img-title">原图</div>
            <el-image
              :src="detailData.record.original_image_url"
              fit="contain"
              :preview-src-list="[detailData.record.original_image_url]"
              class="detail-img"
              preview-teleported
            />
          </el-col>
          <el-col :span="12">
            <div class="img-title">检测结果图</div>
            <el-image
              :src="detailData.record.result_image_url"
              fit="contain"
              :preview-src-list="[detailData.record.result_image_url]"
              class="detail-img"
              preview-teleported
            />
          </el-col>
        </el-row>

        <el-descriptions :column="2" border size="small" class="detail-desc">
          <el-descriptions-item label="记录ID">{{ detailData.record.id }}</el-descriptions-item>
          <el-descriptions-item label="文件名">{{ detailData.record.file_name }}</el-descriptions-item>
          <el-descriptions-item label="检测结论">
            <el-tag :type="detailData.record.status === '合格' ? 'success' : 'danger'" size="small">
              {{ detailData.record.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="缺陷总数">{{ detailData.record.total_defects }}</el-descriptions-item>
          <el-descriptions-item label="平均置信度">
            {{ (detailData.record.confidence_avg * 100).toFixed(1) }}%
          </el-descriptions-item>
          <el-descriptions-item label="处理耗时">{{ detailData.record.processing_time }}s</el-descriptions-item>
          <el-descriptions-item label="检测时间">{{ detailData.record.created_at }}</el-descriptions-item>
          <el-descriptions-item label="缺陷类型">
            <el-tag
              v-for="(count, name) in detailData.record.defect_types"
              :key="name"
              size="small"
              :color="DEFECT_COLORS[name]"
              effect="dark"
              class="type-tag"
            >
              {{ name }} × {{ count }}
            </el-tag>
            <span v-if="!Object.keys(detailData.record.defect_types).length">无</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 检测台主页：
 * 左栏上传+结果展示；右栏指标卡片+统计图表+最近记录；点击记录行弹详情。
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import UploadArea from '../components/UploadArea.vue'
import ResultDisplay from '../components/ResultDisplay.vue'
import StatisticsChart from '../components/StatisticsChart.vue'
import RecordTable from '../components/RecordTable.vue'

import { uploadImage } from '../api/detect'
import { getRecordDetail, getRecords, getStatistics } from '../api/records'
import { DEFECT_COLORS } from '../constants'

// ---------- 后端连接状态 ----------
const connecting = ref(false)
const backendDown = ref(false)

// ---------- 上传检测 ----------
const uploadLoading = ref(false)
const detectResult = ref(null)

// ---------- 统计 ----------
const statistics = ref(null)

// ---------- 最近记录 ----------
const records = ref([])
const recordsTotal = ref(0)
const recordsLoading = ref(false)
const page = ref(1)
const size = ref(5)

// ---------- 详情弹窗 ----------
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref(null)

/** 指标卡片（从统计数据计算） */
const statCards = computed(() => {
  const s = statistics.value || {}
  return [
    { label: '总检测数', value: s.total_count ?? 0, color: '#409eff' },
    { label: '合格率', value: `${((s.pass_rate ?? 0) * 100).toFixed(1)}%`, color: '#67c23a' },
    { label: '今日检测', value: s.today_count ?? 0, color: '#e6a23c' },
    { label: '不合格数', value: s.fail_count ?? 0, color: '#f56c6c' },
  ]
})

async function refreshStatistics() {
  try {
    statistics.value = await getStatistics()
  } catch (e) {
    /* 网络错误已由页面连接状态横幅提示 */
  }
}

async function refreshRecords() {
  recordsLoading.value = true
  try {
    const data = await getRecords({ page: page.value, size: size.value })
    records.value = data.items
    recordsTotal.value = data.total
  } catch (e) {
    /* 网络错误已由页面连接状态横幅提示 */
  } finally {
    recordsLoading.value = false
  }
}

/**
 * 带重试的请求：后端可能刚启动还没就绪，
 * 自动重试最多 6 次（每次间隔 2 秒），都失败才判定连接失败
 */
async function fetchWithRetry(fn, retries = 6, delayMs = 2000) {
  let lastErr
  for (let i = 0; i < retries; i++) {
    try {
      return await fn()
    } catch (e) {
      lastErr = e
      if (i < retries - 1) {
        await new Promise((resolve) => setTimeout(resolve, delayMs))
      }
    }
  }
  throw lastErr
}

/** 初始加载：统计 + 最近记录，带自动重连 */
async function initLoad() {
  connecting.value = true
  backendDown.value = false
  try {
    const [stats, recordData] = await Promise.all([
      fetchWithRetry(getStatistics),
      fetchWithRetry(() => getRecords({ page: page.value, size: size.value })),
    ])
    statistics.value = stats
    records.value = recordData.items
    recordsTotal.value = recordData.total
  } catch (e) {
    backendDown.value = true
  } finally {
    connecting.value = false
  }
}

function onPageChange(p) {
  page.value = p
  refreshRecords()
}

/** 上传后自动触发检测 */
async function handleUpload(file) {
  uploadLoading.value = true
  detectResult.value = null
  try {
    const data = await uploadImage(file)
    detectResult.value = data
    ElMessage.success(`检测完成：${data.status}（${data.total_defects} 处缺陷）`)
    // 刷新统计与记录列表
    refreshStatistics()
    refreshRecords()
  } catch (e) {
    detectResult.value = null
    ElMessage.error('上传检测失败，请确认后端服务正在运行（双击桌面【启动缺陷检测系统】图标）')
  } finally {
    uploadLoading.value = false
  }
}

/** 点击记录行 -> 加载详情并弹窗 */
async function openDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detailData.value = null
  try {
    detailData.value = await getRecordDetail(row.id)
  } catch (e) {
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

onMounted(initLoad)
</script>

<style scoped>
.page-banner {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.page-banner h2 { font-size: 20px; color: #1f3a5f; }
.page-banner p { color: #909399; font-size: 13px; margin-top: 4px; }

.gap { height: 16px; }

.conn-alert { margin-bottom: 14px; }

.stat-card { text-align: center; padding: 6px 0; }

.stat-value { font-size: 26px; font-weight: 700; }

.stat-label { color: #909399; font-size: 13px; margin-top: 4px; }

.detail-imgs { margin-bottom: 14px; }

.img-title {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
  font-weight: 600;
}

.detail-img {
  width: 100%;
  height: 220px;
  background: #1a1a1a;
  border-radius: 6px;
}

.type-tag { margin-right: 6px; margin-bottom: 4px; }
</style>
