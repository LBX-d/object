<template>
  <el-card shadow="hover" class="result-card">
    <template #header>
      <div class="card-title">📋 检测结果</div>
    </template>

    <!-- 空状态 -->
    <el-empty
      v-if="!result && !loading"
      description="暂无检测结果，请先上传产品图像"
      :image-size="80"
    />

    <!-- 检测中 -->
    <div v-if="loading" class="loading-box">
      <span class="spinner"></span>
      <span>AI 检测中...</span>
    </div>

    <!-- 检测结果 -->
    <div v-if="result && !loading">
      <!-- 检测结论横幅 -->
      <div class="conclusion" :class="result.status === '合格' ? 'pass' : 'fail'">
        <span class="conclusion-text">
          {{ result.status === '合格' ? '✅ 检测合格' : `❌ 检测不合格（发现 ${result.total_defects} 处缺陷）` }}
        </span>
        <div class="conclusion-meta">
          <el-tag v-if="result.detect_mode === 'demo'" type="warning" size="small">演示模式</el-tag>
          <span>报告编号: {{ result.report_no }}</span>
          <span>平均置信度: {{ (result.confidence_avg * 100).toFixed(1) }}%</span>
          <span>耗时: {{ result.processing_time }}s</span>
        </div>
      </div>

      <!-- 原图 / 结果图左右对比 -->
      <el-row :gutter="12" class="img-row">
        <el-col :span="12">
          <div class="img-title">原图</div>
          <el-image
            :src="result.original_image_url"
            fit="contain"
            :preview-src-list="[result.original_image_url]"
            class="detect-img"
            preview-teleported
          />
        </el-col>
        <el-col :span="12">
          <div class="img-title">检测结果（彩色框 = 不同缺陷类型）</div>
          <div class="img-box">
            <el-image
              :src="result.result_image_url"
              fit="contain"
              :preview-src-list="[result.result_image_url]"
              class="detect-img"
              preview-teleported
            />
            <!-- 前端叠加检测框：悬停缺陷列表项时高亮对应框 -->
            <div
              v-for="(d, i) in details"
              :key="i"
              class="box-overlay"
              :class="{ highlight: hoveredClass === d.class_name }"
              :style="boxStyle(d.box, d.class_name)"
            />
          </div>
        </el-col>
      </el-row>

      <!-- 缺陷统计 + 明细 -->
      <div v-if="result.statistics" class="detail-section">
        <el-row :gutter="12">
          <el-col :span="12">
            <h4 class="section-title">缺陷类型统计</h4>
            <el-table :data="byType" size="small" border max-height="220">
              <el-table-column prop="class_name" label="缺陷类型" min-width="90">
                <template #default="{ row }">
                  <el-tag :color="DEFECT_COLORS[row.class_name]" effect="dark" size="small">
                    {{ row.class_name }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="count" label="数量" width="70" align="center" />
              <el-table-column label="占比" width="90" align="center">
                <template #default="{ row }">{{ (row.ratio * 100).toFixed(1) }}%</template>
              </el-table-column>
            </el-table>
          </el-col>

          <el-col :span="12">
            <h4 class="section-title">缺陷明细（悬停高亮对应检测框）</h4>
            <el-scrollbar height="220px">
              <div
                v-for="(d, i) in details"
                :key="i"
                class="detail-item"
                @mouseenter="hoveredClass = d.class_name"
                @mouseleave="hoveredClass = null"
              >
                <el-tag :color="DEFECT_COLORS[d.class_name]" effect="dark" size="small">
                  {{ d.class_name }}
                </el-tag>
                <span class="conf-text">置信度 {{ (d.confidence * 100).toFixed(1) }}%</span>
                <el-tag size="small" :type="SEVERITY_TAG_TYPE[d.severity]">{{ d.severity }}危</el-tag>
              </div>
            </el-scrollbar>
          </el-col>
        </el-row>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed, ref } from 'vue'
import { DEFECT_COLORS, SEVERITY_TAG_TYPE } from '../constants'

const props = defineProps({
  /** 检测结果对象（后端 DetectionResponse） */
  result: { type: Object, default: null },
  /** 是否检测中 */
  loading: { type: Boolean, default: false },
})

// 当前悬停的缺陷类型（用于高亮对应检测框）
const hoveredClass = ref(null)

const details = computed(() => props.result?.statistics?.details || [])
const byType = computed(() => props.result?.statistics?.by_type || [])

/** 归一化坐标(0~1) -> 百分比定位样式 */
function boxStyle(box, className) {
  const [x1, y1, x2, y2] = box
  return {
    left: `${x1 * 100}%`,
    top: `${y1 * 100}%`,
    width: `${(x2 - x1) * 100}%`,
    height: `${(y2 - y1) * 100}%`,
    borderColor: DEFECT_COLORS[className] || '#f00',
  }
}
</script>

<style scoped>
.loading-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 30px 0;
  color: #409eff;
  font-size: 14px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 3px solid #d0e5ff;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.conclusion {
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.conclusion.pass { background: #f0f9eb; border: 1px solid #c2e7b0; }
.conclusion.fail { background: #fef0f0; border: 1px solid #fbc4c4; }

.conclusion-text { font-size: 20px; font-weight: 700; }
.conclusion.pass .conclusion-text { color: #67c23a; }
.conclusion.fail .conclusion-text { color: #f56c6c; }

.conclusion-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  color: #606266;
  font-size: 13px;
}

.img-row { margin-bottom: 14px; }

.img-title {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
  font-weight: 600;
}

.detect-img {
  width: 100%;
  height: 260px;
  background: #1a1a1a;
  border-radius: 6px;
}

.img-box { position: relative; }

/* 叠加在结果图上的检测框（百分比定位，随图片缩放） */
.box-overlay {
  position: absolute;
  border: 2px solid;
  border-radius: 3px;
  pointer-events: none;
  transition: all 0.15s;
}

.box-overlay.highlight {
  border-width: 4px;
  filter: brightness(1.4);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.9);
}

.section-title { margin: 4px 0 8px; font-size: 14px; color: #303133; }

.detail-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 8px;
  border-bottom: 1px dashed #ebeef5;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s;
}

.detail-item:hover { background: #ecf5ff; }

.conf-text { font-size: 13px; color: #606266; flex: 1; }
</style>
