<template>
  <div class="min-h-[calc(100vh-72px)] bg-slate-100 p-5 lg:p-6">
    <div class="mx-auto flex max-w-[1800px] flex-col gap-5">
      <section class="overflow-hidden border border-slate-200 bg-white shadow-sm">
        <div class="flex flex-col gap-4 border-b border-slate-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Greenhouse Control Tower</p>
            <h1 class="mt-2 text-2xl font-semibold text-slate-950">온실 관제탑</h1>
          </div>

          <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div
              v-if="store.simulationNotice"
              class="max-w-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700"
            >
              {{ store.simulationNotice }}
            </div>

            <!-- AI 주간 리포트 생성 버튼 -->
            <button
              id="btn-dashboard-generate-report"
              type="button"
              class="inline-flex min-h-11 items-center justify-center gap-2 border border-emerald-600 bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-wait disabled:opacity-60"
              :disabled="store.isGeneratingReport"
              @click="handleGenerateReport"
            >
              <svg class="h-4 w-4" :class="{ 'animate-spin': store.isGeneratingReport }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.346.346A3.51 3.51 0 0115 16.5h-6a3.51 3.51 0 01-2.684-1.254l-.346-.346z"/>
              </svg>
              {{ store.isGeneratingReport ? 'AI 분석 중...' : '📊 AI 주간 리포트 생성' }}
            </button>

            <button
              type="button"
              class="inline-flex min-h-11 items-center justify-center border border-red-700 bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-wait disabled:opacity-60"
              :disabled="store.isInjectingAnomaly"
              @click="store.injectHeatwaveAnomaly"
            >
              {{ store.isInjectingAnomaly ? '주입 중...' : '[🚨 시뮬레이션] 폭염 데이터 강제 주입 (45.5℃)' }}
            </button>
          </div>
        </div>

        <div class="p-5">
          <SensorPanel />
        </div>
      </section>

      <section class="grid min-h-[620px] flex-1 gap-5 xl:grid-cols-2">
        <div class="flex min-h-[560px] flex-col overflow-hidden border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-200 px-5 py-4">
            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Intelligence</p>
            <h2 class="mt-2 text-xl font-semibold text-slate-950">스마트팜 에이전트 브리핑 룸</h2>
          </div>
          <div class="min-h-0 flex-1 p-5">
            <ChatPanel class="h-full min-h-[480px]" @quickHint="handleQuickHint" />
          </div>
        </div>

        <div class="flex min-h-[560px] flex-col overflow-hidden border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-200 px-5 py-4">
            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Hardware Control</p>
            <h2 class="mt-2 text-xl font-semibold text-slate-950">하드웨어 제어 테이블 및 통신 로그</h2>
          </div>
          <div class="min-h-0 flex-1 p-5">
            <ControlTable class="h-full min-h-[480px]" />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import SensorPanel from '../components/SensorPanel.vue'
import ChatPanel from '../components/ChatPanel.vue'
import ControlTable from '../components/ControlTable.vue'
import { useAgentStore } from '../stores/agentStore'

const store = useAgentStore()
const router = useRouter()

function handleQuickHint(text) {
  store.sendAgentQuery(text)
}

async function handleGenerateReport() {
  await store.generateWeeklyReportToArchive()
  // 생성 완료 후 리포트 뷰로 이동
  router.push('/reports')
}
</script>
