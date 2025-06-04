<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <!-- 顶部导航栏 -->
    <header class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <!-- Logo 和标题 -->
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <h1 class="text-2xl font-bold text-blue-600">FixPilot</h1>
            </div>
            <nav class="hidden md:ml-8 md:flex md:space-x-8">
              <router-link
                to="/"
                class="text-gray-900 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                :class="{ 'text-blue-600 bg-blue-50': $route.path === '/' }"
              >
                仪表板
              </router-link>
              <router-link
                to="/hosts"
                class="text-gray-900 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                :class="{ 'text-blue-600 bg-blue-50': $route.path === '/hosts' }"
              >
                主机管理
              </router-link>
              <router-link
                to="/issues"
                class="text-gray-900 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                :class="{ 'text-blue-600 bg-blue-50': $route.path === '/issues' }"
              >
                漏洞管理
              </router-link>
              <router-link
                to="/playbooks"
                class="text-gray-900 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                :class="{ 'text-blue-600 bg-blue-50': $route.path === '/playbooks' }"
              >
                修复任务
              </router-link>
            </nav>
          </div>

          <!-- 右侧操作区 -->
          <div class="flex items-center space-x-4">
            <!-- 刷新按钮 -->
            <el-button
              :icon="Refresh"
              circle
              @click="refreshData"
              :loading="refreshing"
              title="刷新数据"
            />
            
            <!-- 扫描状态 -->
            <div class="flex items-center space-x-2">
              <el-badge :value="stats.pendingIssues" :max="99" class="item">
                <el-button :icon="Warning" circle />
              </el-badge>
              <span class="text-sm text-gray-600">待修复</span>
            </div>

            <!-- 用户菜单 -->
            <el-dropdown>
              <span class="el-dropdown-link flex items-center cursor-pointer">
                <el-avatar :size="32" :icon="UserFilled" />
                <el-icon class="el-icon--right"><arrow-down /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item>个人设置</el-dropdown-item>
                  <el-dropdown-item>系统配置</el-dropdown-item>
                  <el-dropdown-item divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </header>

    <!-- 主要内容区域 -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <!-- 全局加载状态 -->
      <div v-if="loading" class="flex justify-center items-center h-64">
        <el-loading-spinner size="large" />
      </div>

      <!-- 路由视图 -->
      <router-view v-else />
    </main>

    <!-- 全局通知 -->
    <el-backtop :right="100" :bottom="100" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import {
  Refresh,
  Warning,
  UserFilled,
  ArrowDown
} from '@element-plus/icons-vue'
import { statsAPI } from '@/api'

// 响应式数据
const loading = ref(false)
const refreshing = ref(false)
const stats = reactive({
  totalHosts: 0,
  totalIssues: 0,
  pendingIssues: 0,
  fixedIssues: 0,
  highRiskIssues: 0
})

const router = useRouter()

// 提供全局状态给子组件
provide('globalStats', stats)
provide('refreshGlobalData', refreshData)

// 生命周期
onMounted(() => {
  initApp()
})

// 方法
async function initApp() {
  loading.value = true
  try {
    await loadStats()
    ElMessage.success('FixPilot 初始化完成')
  } catch (error) {
    console.error('App initialization failed:', error)
    ElNotification.error({
      title: '初始化失败',
      message: '无法连接到后端服务，请检查网络连接'
    })
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await statsAPI.getStats()
    Object.assign(stats, response.data)
  } catch (error) {
    console.error('Failed to load stats:', error)
    // 使用模拟数据作为回退
    Object.assign(stats, {
      totalHosts: 0,
      totalIssues: 0,
      pendingIssues: 0,
      fixedIssues: 0,
      highRiskIssues: 0
    })
  }
}

async function refreshData() {
  refreshing.value = true
  try {
    await loadStats()
    ElMessage.success('数据已刷新')
    
    // 通知当前页面刷新
    window.dispatchEvent(new CustomEvent('global-refresh'))
  } catch (error) {
    console.error('Failed to refresh data:', error)
    ElMessage.error('刷新失败')
  } finally {
    refreshing.value = false
  }
}

// 全局错误处理
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason)
  ElNotification.error({
    title: '系统错误',
    message: '发生未处理的错误，请刷新页面重试'
  })
})
</script>

<style scoped>
.el-dropdown-link {
  color: var(--el-text-color-regular);
  display: flex;
  align-items: center;
}

.router-link-active {
  color: var(--el-color-primary) !important;
  background-color: var(--el-color-primary-light-9) !important;
}

/* 自定义滚动条 */
:deep(.el-scrollbar__wrap) {
  scrollbar-width: thin;
  scrollbar-color: #c1c1c1 transparent;
}

:deep(.el-scrollbar__wrap::-webkit-scrollbar) {
  width: 6px;
  height: 6px;
}

:deep(.el-scrollbar__wrap::-webkit-scrollbar-thumb) {
  background-color: #c1c1c1;
  border-radius: 3px;
}

:deep(.el-scrollbar__wrap::-webkit-scrollbar-track) {
  background-color: transparent;
}
</style>
