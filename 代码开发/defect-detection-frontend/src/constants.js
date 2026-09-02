/**
 * 前端常量：与后端 algorithms/defect_mapping.py 的 DEFECT_CLASSES 保持一致
 * 缺陷类型、显示颜色、严重程度颜色
 */
export const DEFECT_TYPES = ['裂纹', '夹杂', '斑块', '麻点', '氧化皮', '划痕']

export const DEFECT_COLORS = {
  裂纹: '#DC143C',
  夹杂: '#FF8C00',
  斑块: '#32CD32',
  麻点: '#1E90FF',
  氧化皮: '#9400D3',
  划痕: '#00CED1',
}

export const SEVERITY_COLORS = {
  高: '#f56c6c',
  中: '#e6a23c',
  低: '#67c23a',
}

export const SEVERITY_TAG_TYPE = {
  高: 'danger',
  中: 'warning',
  低: 'success',
}
