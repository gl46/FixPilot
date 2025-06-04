<template>
  <div class="radar-chart-container">
    <div class="chart-header mb-4">
      <h3 class="text-lg font-semibold text-gray-900">安全风险雷达图</h3>
      <p class="text-sm text-gray-600">主机安全状态多维度分析</p>
    </div>
    
    <div class="chart-wrapper" ref="chartContainer">
      <canvas ref="chartCanvas"></canvas>
    </div>
    
    <!-- 图例 -->
    <div class="chart-legend mt-4">
      <div class="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
        <div class="flex items-center">
          <div class="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
          <span>严重漏洞</span>
        </div>
        <div class="flex items-center">
          <div class="w-3 h-3 bg-orange-500 rounded-full mr-2"></div>
          <span>高危漏洞</span>
        </div>
        <div class="flex items-center">
          <div class="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
          <span>中危漏洞</span>
        </div>
        <div class="flex items-center">
          <div class="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
          <span>系统暴露</span>
        </div>
        <div class="flex items-center">
          <div class="w-3 h-3 bg-purple-500 rounded-full mr-2"></div>
          <span>补丁覆盖</span>
        </div>
        <div class="flex items-center">
          <div class="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
          <span>安全评分</span>
        </div>
      </div>
    </div>
    
    <!-- 统计信息 -->
    <div class="chart-stats mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="stat-item text-center p-3 bg-gray-50 rounded-lg">
        <div class="text-2xl font-bold text-red-600">{{ stats.critical }}</div>
        <div class="text-xs text-gray-600">严重</div>
      </div>
      <div class="stat-item text-center p-3 bg-gray-50 rounded-lg">
        <div class="text-2xl font-bold text-orange-600">{{ stats.high }}</div>
        <div class="text-xs text-gray-600">高危</div>
      </div>
      <div class="stat-item text-center p-3 bg-gray-50 rounded-lg">
        <div class="text-2xl font-bold text-yellow-600">{{ stats.medium }}</div>
        <div class="text-xs text-gray-600">中危</div>
      </div>
      <div class="stat-item text-center p-3 bg-gray-50 rounded-lg">
        <div class="text-2xl font-bold text-green-600">{{ stats.low }}</div>
        <div class="text-xs text-gray-600">低危</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
} from 'chart.js'

// 注册 Chart.js 组件
ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
)

// Props
const props = defineProps({
  data: {
    type: Object,
    default: () => ({
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      exposure: 0,
      patchCoverage: 0
    })
  },
  height: {
    type: Number,
    default: 300
  }
})

// 响应式数据
const chartContainer = ref(null)
const chartCanvas = ref(null)
const chart = ref(null)

const stats = reactive({
  critical: 0,
  high: 0,
  medium: 0,
  low: 0
})

// 监听数据变化
watch(() => props.data, (newData) => {
  updateChart(newData)
  updateStats(newData)
}, { deep: true })

// 生命周期
onMounted(() => {
  nextTick(() => {
    initChart()
    updateStats(props.data)
  })
})

onUnmounted(() => {
  if (chart.value) {
    chart.value.destroy()
  }
})

// 方法
function initChart() {
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  
  chart.value = new ChartJS(ctx, {
    type: 'radar',
    data: {
      labels: [
        '严重漏洞',
        '高危漏洞', 
        '中危漏洞',
        '系统暴露',
        '补丁覆盖',
        '安全评分'
      ],
      datasets: [{
        label: '当前状态',
        data: [0, 0, 0, 0, 0, 0],
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderColor: 'rgba(59, 130, 246, 0.8)',
        borderWidth: 2,
        pointBackgroundColor: 'rgba(59, 130, 246, 1)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#fff',
          bodyColor: '#fff',
          borderColor: 'rgba(59, 130, 246, 0.8)',
          borderWidth: 1,
          callbacks: {
            label: function(context) {
              const label = context.dataset.label || ''
              const value = context.parsed.r
              return `${label}: ${value.toFixed(1)}`
            }
          }
        }
      },
      scales: {
        r: {
          beginAtZero: true,
          max: 10,
          min: 0,
          ticks: {
            stepSize: 2,
            color: '#6b7280',
            font: {
              size: 10
            }
          },
          grid: {
            color: 'rgba(107, 114, 128, 0.2)'
          },
          angleLines: {
            color: 'rgba(107, 114, 128, 0.2)'
          },
          pointLabels: {
            color: '#374151',
            font: {
              size: 11,
              weight: '500'
            }
          }
        }
      },
      animation: {
        duration: 1000,
        easing: 'easeInOutQuart'
      }
    }
  })
  
  // 初始化数据
  updateChart(props.data)
}

function updateChart(data) {
  if (!chart.value) return

  // 计算雷达图数据
  const radarData = calculateRadarData(data)
  
  // 更新图表数据
  chart.value.data.datasets[0].data = radarData
  chart.value.update('active')
}

function calculateRadarData(data) {
  // 将原始数据转换为 0-10 的评分
  const maxValues = {
    critical: 20,  // 假设最大严重漏洞数
    high: 50,      // 假设最大高危漏洞数
    medium: 100,   // 假设最大中危漏洞数
    exposure: 100, // 系统暴露度百分比
    patchCoverage: 100, // 补丁覆盖率百分比
    securityScore: 10   // 安全评分
  }
  
  return [
    // 严重漏洞 (数值越高风险越大，需要反转)
    Math.max(0, 10 - (data.critical || 0) / maxValues.critical * 10),
    
    // 高危漏洞
    Math.max(0, 10 - (data.high || 0) / maxValues.high * 10),
    
    // 中危漏洞
    Math.max(0, 10 - (data.medium || 0) / maxValues.medium * 10),
    
    // 系统暴露 (百分比，需要反转)
    Math.max(0, 10 - (data.exposure || 0) / 10),
    
    // 补丁覆盖 (百分比，直接使用)
    Math.min(10, (data.patchCoverage || 0) / 10),
    
    // 安全评分 (直接使用)
    Math.min(10, data.securityScore || 0)
  ]
}

function updateStats(data) {
  stats.critical = data.critical || 0
  stats.high = data.high || 0
  stats.medium = data.medium || 0
  stats.low = data.low || 0
}

// 导出方法供父组件调用
defineExpose({
  updateChart,
  chart
})
</script>

<style scoped>
.radar-chart-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
}

.chart-wrapper {
  position: relative;
  height: 300px;
  width: 100%;
}

.chart-header h3 {
  margin: 0;
}

.chart-legend {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.chart-stats {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.stat-item {
  transition: all 0.2s ease;
}

.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .radar-chart-container {
    padding: 16px;
  }
  
  .chart-wrapper {
    height: 250px;
  }
  
  .chart-legend {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .chart-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
