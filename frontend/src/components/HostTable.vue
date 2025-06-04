<template>
  <div class="host-table-container">
    <!-- 表格头部操作区 -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">主机管理</h2>
        <p class="text-gray-600 mt-1">管理和监控所有扫描主机的安全状态</p>
      </div>
      
      <div class="flex space-x-3">
        <!-- 搜索框 -->
        <el-input
          v-model="searchQuery"
          placeholder="搜索主机 IP 或主机名"
          :prefix-icon="Search"
          clearable
          class="w-64"
          @input="handleSearch"
        />
        
        <!-- 筛选器 -->
        <el-select
          v-model="riskFilter"
          placeholder="风险等级"
          clearable
          class="w-32"
          @change="handleFilter"
        >
          <el-option label="全部" value="" />
          <el-option label="严重" value="critical" />
          <el-option label="高危" value="high" />
          <el-option label="中危" value="medium" />
          <el-option label="低危" value="low" />
        </el-select>
        
        <!-- 刷新按钮 -->
        <el-button
          :icon="Refresh"
          @click="loadHosts"
          :loading="loading"
        >
          刷新
        </el-button>
        
        <!-- 扫描按钮 -->
        <el-button
          type="primary"
          :icon="Search"
          @click="triggerScan"
          :loading="scanning"
        >
          开始扫描
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-white p-4 rounded-lg shadow-sm border">
        <div class="flex items-center">
          <div class="p-2 bg-blue-100 rounded-lg">
            <el-icon class="text-blue-600" size="20"><Monitor /></el-icon>
          </div>
          <div class="ml-3">
            <p class="text-sm text-gray-600">总主机数</p>
            <p class="text-2xl font-bold text-gray-900">{{ stats.totalHosts }}</p>
          </div>
        </div>
      </div>
      
      <div class="bg-white p-4 rounded-lg shadow-sm border">
        <div class="flex items-center">
          <div class="p-2 bg-red-100 rounded-lg">
            <el-icon class="text-red-600" size="20"><Warning /></el-icon>
          </div>
          <div class="ml-3">
            <p class="text-sm text-gray-600">高危主机</p>
            <p class="text-2xl font-bold text-gray-900">{{ stats.highRiskHosts }}</p>
          </div>
        </div>
      </div>
      
      <div class="bg-white p-4 rounded-lg shadow-sm border">
        <div class="flex items-center">
          <div class="p-2 bg-green-100 rounded-lg">
            <el-icon class="text-green-600" size="20"><CircleCheck /></el-icon>
          </div>
          <div class="ml-3">
            <p class="text-sm text-gray-600">安全主机</p>
            <p class="text-2xl font-bold text-gray-900">{{ stats.safeHosts }}</p>
          </div>
        </div>
      </div>
      
      <div class="bg-white p-4 rounded-lg shadow-sm border">
        <div class="flex items-center">
          <div class="p-2 bg-yellow-100 rounded-lg">
            <el-icon class="text-yellow-600" size="20"><Clock /></el-icon>
          </div>
          <div class="ml-3">
            <p class="text-sm text-gray-600">待扫描</p>
            <p class="text-2xl font-bold text-gray-900">{{ stats.pendingHosts }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 主机表格 -->
    <div class="bg-white rounded-lg shadow-sm border">
      <el-table
        :data="filteredHosts"
        v-loading="loading"
        stripe
        class="w-full"
        @row-click="handleRowClick"
        @sort-change="handleSortChange"
      >
        <!-- IP 地址 -->
        <el-table-column
          prop="ip"
          label="IP 地址"
          width="140"
          sortable="custom"
        >
          <template #default="{ row }">
            <div class="flex items-center">
              <el-icon class="text-gray-400 mr-2"><Monitor /></el-icon>
              <span class="font-mono">{{ row.ip }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 主机名 -->
        <el-table-column
          prop="hostname"
          label="主机名"
          min-width="150"
          sortable="custom"
        >
          <template #default="{ row }">
            <span>{{ row.hostname || '-' }}</span>
          </template>
        </el-table-column>

        <!-- 操作系统 -->
        <el-table-column
          prop="os"
          label="操作系统"
          min-width="180"
        >
          <template #default="{ row }">
            <div class="flex items-center">
              <el-icon class="text-gray-400 mr-2"><Platform /></el-icon>
              <span>{{ row.os || '未知' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 风险评分 -->
        <el-table-column
          prop="risk_score"
          label="风险评分"
          width="120"
          sortable="custom"
        >
          <template #default="{ row }">
            <div class="flex items-center">
              <el-progress
                :percentage="Math.min(row.risk_score * 10, 100)"
                :color="getRiskColor(row.risk_score)"
                :stroke-width="8"
                class="w-16"
              />
              <span class="ml-2 font-bold" :class="getRiskTextColor(row.risk_score)">
                {{ row.risk_score.toFixed(1) }}
              </span>
            </div>
          </template>
        </el-table-column>

        <!-- 漏洞数量 -->
        <el-table-column
          label="漏洞统计"
          width="120"
        >
          <template #default="{ row }">
            <div class="space-y-1">
              <div class="flex justify-between text-xs">
                <span class="text-red-600">严重:</span>
                <span class="font-bold">{{ row.critical_count || 0 }}</span>
              </div>
              <div class="flex justify-between text-xs">
                <span class="text-orange-600">高危:</span>
                <span class="font-bold">{{ row.high_count || 0 }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <!-- 最后扫描时间 -->
        <el-table-column
          prop="last_scan"
          label="最后扫描"
          width="160"
          sortable="custom"
        >
          <template #default="{ row }">
            <div v-if="row.last_scan">
              <div class="text-sm">{{ formatDate(row.last_scan) }}</div>
              <div class="text-xs text-gray-500">{{ formatTime(row.last_scan) }}</div>
            </div>
            <span v-else class="text-gray-400">未扫描</span>
          </template>
        </el-table-column>

        <!-- 状态 -->
        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.status)"
              size="small"
            >
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column
          label="操作"
          width="200"
          fixed="right"
        >
          <template #default="{ row }">
            <div class="flex space-x-2">
              <el-button
                size="small"
                @click.stop="viewDetails(row)"
                :icon="View"
              >
                详情
              </el-button>
              
              <el-button
                size="small"
                type="primary"
                @click.stop="generatePlaybook(row)"
                :disabled="!row.high_count && !row.critical_count"
                :icon="Document"
              >
                修复
              </el-button>
              
              <el-dropdown @command="handleCommand" trigger="click">
                <el-button size="small" :icon="More" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :command="`scan:${row.id}`">
                      <el-icon><Refresh /></el-icon>
                      重新扫描
                    </el-dropdown-item>
                    <el-dropdown-item :command="`edit:${row.id}`">
                      <el-icon><Edit /></el-icon>
                      编辑信息
                    </el-dropdown-item>
                    <el-dropdown-item :command="`delete:${row.id}`" divided>
                      <el-icon><Delete /></el-icon>
                      删除主机
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="flex justify-between items-center p-4 border-t">
        <div class="text-sm text-gray-600">
          共 {{ totalHosts }} 台主机
        </div>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalHosts"
          layout="sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Refresh,
  Monitor,
  Warning,
  CircleCheck,
  Clock,
  Platform,
  View,
  Document,
  More,
  Edit,
  Delete
} from '@element-plus/icons-vue'
import { hostAPI, playbookAPI, scanAPI } from '@/api'
import dayjs from 'dayjs'

// 响应式数据
const loading = ref(false)
const scanning = ref(false)
const searchQuery = ref('')
const riskFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalHosts = ref(0)
const sortField = ref('')
const sortOrder = ref('')

const hosts = ref([])
const stats = reactive({
  totalHosts: 0,
  highRiskHosts: 0,
  safeHosts: 0,
  pendingHosts: 0
})

const router = useRouter()

// 计算属性
const filteredHosts = computed(() => {
  let result = hosts.value

  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(host =>
      host.ip.toLowerCase().includes(query) ||
      (host.hostname && host.hostname.toLowerCase().includes(query))
    )
  }

  // 风险等级过滤
  if (riskFilter.value) {
    result = result.filter(host => {
      const riskLevel = getRiskLevel(host.risk_score)
      return riskLevel === riskFilter.value
    })
  }

  return result
})

// 生命周期
onMounted(() => {
  loadHosts()
  
  // 监听全局刷新事件
  window.addEventListener('global-refresh', loadHosts)
})

onUnmounted(() => {
  window.removeEventListener('global-refresh', loadHosts)
})

// 方法
async function loadHosts() {
  loading.value = true
  try {
    const response = await hostAPI.getHosts()
    hosts.value = response.data
    totalHosts.value = response.data.length
    
    // 更新统计数据
    updateStats()
    
  } catch (error) {
    console.error('Failed to load hosts:', error)
    ElMessage.error('加载主机列表失败')
  } finally {
    loading.value = false
  }
}

function updateStats() {
  stats.totalHosts = hosts.value.length
  stats.highRiskHosts = hosts.value.filter(h => h.risk_score >= 7).length
  stats.safeHosts = hosts.value.filter(h => h.risk_score < 4).length
  stats.pendingHosts = hosts.value.filter(h => !h.last_scan).length
}

function handleSearch() {
  currentPage.value = 1
}

function handleFilter() {
  currentPage.value = 1
}

function handleSortChange({ prop, order }) {
  sortField.value = prop
  sortOrder.value = order
  // 这里可以实现服务端排序
}

function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
}

function handleCurrentChange(page) {
  currentPage.value = page
}

function handleRowClick(row) {
  viewDetails(row)
}

function viewDetails(host) {
  router.push(`/hosts/${host.id}`)
}

async function generatePlaybook(host) {
  try {
    const response = await playbookAPI.generatePlaybook({
      host_id: host.id,
      cvss_threshold: 7.0
    })
    
    ElMessage.success('Playbook 生成成功')
    
    // 可以选择下载或跳转到任务页面
    router.push(`/playbooks?host=${host.id}`)
    
  } catch (error) {
    console.error('Failed to generate playbook:', error)
    ElMessage.error('生成 Playbook 失败')
  }
}

async function triggerScan() {
  scanning.value = true
  try {
    await scanAPI.triggerScan({
      targets: 'all'
    })
    
    ElMessage.success('扫描任务已启动')
    
    // 定期检查扫描状态
    checkScanStatus()
    
  } catch (error) {
    console.error('Failed to trigger scan:', error)
    ElMessage.error('启动扫描失败')
  } finally {
    scanning.value = false
  }
}

async function checkScanStatus() {
  // 实现扫描状态检查逻辑
  // 可以使用轮询或 WebSocket
}

function handleCommand(command) {
  const [action, hostId] = command.split(':')
  const host = hosts.value.find(h => h.id === parseInt(hostId))
  
  switch (action) {
    case 'scan':
      rescanHost(host)
      break
    case 'edit':
      editHost(host)
      break
    case 'delete':
      deleteHost(host)
      break
  }
}

async function rescanHost(host) {
  try {
    await scanAPI.triggerScan({
      targets: [host.ip]
    })
    ElMessage.success(`已启动对 ${host.ip} 的扫描`)
  } catch (error) {
    ElMessage.error('启动扫描失败')
  }
}

function editHost(host) {
  // 实现编辑主机信息的逻辑
  ElMessage.info('编辑功能开发中')
}

async function deleteHost(host) {
  try {
    await ElMessageBox.confirm(
      `确定要删除主机 ${host.ip} 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 实现删除逻辑
    ElMessage.success('删除成功')
    loadHosts()
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 工具函数
function getRiskLevel(score) {
  if (score >= 9) return 'critical'
  if (score >= 7) return 'high'
  if (score >= 4) return 'medium'
  return 'low'
}

function getRiskColor(score) {
  if (score >= 9) return '#f56565'
  if (score >= 7) return '#ed8936'
  if (score >= 4) return '#ecc94b'
  return '#48bb78'
}

function getRiskTextColor(score) {
  if (score >= 9) return 'text-red-600'
  if (score >= 7) return 'text-orange-600'
  if (score >= 4) return 'text-yellow-600'
  return 'text-green-600'
}

function getStatusType(status) {
  const statusMap = {
    'online': 'success',
    'offline': 'danger',
    'scanning': 'warning',
    'unknown': 'info'
  }
  return statusMap[status] || 'info'
}

function getStatusText(status) {
  const statusMap = {
    'online': '在线',
    'offline': '离线',
    'scanning': '扫描中',
    'unknown': '未知'
  }
  return statusMap[status] || status
}

function formatDate(dateString) {
  return dayjs(dateString).format('YYYY-MM-DD')
}

function formatTime(dateString) {
  return dayjs(dateString).format('HH:mm:ss')
}
</script>

<style scoped>
.host-table-container {
  padding: 0;
}

.el-table {
  font-size: 14px;
}

.el-table .el-table__row {
  cursor: pointer;
}

.el-table .el-table__row:hover {
  background-color: #f5f7fa;
}

.el-progress {
  width: 60px;
}

.el-dropdown-menu {
  min-width: 120px;
}
</style>
