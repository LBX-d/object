<template>
  <div class="history">
    <div class="page-banner">
      <h2>历史检测记录</h2>
      <p>支持按缺陷类型、日期范围筛选，点击"查看详情"获取完整检测报告</p>
    </div>

    <!-- 筛选条件 -->
    <el-card shadow="hover" class="filter-card">
      <div class="filter-row">
        <div class="filter-item">
          <span class="filter-label">缺陷类型</span>
          <el-select
            v-model="filters.defect_type"
            placeholder="全部类型"
            clearable
            style="width: 160px"
          >
            <el-option v-for="t in DEFECT_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">检测日期</span>
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 280px"
          />
        </div>
        <el-button type="primary" @click="onSearch">查询</el-button>
        <el-button @click="onReset">重置</el-button>
      </div>
    </el-card>

    <!-- 后端连接状态 -->
    <el-alert
      v-if="backendDown"
      title="无法连接后端服务"
      description="请双击桌面上的【启动缺陷检测系统】图标启动服务，然后点击“重新连接”。"
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

    <!-- 记录表格 -->
    <el-card shadow="hover">
      <el-table :data="records" border stripe v-loading="loading" class="record-table">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="file_name" label="文件名" min-width="160" show-overflow-tooltip />
        <el-table-column prop="total_defects" label="缺陷总数" width="90" align="center" />
        <el-table-column label="缺陷类型" min-width="180">
          <template #default="{ row }">
            <el-tag
              v-for="(count, name) in row.defect_types"
              :key="name"
              size="small"
              :color="DEFECT_COLORS[name]"
              effect="dark"
              class="type-tag"
            >
              {{ name }} × {{ count }}
            </el-tag>
            <span v-if="!Object.keys(row.defect_types).length" class="no-defect">—</span>
          </template>
        </el-table-column>
        <el-table-column label="检测结论" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === '合格' ? 'success' : 'danger'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="检测时间" width="165" />
        <el-table-column label="操作" width="110" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pagination"
        background
        layout="total, prev, pager, next, sizes"
        :total="total"
        :page-size="size"
        :current-page="page"
        :page-sizes="[10, 20, 50]"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </el-card>

    <!-- 详情抽屉：完整检测报告 -->
    <el-drawer
      v-model="drawerVisible"
      title="完整检测报告"
      size="52%"
      destroy-on-close
    >
      <div v-loading="detailLoading">
        <template v-if="detail">
          <!-- 结论横幅 -->
          <div class="report-conclusion" :class="detail.record.status === '合格' ? 'pass' : 'fail'">
            <span class="conclusion-text">
              {{ detail.record.status === '合格' ? '✅ 检测合格' : `❌ 检测不合格（${detail.record.total_defects} 处缺陷）` }}
            </span>
            <span v-if="detail.report?.conclusion?.processing_time" class="meta">
              耗时 {{ detail.report.conclusion.processing_time }}s
            </span>
          </div>

          <!-- 图像对比 -->
          <el-row :gutter="10" class="report-imgs">
            <el-col :span="12">
              <div class="img-title">原图</div>
              <el-image
                :src="detail.record.original_image_url"
                fit="contain"
                :preview-src-list="[detail.record.original_image_url]"
                class="report-img"
                preview-teleported
              />
            </el-col>
            <el-col :span="12">
              <div class="img-title">检测结果图</div>
              <el-image
                :src="detail.record.result_image_url"
                fit="contain"
                :preview-src-list="[detail.record.result_image_url]"
                class="report-img"
                preview-teleported
              />
            </el-col>
          </el-row>

          <template v-if="detail.report">
            <!-- 报告基本信息 -->
            <el-descriptions title="报告信息" :column="2" border size="small">
              <el-descriptions-item label="报告编号">{{ detail.report.report_no }}</el-descriptions-item>
              <el-descriptions-item label="检测时间">{{ detail.report.detect_time }}</el-descriptions-item>
              <el-descriptions-item label="图像尺寸">
                {{ detail.report.image_info?.width }} × {{ detail.report.image_info?.height }}
              </el-descriptions-item>
              <el-descriptions-item label="平均置信度">
                {{ (detail.report.conclusion?.confidence_avg * 100).toFixed(1) }}%
              </el-descriptions-item>
            </el-descriptions>

            <!-- 缺陷明细表 -->
            <h4 class="report-section-title">缺陷明细表</h4>
            <el-table
              v-if="detail.report.defect_details?.length"
              :data="detail.report.defect_details"
              size="small"
              border
              max-height="240"
            >
              <el-table-column label="序号" type="index" width="60" align="center" />
              <el-table-column prop="class_name" label="缺陷类型" width="100">
                <template #default="{ row }">
                  <el-tag :color="DEFECT_COLORS[row.class_name]" effect="dark" size="small">
                    {{ row.class_name }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="置信度" width="100" align="center">
                <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
              </el-table-column>
              <el-table-column prop="severity" label="严重程度" width="90" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="SEVERITY_TAG_TYPE[row.severity]">{{ row.severity }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="无缺陷" :image-size="60" />

            <!-- 统计汇总 -->
            <h4 class="report-section-title">统计汇总</h4>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-table :data="detail.report.statistics?.by_type || []" size="small" border>
                  <el-table-column prop="class_name" label="缺陷类型" />
                  <el-table-column prop="count" label="数量" width="70" align="center" />
                  <el-table-column label="占比" width="80" align="center">
                    <template #default="{ row }">{{ (row.ratio * 100).toFixed(1) }}%</template>
                  </el-table-column>
                </el-table>
              </el-col>
              <el-col :span="12">
                <el-table
                  :data="Object.entries(detail.report.statistics?.by_severity || {}).map(([k, v]) => ({ severity: k, count: v }))"
                  size="small"
                  border
                >
                  <el-table-column prop="severity" label="严重程度" />
                  <el-table-column prop="count" label="数量" width="80" align="center" />
                </el-table>
              </el-col>
            </el-row>

            <!-- 检测员信息 -->
            <h4 class="report-section-title">检测信息</h4>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="检测员">{{ detail.report.inspector?.name }}</el-descriptions-item>
              <el-descriptions-item label="检测模型">{{ detail.report.inspector?.model }}</el-descriptions-item>
              <el-descriptions-item label="检测方式">
                {{ detail.report.inspector?.detect_mode === 'demo' ? '演示模式（模拟检测）' : '真实模型推理' }}
              </el-descriptions-item>
            </el-descriptions>
          </template>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
/**
 * 历史记录页：筛选 + 分页表格 + 详情抽屉（完整报告）
 */
import { onMounted, reactive, ref } from 'vue'

import { getRecordDetail, getRecords } from '../api/records'
import { DEFECT_COLORS, DEFECT_TYPES, SEVERITY_TAG_TYPE } from '../constants'

// ---------- 筛选条件 ----------
const filters = reactive({
  defect_type: null,
  dateRange: null,
})

// ---------- 表格 ----------
const records = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)

// ---------- 详情抽屉 ----------
const drawerVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

async function loadRecords() {
  loading.value = true
  try {
    const params = { page: page.value, size: size.value }
    if (filters.defect_type) params.defect_type = filters.defect_type
    if (filters.dateRange?.length === 2) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    const data = await getRecords(params)
    records.value = data.items
    total.value = data.total
  } catch (e) {
    /* 网络错误由连接状态横幅提示 */
  } finally {
    loading.value = false
  }
}

// ---------- 后端连接状态（自动重试） ----------
const connecting = ref(false)
const backendDown = ref(false)

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

/** 初始加载：带自动重连 */
async function initLoad() {
  connecting.value = true
  backendDown.value = false
  try {
    await fetchWithRetry(loadRecords)
    backendDown.value = false
  } catch (e) {
    backendDown.value = true
  } finally {
    connecting.value = false
  }
}

function onSearch() {
  page.value = 1
  loadRecords()
}

function onReset() {
  filters.defect_type = null
  filters.dateRange = null
  page.value = 1
  loadRecords()
}

function onPageChange(p) {
  page.value = p
  loadRecords()
}

function onSizeChange(s) {
  size.value = s
  page.value = 1
  loadRecords()
}

/** 打开详情抽屉，加载完整报告 */
async function openDetail(row) {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await getRecordDetail(row.id)
  } catch (e) {
    drawerVisible.value = false
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

.filter-card { margin-bottom: 16px; }

.conn-alert { margin-bottom: 14px; }

.filter-row { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }

.filter-item { display: flex; align-items: center; gap: 8px; }

.filter-label { color: #606266; font-size: 14px; }

.record-table { cursor: default; }

.type-tag { margin-right: 6px; margin-bottom: 4px; }

.no-defect { color: #c0c4cc; }

.pagination { margin-top: 14px; justify-content: flex-end; }

.report-conclusion {
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.report-conclusion.pass { background: #f0f9eb; border: 1px solid #c2e7b0; }
.report-conclusion.fail { background: #fef0f0; border: 1px solid #fbc4c4; }

.conclusion-text { font-size: 18px; font-weight: 700; }
.report-conclusion.pass .conclusion-text { color: #67c23a; }
.report-conclusion.fail .conclusion-text { color: #f56c6c; }
.report-conclusion .meta { color: #909399; font-size: 13px; }

.report-imgs { margin-bottom: 14px; }

.img-title {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
  font-weight: 600;
}

.report-img {
  width: 100%;
  height: 200px;
  background: #1a1a1a;
  border-radius: 6px;
}

.report-section-title { margin: 18px 0 10px; font-size: 15px; color: #303133; }
</style>
