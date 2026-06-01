<template>
  <section class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Environment Sensors</p>
        <h2 class="mt-1 text-sm font-semibold text-slate-900">실시간 온실 센서</h2>
      </div>
      <div class="flex items-center gap-2 text-xs font-semibold text-slate-500">
        <span v-if="store.isSensorActive" class="border border-emerald-200 bg-emerald-50 px-3 py-1 text-[#2F6D43]">LIVE</span>
        <span v-else class="border border-slate-200 bg-slate-50 px-3 py-1 text-slate-500">POLLING</span>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-3">
      <div class="border border-slate-200 bg-slate-50 p-5">
        <div class="mb-2 flex items-center justify-between">
          <span class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">온도 (TI)</span>
          <span class="text-sm text-slate-500">℃</span>
        </div>
        <div class="flex items-end justify-between gap-3">
          <span :class="['text-5xl font-extrabold leading-none', tempStatus.color]">
            {{ store.hasSensorData ? store.sensorData.temperature : '--' }}
          </span>
          <span :class="['mb-1 px-2 py-1 text-[11px] font-semibold', tempStatus.badgeClass]">
            {{ tempStatus.label }}
          </span>
        </div>
        <div class="mt-4 h-2 overflow-hidden bg-slate-200">
          <div
            class="h-full transition-all duration-700"
            :class="tempStatus.barColor"
            :style="{ width: store.hasSensorData ? `${Math.min(100, (store.sensorData.temperature / 40) * 100)}%` : '0%' }"
          ></div>
        </div>
      </div>

      <div class="border border-slate-200 bg-slate-50 p-5">
        <div class="mb-2 flex items-center justify-between">
          <span class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">습도 (HI)</span>
          <span class="text-sm text-slate-500">%</span>
        </div>
        <div class="flex items-end justify-between gap-3">
          <span :class="['text-5xl font-extrabold leading-none', humidStatus.color]">
            {{ store.hasSensorData ? store.sensorData.humidity : '--' }}
          </span>
          <span :class="['mb-1 px-2 py-1 text-[11px] font-semibold', humidStatus.badgeClass]">
            {{ humidStatus.label }}
          </span>
        </div>
        <div class="mt-4 h-2 overflow-hidden bg-slate-200">
          <div
            class="h-full transition-all duration-700"
            :class="humidStatus.barColor"
            :style="{ width: store.hasSensorData ? `${Math.min(100, store.sensorData.humidity)}%` : '0%' }"
          ></div>
        </div>
      </div>

      <div class="border border-slate-200 bg-slate-50 p-5">
        <div class="mb-2 flex items-center justify-between">
          <span class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">CO2 (CI)</span>
          <span class="text-sm text-slate-500">ppm</span>
        </div>
        <div class="flex items-end justify-between gap-3">
          <span :class="['text-5xl font-extrabold leading-none', co2Status.color]">
            {{ store.hasSensorData ? store.sensorData.co2 : '--' }}
          </span>
          <span :class="['mb-1 px-2 py-1 text-[11px] font-semibold', co2Status.badgeClass]">
            {{ co2Status.label }}
          </span>
        </div>
        <div class="mt-4 h-2 overflow-hidden bg-slate-200">
          <div
            class="h-full transition-all duration-700"
            :class="co2Status.barColor"
            :style="{ width: store.hasSensorData ? `${Math.min(100, (store.sensorData.co2 / 1500) * 100)}%` : '0%' }"
          ></div>
        </div>
      </div>
    </div>

    <div v-if="store.hasSensorData" class="border border-slate-200 bg-white px-4 py-3 text-[10px] text-slate-500">
      시설 ID: {{ store.sensorData.facility_id ?? 'N/A' }}
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '../stores/agentStore'

const store = useAgentStore()
let sensorPoller = null

onMounted(() => {
  store.fetchLatestSensorData()
  sensorPoller = window.setInterval(() => {
    store.fetchLatestSensorData()
  }, 10000)
})

onUnmounted(() => {
  if (sensorPoller) {
    window.clearInterval(sensorPoller)
    sensorPoller = null
  }
})

const tempStatus = computed(() => {
  const t = store.sensorData?.temperature
  if (t == null) return { color: 'text-slate-400', barColor: 'bg-slate-300', label: '--', badgeClass: 'bg-slate-100 text-slate-400' }
  if (t < 15) return { color: 'text-blue-600', barColor: 'bg-blue-500', label: '저온', badgeClass: 'bg-blue-50 text-blue-700' }
  if (t > 30) return { color: 'text-red-600', barColor: 'bg-red-500', label: '고온', badgeClass: 'bg-red-50 text-red-700' }
  return { color: 'text-[#2F6D43]', barColor: 'bg-emerald-500', label: '적정', badgeClass: 'bg-emerald-50 text-[#2F6D43]' }
})

const humidStatus = computed(() => {
  const h = store.sensorData?.humidity
  if (h == null) return { color: 'text-slate-400', barColor: 'bg-slate-300', label: '--', badgeClass: 'bg-slate-100 text-slate-400' }
  if (h < 60) return { color: 'text-amber-600', barColor: 'bg-amber-400', label: '건조', badgeClass: 'bg-amber-50 text-amber-700' }
  if (h > 80) return { color: 'text-indigo-600', barColor: 'bg-indigo-500', label: '과습', badgeClass: 'bg-indigo-50 text-indigo-700' }
  return { color: 'text-[#2F6D43]', barColor: 'bg-emerald-500', label: '적정', badgeClass: 'bg-emerald-50 text-[#2F6D43]' }
})

const co2Status = computed(() => {
  const c = store.sensorData?.co2
  if (c == null) return { color: 'text-slate-400', barColor: 'bg-slate-300', label: '--', badgeClass: 'bg-slate-100 text-slate-400' }
  if (c < 400) return { color: 'text-orange-600', barColor: 'bg-orange-500', label: '부족', badgeClass: 'bg-orange-50 text-orange-700' }
  if (c > 1000) return { color: 'text-red-600', barColor: 'bg-red-500', label: '과다', badgeClass: 'bg-red-50 text-red-700' }
  return { color: 'text-[#2F6D43]', barColor: 'bg-emerald-500', label: '적정', badgeClass: 'bg-emerald-50 text-[#2F6D43]' }
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s, transform 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
