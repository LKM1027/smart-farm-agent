<template>
  <div class="min-h-[calc(100vh-72px)] bg-slate-950 p-5 lg:p-6">
    <div class="mx-auto flex max-w-[1800px] flex-col gap-5">

      <!-- ── 헤더 ──────────────────────────────────────────── -->
      <section class="relative overflow-hidden rounded-xl border border-emerald-500/20 bg-gradient-to-br from-slate-900 via-emerald-950/30 to-slate-900 p-6 shadow-2xl">
        <!-- 배경 글로우 -->
        <div class="pointer-events-none absolute inset-0 overflow-hidden">
          <div class="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl"></div>
          <div class="absolute -right-20 bottom-0 h-48 w-48 rounded-full bg-teal-400/10 blur-3xl"></div>
        </div>

        <div class="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-400">
              AI Weekly Report Archive
            </p>
            <h1 class="mt-2 text-2xl font-bold text-white">주간 AI 생육 분석 리포트</h1>
            <p class="mt-1 text-sm text-slate-400">
              최근 7일간 센서 데이터를 일별 집계 → Gemini AI가 생육 분석 리포트 자동 생성
            </p>
          </div>

          <!-- 리포트 생성 버튼 -->
          <button
            id="btn-generate-report"
            type="button"
            :disabled="store.isGeneratingReport"
            @click="handleGenerate"
            class="group relative inline-flex min-h-12 items-center gap-2.5 overflow-hidden rounded-lg border border-emerald-500/40 bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-900/40 transition-all duration-200 hover:from-emerald-500 hover:to-teal-500 hover:shadow-emerald-700/50 disabled:cursor-wait disabled:opacity-60"
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
              수동 리포트 생성
            </span>
          </button>
        </div>

        <!-- 에러 메시지 -->
        <div
          v-if="store.reportError"
          class="relative mt-4 flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-950/40 px-4 py-3 text-sm text-red-300"
        >
          <svg class="mt-0.5 h-4 w-4 shrink-0 text-red-400" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
          </svg>
          <span>{{ store.reportError }}</span>
        </div>
      </section>

      <!-- ── 메인 콘텐츠 ─────────────────────────────────── -->
      <div class="grid min-h-[680px] gap-5 lg:grid-cols-[320px_1fr]">

        <!-- 좌측: 리포트 목록 -->
        <aside class="flex flex-col overflow-hidden rounded-xl border border-slate-700/50 bg-slate-900 shadow-xl">
          <div class="border-b border-slate-700/50 px-5 py-4">
            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Archive</p>
            <h2 class="mt-1 text-base font-semibold text-white">리포트 보관함</h2>
            <p class="mt-0.5 text-xs text-slate-500">
              총 <span class="font-bold text-emerald-400">{{ store.weeklyReports.length }}</span>건
            </p>
          </div>

          <!-- 목록 로딩 -->
          <div v-if="store.isLoadingReports" class="flex flex-1 flex-col items-center justify-center gap-3 p-8">
            <div class="h-8 w-8 animate-spin rounded-full border-2 border-slate-700 border-t-emerald-400"></div>
            <p class="text-xs text-slate-500">목록 불러오는 중...</p>
          </div>

          <!-- 빈 목록 -->
          <div
            v-else-if="store.weeklyReports.length === 0"
            class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center"
          >
            <div class="flex h-14 w-14 items-center justify-center rounded-full bg-slate-800">
              <svg class="h-7 w-7 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
            </div>
            <p class="text-sm font-medium text-slate-400">생성된 리포트 없음</p>
            <p class="text-xs text-slate-600">우측 상단의 "수동 리포트 생성" 버튼을 눌러 첫 리포트를 만들어 보세요.</p>
          </div>

          <!-- 리포트 목록 -->
          <ul v-else class="flex-1 overflow-y-auto divide-y divide-slate-800">
            <li
              v-for="report in store.weeklyReports"
              :key="report.id"
              @click="store.selectReport(report)"
              :class="[
                'group cursor-pointer px-5 py-4 transition-all duration-150',
                store.selectedReport?.id === report.id
                  ? 'border-l-2 border-l-emerald-400 bg-emerald-950/40'
                  : 'border-l-2 border-l-transparent hover:border-l-slate-600 hover:bg-slate-800/60',
              ]"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="text-sm font-semibold" :class="store.selectedReport?.id === report.id ? 'text-emerald-300' : 'text-slate-200 group-hover:text-white'">
                    📅 {{ report.report_week }}
                  </p>
                  <p class="mt-1 text-xs text-slate-500 truncate">
                    {{ formatDate(report.created_at) }} 생성
                  </p>
                  <p class="mt-1.5 text-xs text-slate-600 line-clamp-2">
                    {{ extractPreview(report.report_content) }}
                  </p>
                </div>
                <svg
                  v-if="store.selectedReport?.id === report.id"
                  class="mt-0.5 h-4 w-4 shrink-0 text-emerald-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            </li>
          </ul>
        </aside>

        <!-- 우측: 리포트 본문 뷰어 -->
        <main class="flex flex-col overflow-hidden rounded-xl border border-slate-700/50 bg-slate-900 shadow-xl">

          <!-- 리포트 미선택 상태 -->
          <div
            v-if="!store.selectedReport"
            class="flex flex-1 flex-col items-center justify-center gap-4 p-12 text-center"
          >
            <div class="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-emerald-900/40 to-teal-900/40 ring-1 ring-emerald-700/30">
              <svg class="h-10 w-10 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
            </div>
            <div>
              <p class="text-lg font-semibold text-slate-300">리포트를 선택하세요</p>
              <p class="mt-1 text-sm text-slate-500">좌측 목록에서 주차를 클릭하면 AI 분석 내용이 표시됩니다.</p>
            </div>
          </div>

          <!-- 리포트 본문 -->
          <template v-else>
            <!-- 뷰어 헤더 -->
            <div class="flex items-center justify-between border-b border-slate-700/50 px-6 py-4">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-500">Weekly Report</p>
                <h2 class="mt-1 text-lg font-bold text-white">{{ store.selectedReport.report_week }}</h2>
                <p class="mt-0.5 text-xs text-slate-500">생성일: {{ formatDate(store.selectedReport.created_at) }}</p>
              </div>
              <div class="flex items-center gap-2">
                <span class="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-950/50 px-3 py-1 text-xs font-semibold text-emerald-400">
                  <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  AI 생성
                </span>
              </div>
            </div>

            <!-- 마크다운 렌더링 영역 -->
            <div class="flex-1 overflow-y-auto p-6 lg:p-8">
              <article
                class="markdown-report prose prose-invert max-w-none"
                v-html="renderedMarkdown"
              ></article>
            </div>
          </template>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { marked } from 'marked'
import { useAgentStore } from '../stores/agentStore'

const store = useAgentStore()

// 마운트 시 리포트 목록 로드
onMounted(() => {
  store.fetchWeeklyReports()
})

// 선택된 리포트 마크다운 → HTML 변환
const renderedMarkdown = computed(() => {
  if (!store.selectedReport?.report_content) return ''
  return marked.parse(store.selectedReport.report_content)
})

// 날짜 포맷팅
function formatDate(isoString) {
  if (!isoString) return '날짜 없음'
  const d = new Date(isoString)
  return d.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 리포트 마크다운에서 첫 2줄 미리보기 추출
function extractPreview(content) {
  if (!content) return ''
  return content
    .replace(/#{1,6}\s/g, '')
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/`/g, '')
    .replace(/>\s/g, '')
    .trim()
    .split('\n')
    .filter(l => l.trim())
    .slice(0, 2)
    .join(' ')
    .slice(0, 100)
}

async function handleGenerate() {
  await store.generateWeeklyReportToArchive()
}
</script>

<style scoped>
/* 마크다운 리포트 커스텀 스타일 */
.markdown-report :deep(h1),
.markdown-report :deep(h2),
.markdown-report :deep(h3) {
  color: #34d399;
  border-bottom: 1px solid rgba(52, 211, 153, 0.15);
  padding-bottom: 0.4rem;
  margin-top: 1.6rem;
  margin-bottom: 0.8rem;
  font-weight: 700;
}

.markdown-report :deep(h1) {
  font-size: 1.35rem;
}

.markdown-report :deep(h2) {
  font-size: 1.1rem;
  color: #6ee7b7;
}

.markdown-report :deep(h3) {
  font-size: 0.95rem;
  color: #a7f3d0;
  border-bottom: none;
}

.markdown-report :deep(p) {
  color: #cbd5e1;
  line-height: 1.75;
  margin-bottom: 0.75rem;
}

.markdown-report :deep(ul),
.markdown-report :deep(ol) {
  color: #94a3b8;
  padding-left: 1.4rem;
  margin-bottom: 0.75rem;
}

.markdown-report :deep(li) {
  margin-bottom: 0.3rem;
  line-height: 1.65;
}

.markdown-report :deep(strong) {
  color: #e2e8f0;
  font-weight: 600;
}

.markdown-report :deep(blockquote) {
  border-left: 3px solid #10b981;
  background: rgba(16, 185, 129, 0.07);
  padding: 0.6rem 1rem;
  border-radius: 0 0.375rem 0.375rem 0;
  margin: 0.75rem 0;
  color: #a7f3d0;
  font-style: normal;
}

.markdown-report :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.875rem;
}

.markdown-report :deep(th) {
  background: rgba(52, 211, 153, 0.12);
  color: #6ee7b7;
  font-weight: 600;
  padding: 0.5rem 0.75rem;
  border: 1px solid rgba(100, 116, 139, 0.3);
  text-align: left;
}

.markdown-report :deep(td) {
  padding: 0.4rem 0.75rem;
  border: 1px solid rgba(100, 116, 139, 0.2);
  color: #94a3b8;
}

.markdown-report :deep(tr:nth-child(even) td) {
  background: rgba(30, 41, 59, 0.5);
}

.markdown-report :deep(code) {
  background: rgba(30, 41, 59, 0.8);
  color: #10b981;
  padding: 0.1rem 0.4rem;
  border-radius: 0.25rem;
  font-size: 0.82rem;
}

.markdown-report :deep(hr) {
  border-color: rgba(100, 116, 139, 0.25);
  margin: 1.25rem 0;
}
</style>
