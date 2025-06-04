/**
 * FixPilot API 客户端
 * 封装所有后端 API 调用
 */

import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证 token（如果有）
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('Response error:', error)
    
    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          // 未授权，清除 token 并跳转登录
          localStorage.removeItem('auth_token')
          window.location.href = '/login'
          break
        case 403:
          console.error('Access forbidden')
          break
        case 404:
          console.error('Resource not found')
          break
        case 500:
          console.error('Server error:', data.detail || 'Internal server error')
          break
        default:
          console.error(`HTTP ${status}:`, data.detail || error.message)
      }
    } else if (error.request) {
      console.error('Network error: No response received')
    } else {
      console.error('Request setup error:', error.message)
    }
    
    return Promise.reject(error)
  }
)

// API 方法定义
export const hostAPI = {
  /**
   * 获取所有主机列表
   */
  getHosts: () => api.get('/hosts'),
  
  /**
   * 获取指定主机信息
   * @param {number} hostId - 主机 ID
   */
  getHost: (hostId) => api.get(`/hosts/${hostId}`),
  
  /**
   * 更新主机信息
   * @param {number} hostId - 主机 ID
   * @param {object} data - 更新数据
   */
  updateHost: (hostId, data) => api.patch(`/hosts/${hostId}`, data)
}

export const issueAPI = {
  /**
   * 获取漏洞列表
   * @param {object} params - 查询参数
   * @param {number} params.host_id - 主机 ID
   * @param {number} params.cvss_min - 最小 CVSS 评分
   * @param {string} params.status - 状态筛选
   */
  getIssues: (params = {}) => api.get('/issues', { params }),
  
  /**
   * 获取指定漏洞详情
   * @param {number} issueId - 漏洞 ID
   */
  getIssue: (issueId) => api.get(`/issues/${issueId}`),
  
  /**
   * 更新漏洞状态
   * @param {number} issueId - 漏洞 ID
   * @param {object} data - 更新数据
   */
  updateIssue: (issueId, data) => api.patch(`/issues/${issueId}`, data)
}

export const playbookAPI = {
  /**
   * 生成 Ansible Playbook
   * @param {object} data - 生成参数
   * @param {number} data.host_id - 主机 ID
   * @param {number} data.cvss_threshold - CVSS 阈值
   */
  generatePlaybook: (data) => api.post('/playbook', data),
  
  /**
   * 下载 Playbook 文件
   * @param {string} filename - 文件名
   */
  downloadPlaybook: (filename) => api.get(`/playbooks/${filename}`, {
    responseType: 'blob'
  })
}

export const scanAPI = {
  /**
   * 解析扫描结果
   */
  parseResults: () => api.post('/scan/parse'),
  
  /**
   * 获取扫描状态
   */
  getScanStatus: () => api.get('/scan/status'),
  
  /**
   * 触发新的扫描
   * @param {object} data - 扫描参数
   */
  triggerScan: (data) => api.post('/scan/trigger', data)
}

export const statsAPI = {
  /**
   * 获取统计数据
   */
  getStats: () => api.get('/stats'),
  
  /**
   * 获取风险分布数据
   */
  getRiskDistribution: () => api.get('/stats/risk-distribution'),
  
  /**
   * 获取修复趋势数据
   * @param {object} params - 查询参数
   * @param {string} params.period - 时间周期 (day/week/month)
   */
  getFixTrends: (params = {}) => api.get('/stats/fix-trends', { params })
}

// 工具函数
export const utils = {
  /**
   * 格式化错误消息
   * @param {Error} error - 错误对象
   * @returns {string} 格式化的错误消息
   */
  formatError: (error) => {
    if (error.response?.data?.detail) {
      return error.response.data.detail
    } else if (error.message) {
      return error.message
    } else {
      return '未知错误'
    }
  },
  
  /**
   * 下载文件
   * @param {Blob} blob - 文件数据
   * @param {string} filename - 文件名
   */
  downloadFile: (blob, filename) => {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },
  
  /**
   * 格式化 CVSS 评分颜色
   * @param {number} cvss - CVSS 评分
   * @returns {string} 颜色类名
   */
  getCvssColor: (cvss) => {
    if (cvss >= 9.0) return 'text-red-600'
    if (cvss >= 7.0) return 'text-orange-500'
    if (cvss >= 4.0) return 'text-yellow-500'
    return 'text-green-500'
  },
  
  /**
   * 格式化风险等级
   * @param {number} cvss - CVSS 评分
   * @returns {string} 风险等级
   */
  getRiskLevel: (cvss) => {
    if (cvss >= 9.0) return '严重'
    if (cvss >= 7.0) return '高危'
    if (cvss >= 4.0) return '中危'
    return '低危'
  },
  
  /**
   * 格式化状态显示
   * @param {string} status - 状态值
   * @returns {object} 状态显示信息
   */
  formatStatus: (status) => {
    const statusMap = {
      'open': { text: '待修复', color: 'warning' },
      'fixing': { text: '修复中', color: 'primary' },
      'fixed': { text: '已修复', color: 'success' },
      'failed': { text: '修复失败', color: 'danger' }
    }
    return statusMap[status] || { text: status, color: 'info' }
  }
}

// 默认导出 API 实例
export default api
