<template>
  <el-card shadow="hover">
    <template #header>
      <div class="card-title">🗂 最近检测记录（点击行查看详情）</div>
    </template>

    <el-table
      :data="records"
      size="small"
      border
      stripe
      v-loading="loading"
      class="record-table"
      @row-click="(row) => emit('row-click', row)"
    >
      <el-table-column label="序号" width="60" align="center" type="index" :index="indexOffset" />
      <el-table-column prop="file_name" label="文件名" min-width="130" show-overflow-tooltip />
      <el-table-column prop="total_defects" label="缺陷总数" width="80" align="center" />
      <el-table-column label="检测结果" width="85" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === '合格' ? 'success' : 'danger'" size="small">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="检测时间" width="150" />
    </el-table>

    <el-pagination
      class="pagination"
      background
      layout="prev, pager, next, total"
      :total="total"
      :page-size="size"
      :current-page="page"
      @current-change="(p) => emit('page-change', p)"
    />
  </el-card>
</template>

<script setup>
/**
 * 检测记录表格组件（通用：Dashboard 右侧与 History 页面复用逻辑样式）
 * 点击行触发 row-click 事件（父组件打开详情弹窗/抽屉）
 */
const props = defineProps({
  records: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  size: { type: Number, default: 10 },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['page-change', 'row-click'])

/** 分页时序号连续 */
function indexOffset(i) {
  return (props.page - 1) * props.size + i + 1
}
</script>

<style scoped>
.record-table { cursor: pointer; }

.pagination {
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
