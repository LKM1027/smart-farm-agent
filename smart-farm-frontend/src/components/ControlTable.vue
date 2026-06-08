<template>
  <section class="flex h-full flex-col bg-white border-t-0 border-transparent overflow-hidden">
    
    <div class="flex-1 grid grid-cols-2 divide-x divide-slate-200 min-h-0 overflow-hidden">
      <div class="flex flex-col min-h-0 overflow-hidden">
        <div class="px-4 py-3 bg-slate-0 border-b border-slate-200">
          <div class="text-[10px] uppercase tracking-[0.18em] font-semibold text-slate-500">제어 시퀀스</div>
        </div>

        <div v-if="!store.hasControlData && !store.isPageLoading" class="flex-1 flex flex-col items-center justify-center text-center gap-3 p-6">
          <div class="w-12 h-12 rounded-lg border border-slate-200 grid place-items-center text-slate-400 bg-slate-50 shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="h-5 w-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 5.25h16.5m-16.5 4.5h16.5m-16.5 4.5h16.5m-16.5 4.5h16.5" />
            </svg>
          </div>
          <p class="text-xs text-slate-400 font-medium tracking-wide">제어 시퀀스 대기 중...</p>
        </div>

        <div v-else-if="store.isPageLoading" class="flex-1 px-4 py-3 flex flex-col gap-2">
          <div v-for="i in 3" :key="i" class="h-10 rounded-md bg-slate-100 animate-pulse"></div>
        </div>

        <Transition name="table-fade">
          <div v-if="store.hasControlData && !store.isPageLoading" class="flex-1 overflow-auto">
            <table class="w-full text-left border-separate border-spacing-0">
              <thead class="sticky top-0 bg-white">
                <tr>
                  <th class="py-3 px-2 text-[10px] font-semibold text-slate-500 text-center">#</th>
                  <th class="py-3 px-2 text-[10px] font-semibold text-slate-500">장치</th>
                  <th class="py-3 px-2 text-[10px] font-semibold text-slate-500">코드</th>
                  <th class="py-3 px-2 text-[10px] font-semibold text-slate-500">액션</th>
                  <th class="py-3 px-2 text-[10px] font-semibold text-slate-500">값</th>
                  <th class="py-3 px-2 text-[10px] font-semibold text-slate-500 text-left">제어 사유</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(cmd, idx) in store.controlSequence"
                  :key="idx"
                  class="border-b border-slate-200 last:border-b-0 hover:bg-slate-50"
                >
                  <td class="py-3 px-2 text-center text-[11px] text-slate-500 font-semibold">{{ idx + 1 }}</td>
                  <td class="py-3 px-2">
                    <span class="text-[11px] font-semibold text-slate-900">{{ deviceName(cmd.device) }}</span>
                  </td>
                  <td class="py-3 px-2">
                    <span class="inline-flex rounded-md border border-slate-200 bg-white px-2 py-1 text-[10px] font-mono text-slate-600 shadow-sm">
                      {{ cmd.device }}
                    </span>
                  </td>
                  <td class="py-3 px-2">
                    <span :class="['inline-flex rounded-md border px-2 py-1 text-[10px] font-semibold shadow-sm', actionClass(cmd.action)]">
                      {{ cmd.action }}
                    </span>
                  </td>
                  <td class="py-3 px-2">
                    <span v-if="cmd.value != null" class="font-extrabold font-mono text-[11px] text-slate-900">
                      {{ cmd.value }}<span class="text-slate-500 font-normal">{{ valueUnit(cmd.device, cmd.action) }}</span>
                    </span>
                    <span v-else class="text-slate-500 text-[11px] font-mono italic">—</span>
                  </td>
                  <td class="py-3 px-2 max-w-[150px]">
                    <p class="text-[10px] leading-relaxed text-slate-500 line-clamp-2" :title="cmd.reason || cmd.description">
                      {{ cmd.reason || cmd.description || '-' }}
                    </p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Transition>

        <div v-if="store.hasControlData" class="px-4 py-2 border-t border-slate-200 bg-slate-50 text-[10px] text-slate-500">
          SmartFarm CPS 규격 준수 • 안전 가드레일 검증 완료
        </div>
      </div>

      <div class="flex flex-col min-h-0 bg-slate-50">
        <div class="px-4 py-3 border-b border-slate-200 flex items-center justify-between text-[10px] text-slate-500">
          <div>
            <div class="font-semibold text-slate-700">RS-485 MODBUS I/O TERMINAL</div>
          </div>
          <div class="flex items-center gap-2">
            <span :class="hasModbusData ? 'text-[#2F6D43]' : 'text-slate-500'">{{ hasModbusData ? 'CONNECTED' : 'IDLE' }}</span>
          </div>
        </div>

        <div ref="terminalRef" class="flex-1 overflow-y-auto p-4 font-mono text-sm leading-6 space-y-2 min-h-0">
          <div v-if="!hasModbusData && !store.isPageLoading" class="h-full flex flex-col items-center justify-center text-center gap-3 p-6">
            <div class="w-12 h-12 rounded-lg border border-slate-200 grid place-items-center text-slate-400 bg-slate-50 shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="h-5 w-5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0 0 21 18V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v12a2.25 2.25 0 0 0 2.25 2.25Z" />
              </svg>
            </div>
            <p class="text-xs text-slate-400 font-medium tracking-wide">에이전트 명령 대기 중...</p>
          </div>

          <div v-else-if="store.isPageLoading && !hasModbusData" class="text-slate-700">
            <span class="text-slate-500">$ </span>
            <span class="terminal-cursor">▋</span>
          </div>

          <template v-else>
            <div
              v-for="(line, idx) in visibleLines"
              :key="idx"
              :class="terminalLineClass(line)"
            >
              <span v-if="line.startsWith('[Tx]')" class="text-[#2F6D43]">▶ </span>
              <span v-else-if="line.startsWith('[Rx]')" class="text-slate-700">◀ </span>
              <span v-else-if="line.startsWith('[SYS]')" class="text-slate-500">· </span>
              <span v-else-if="line.startsWith('[CMD')" class="text-slate-700">→ </span>
              <span v-else-if="line.startsWith('[WARN]')" class="text-red-500">⚠ </span>
              <span>{{ line }}</span>
            </div>
            <div v-if="hasModbusData && !store.isPageLoading" class="text-[#2F6D43] mt-1">
              <span class="text-slate-500">$ </span>
              <span class="terminal-cursor">▋</span>
            </div>
          </template>
        </div>

        <div class="px-4 py-3 border-t border-slate-200 bg-slate-100 text-[10px] text-slate-500 flex items-center justify-between">
          <span>RS-485 • 19200 bps</span>
          <span>Lines: {{ store.modbusFrames.length }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useAgentStore } from '../stores/agentStore'

const store = useAgentStore()
const terminalRef = ref(null)

const hasModbusData = computed(() => Array.isArray(store.modbusFrames) && store.modbusFrames.length > 0)
const visibleLines = ref([])
let renderTimer = null

function renderLines(frames) {
  visibleLines.value = []
  if (renderTimer) clearInterval(renderTimer)
  if (!frames || frames.length === 0) return

  let idx = 0
  renderTimer = setInterval(() => {
    if (idx < frames.length) {
      visibleLines.value.push(frames[idx])
      idx++
      nextTick(() => {
        if (terminalRef.value) terminalRef.value.scrollTop = terminalRef.value.scrollHeight
      })
    } else {
      clearInterval(renderTimer)
    }
  }, 55)
}

watch(() => store.modbusFrames, (newFrames) => {
  if (newFrames && newFrames.length > 0) renderLines(newFrames)
  else visibleLines.value = []
}, { immediate: true, deep: true })

function terminalLineClass(line) {
  if (line.startsWith('[Tx]'))   return 'text-[#2F6D43]'
  if (line.startsWith('[Rx]'))   return 'text-slate-700'
  if (line.startsWith('[SYS]'))  return 'text-slate-500'
  if (line.startsWith('[CMD'))   return 'text-slate-700'
  if (line.startsWith('[WARN]')) return 'text-red-500'
  return 'text-slate-700'
}

const DEVICE_INFO = {
  'CC01':     { 'name': '천창' },
  'CC03':     { 'name': '측창' },
  'CC05':     { 'name': '보온커튼' },
  'CC04':     { 'name': '차광막' },
  'CC18':     { 'name': '환풍기' },
  'CC08':     { 'name': '유동팬' },
  'CC26':     { 'name': '관수펌프' },
  'CC27':     { 'name': '관수밸브' },
  'CC23':     { 'name': '냉난방기' },
  'NU_EC_SET':{ 'name': 'EC설정' },
  'NU_PH_SET':{ 'name': 'pH설정' },
  'NU_VALVE': { 'name': '구역밸브' },
}

function deviceName(code) { return DEVICE_INFO[code]?.name ?? code }
function actionClass(action) {
  if (action.includes('ON') || action.includes('SET')) return 'border-[#2F6D43] bg-[#eff7ef] text-[#2F6D43]'
  if (action.includes('OFF') || action.includes('CLOSE') || action.includes('STOP')) return 'border-slate-200 bg-slate-100 text-slate-700'
  return 'border-slate-200 bg-slate-100 text-slate-700'
}
function valueUnit(device, action) {
  if (device === 'CC18') return '%'
  if (device === 'CC23') return '℃'
  if (action.includes('EC')) return ' dS/m'
  if (action.includes('PH')) return ''
  return ''
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.4s, transform 0.3s; }
.fade-enter-from, .fade-leave-to       { opacity: 0; transform: translateY(-4px); }

.table-fade-enter-active, .table-fade-leave-active { transition: opacity 0.25s ease; }
.table-fade-enter-from, .table-fade-leave-to { opacity: 0; }
.terminal-cursor { display: inline-block; animation: blink 1.2s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }
</style>
