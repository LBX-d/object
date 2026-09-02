/**
 * 历史记录与统计接口封装
 */
import request from './index'

/** 分页查询检测记录 */
export function getRecords(params) {
  return request.get('/records', { params })
}

/** 获取单条记录详情（含完整报告） */
export function getRecordDetail(id) {
  return request.get(`/records/${id}`)
}

/** 获取统计总览（总检测数、合格率、缺陷分布、日趋势） */
export function getStatistics() {
  return request.get('/statistics/overview')
}

/** 获取单次检测的完整结构化报告 */
export function getReport(id) {
  return request.get(`/statistics/report/${id}`)
}
