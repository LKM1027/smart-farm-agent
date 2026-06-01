<template>
  <div class="min-h-[calc(100vh-72px)] bg-slate-100 p-5 lg:p-6">
    <div class="mx-auto flex max-w-[1800px] flex-col gap-5">
      
      <!-- 1. 메인 헤더 영역 (독립된 박스로 분리 & 디자인 통일) -->
      <section class="relative overflow-hidden rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div class="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 class="mt-2 text-2xl font-bold text-slate-900">AI 자율 제어 관제탑</h1>
            <p class="mt-1 text-sm text-slate-500">
              다중 도구 기반 토마토 생육 환경 실시간 모니터링 및 자율 제어 시스템
            </p>
          </div>

          <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
            <!-- 시뮬레이션 알림바 -->
            <div
              v-if="store.simulationNotice"
              class="max-w-xl rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700"
            >
              {{ store.simulationNotice }}
            </div>

            <!-- 신규 디자인 적용된 AI 리포트 생성 버튼 -->
            <button
              id="btn-dashboard-generate-report"
              type="button"
              :disabled="store.isGeneratingReport"
              @click="handleGenerateReport"
              class="group relative inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-slate-900 px-6 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-slate-800 disabled:cursor-wait disabled:opacity-60"
            >
              <span v-if="store.isGeneratingReport" class="flex items-center gap-2">
                <svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                AI 분석 중... (최대 2분)
              </span>
              <span v-else class="flex items-center gap-2">
                <svg class="h-4 w-4 transition-transform group-hover:rotate-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.346.346A3.51 3.51 0 0115 16.5h-6a3.51 3.51 0 01-2.684-1.254l-.346-.346z"/>
                </svg>
                AI 리포트 생성
              </span>
            </button>
          </div>
        </div>
      </section>

      <!-- 2. 센서 모니터링 영역 (완전 독립된 박스로 분리) -->
      <section class="flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div class="border-b border-slate-200 px-5 py-4 flex flex-col">
          <h2 class="text-base font-bold tracking-tight text-slate-900">온실 환경 모니터링</h2>
          <p class="mt-1 text-xs text-slate-500 tracking-wide">
            내부 핵심 센서(온도, 습도, CO₂) 데이터 실시간 집계 및 생육 임계치 추적
          </p>
        </div>
        <div class="min-h-0 flex-1 p-5">
          <SensorPanel />
        </div>
      </section>

      <!-- 3. 에이전트 및 하드웨어 제어 영역 -->
      <section class="grid min-h-[620px] flex-1 gap-5 xl:grid-cols-2">
        <div class="flex min-h-[560px] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div class="border-b border-slate-200 px-5 py-4 flex flex-col">
            <h2 class="text-base font-bold tracking-tight text-slate-900">스마트팜 에이전트 브리핑 룸</h2>
            <p class="mt-1 text-xs text-slate-500 tracking-wide">
              자연어 기반 온실 상태 진단 및 최적 생육 환경 제어 시나리오 자동 생성
            </p>
          </div>
          <div class="min-h-0 flex-1 p-5">
            <ChatPanel class="h-full min-h-[480px]" @quickHint="handleQuickHint" />
          </div>
        </div>

        <div class="flex min-h-[560px] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div class="border-b border-slate-200 px-5 py-4 flex flex-col">
            <h2 class="text-base font-bold tracking-tight text-slate-900">설비 제어 및 통신 터미널</h2>
            <p class="mt-1 text-xs text-slate-500 tracking-wide">
              에이전트 제어 시퀀스 물리 장치 매핑 및 RS-485 모드버스 실시간 로그
            </p>
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
