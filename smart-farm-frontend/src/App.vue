<template>
  <div class="min-h-screen bg-slate-50 text-slate-950">
    <div class="min-h-screen flex">
      <aside class="w-[250px] border-r border-slate-200 bg-white">
        <div class="flex h-full flex-col">
          <div class="px-6 py-6 border-b border-slate-200">
            <div class="flex items-start gap-3">
              <div class="flex h-12 w-12 items-center justify-center rounded-sm bg-[#2F6D43] text-lg font-semibold text-white">S</div>
              <div>
                <p class="text-sm font-semibold text-slate-900">SmartFarm CPS</p>
                <p class="mt-1 text-xs text-slate-500">AI의 지능과 하드웨어의 물리적 융합</p>
              </div>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto px-4 py-6">
            <nav class="space-y-1 text-sm">
              <router-link
                v-for="item in navItems"
                :key="item.path"
                :to="item.path"
                class="flex w-full items-center justify-between rounded-sm border px-4 py-3 text-left transition"
                :class="route.path === item.path
                  ? 'border-stone-200 bg-emerald-50 text-emerald-700 font-semibold'
                  : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-900'"
              >
                <span>{{ item.label }}</span>
                <span class="text-[11px]" :class="route.path === item.path ? 'text-emerald-700' : 'text-slate-400'">{{ item.tag }}</span>
              </router-link>
            </nav>
          </div>

          <div class="px-4 py-6 border-t border-slate-200 text-xs text-slate-500">
            <p class="font-semibold text-slate-700">운영 환경</p>
            <p class="mt-2 leading-relaxed">온실 관제, RAG, Modbus 통합 리포트</p>
          </div>
        </div>
      </aside>

      <main class="flex-1">
        <div class="border-b border-slate-200 bg-white px-6 py-4">
          <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div class="flex items-center gap-3">
              <input
                type="text"
                placeholder="장비, 센서, 보고서 검색..."
                class="h-11 min-w-[280px] rounded-sm border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 focus:border-[#2F6D43] focus:outline-none focus:ring-1 focus:ring-[#2F6D43]/20"
              />
            </div>
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div class="inline-flex items-center gap-2 rounded-sm border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-700">
                <span>{{ currentTime }}</span>
              </div>
              <div class="inline-flex items-center gap-2 rounded-sm border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700">
                <span class="inline-flex h-2 w-2 rounded-full bg-[#2F6D43]"></span>
                Edge Node Online
              </div>
              <button
                :disabled="store.reports.isLoading"
                @click="handleGenerateReport"
                class="inline-flex items-center justify-center gap-2 rounded-sm border border-[#2F6D43] bg-white px-4 py-2 text-sm font-semibold text-[#2F6D43] transition hover:bg-[#2F6D43]/10 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {{ store.reports.isLoading ? '생성 중...' : '주간 리포트 생성' }}
              </button>
            </div>
          </div>
        </div>

        <div class="p-6">
          <router-view />
        </div>
      </main>
    </div>

    <Transition name="overlay-fade">
      <div v-if="store.isPageLoading" class="fixed inset-0 z-40 flex items-center justify-center bg-slate-50/75">
        <div class="rounded-sm border border-slate-200 bg-white p-8">
          <div class="flex flex-col items-center gap-4">
            <div class="h-12 w-12 rounded-sm border-4 border-slate-200 border-t-[#2F6D43] animate-spin"></div>
            <p class="text-base font-semibold text-slate-900">에이전트 추론 중...</p>
            <p class="text-sm text-slate-500">LangGraph 워크플로우 실행 중</p>
          </div>
        </div>
      </div>
    </Transition>

    <Transition name="modal-fade">
      <div v-if="showReportModal" class="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-slate-900/35"></div>
        <div class="relative w-full max-w-4xl rounded-sm border border-slate-200 bg-white overflow-hidden">
          <div class="flex items-center justify-between gap-4 border-b border-slate-200 px-6 py-4">
            <div>
              <p class="text-xs uppercase tracking-[0.24em] text-slate-500">주간 리포트</p>
              <h2 class="mt-2 text-lg font-semibold text-slate-900">AI 생육 및 설비 리포트</h2>
            </div>
            <button
              @click="showReportModal = false"
              class="inline-flex h-10 w-10 items-center justify-center rounded-sm border border-slate-200 text-slate-600 transition hover:bg-slate-100"
            >✕</button>
          </div>

          <div class="flex items-center gap-2 border-b border-slate-200 bg-slate-50 px-4 py-3">
            <button
              @click="activeReportTab = 'farm'"
              :class="activeReportTab === 'farm'
                ? 'rounded-sm bg-[#2F6D43] px-4 py-2 text-sm font-semibold text-white'
                : 'rounded-sm bg-transparent px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100'"
            >농업인용</button>
            <button
              @click="activeReportTab = 'equipment'"
              :class="activeReportTab === 'equipment'
                ? 'rounded-sm bg-[#2F6D43] px-4 py-2 text-sm font-semibold text-white'
                : 'rounded-sm bg-transparent px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100'"
            >설비업체용</button>
          </div>

          <div class="max-h-[70vh] overflow-y-auto p-6">
            <div v-if="store.reports.isLoading" class="flex flex-col items-center justify-center gap-4 py-12">
              <div class="h-12 w-12 rounded-sm border-4 border-slate-200 border-t-[#2F6D43] animate-spin"></div>
              <p class="text-sm text-slate-500">리포트 생성 중...</p>
            </div>
            <div v-else class="space-y-4 text-slate-700">
              <div v-if="activeReportTab === 'farm'" v-html="renderMarkdown(store.reports.farmReport)" class="report-content"></div>
              <div v-else v-html="renderMarkdown(store.reports.equipmentReport)" class="report-content"></div>
            </div>
          </div>

          <div class="flex justify-end border-t border-slate-200 bg-slate-50 px-6 py-4">
            <button
              @click="showReportModal = false"
              class="rounded-sm border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >닫기</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAgentStore } from './stores/agentStore'

const route = useRoute()
const store = useAgentStore()

const showReportModal = ref(false)
const activeReportTab = ref('farm')

const currentTime = ref('')
let clockTimer = null
function updateClock() {
  currentTime.value = new Date().toLocaleTimeString('ko-KR', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  })
}
onMounted(() => { updateClock(); clockTimer = setInterval(updateClock, 1000) })
onUnmounted(() => clearInterval(clockTimer))

const navItems = [
  { path: '/', label: '통합 대시보드', tag: 'Active' },
  { path: '/data', label: '환경 및 생육 데이터', tag: '데이터' },
  { path: '/hardware', label: '하드웨어 제어망', tag: '모드' },
  { path: '/reports', label: 'AI 리포트 아카이브', tag: '보관' },
  { path: '/settings', label: '시스템 설정', tag: '설정' },
]

function handleGenerateReport() {
  showReportModal.value = true
  activeReportTab.value = 'farm'
  store.generateWeeklyReport()
}

function renderMarkdown(md) {
  if (!md) return ''
  return md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold text-slate-900 mt-4 mb-2">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold text-slate-900 mt-5 mb-3">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-slate-900 mt-6 mb-4">$1</h1>')
    .replace(/^\- (.+)$/gm, '<li class="text-sm text-slate-700 leading-relaxed mb-1 ml-4 list-disc">$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>')
    .replace(/`(.+?)`/g, '<code class="font-mono text-slate-800 bg-slate-100 px-1.5 rounded text-[11px]">$1</code>')
    .replace(/\n/g, '<br>')
    .trim()
}
</script>

<style scoped>
.overlay-fade-enter-active, .overlay-fade-leave-active { transition: opacity 0.4s ease; }
.overlay-fade-enter-from, .overlay-fade-leave-to       { opacity: 0; }

.modal-fade-enter-active { transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.16, 1, 0.3, 1); }
.modal-fade-leave-active { transition: opacity 0.25s ease, transform 0.2s ease; }
.modal-fade-enter-from   { opacity: 0; transform: scale(1.02); }
.modal-fade-leave-to     { opacity: 0; transform: scale(0.98); }
</style>
