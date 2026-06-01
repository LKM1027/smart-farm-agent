<template>
  <div class="min-h-screen bg-slate-50 text-slate-950 flex flex-col">
    <!-- 상단 헤더 (GNB) -->
    <header class="border-b border-slate-200 bg-white px-6 py-4 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 sticky top-0 z-30">
      <div class="flex flex-col sm:flex-row sm:items-center gap-6 lg:gap-8">
        <!-- 로고 -->
        <div class="flex items-center gap-3">
          <img src="./assets/logo2.png" alt="SmartFarm CPS Logo" class="h-12 w-auto object-contain drop-shadow-sm" />
          <div>
            <p class="text-lg font-bold tracking-tight text-slate-900">SmartFarm CPS</p>
            <p class="text-xs font-medium text-slate-500 opacity-75">AI 지능형 관제 시스템</p>
          </div>
        </div>

        <!-- GNB 네비게이션 -->
        <nav class="flex items-center gap-1 sm:border-l sm:border-slate-200 sm:pl-6 lg:pl-8">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="px-4 py-2 text-sm font-semibold rounded-md transition-colors"
            :class="route.path === item.path
              ? 'bg-emerald-50 text-emerald-700'
              : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'"
          >
            {{ item.label }}
          </router-link>
        </nav>
      </div>

      <!-- 상태 표시줄 -->
      <div class="flex items-center gap-3">
        <div class="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm">
          <span class="font-mono">{{ currentTime }}</span>
        </div>
      </div>
    </header>

    <!-- 메인 콘텐츠 영역 -->
    <main class="flex-1 w-full relative">
      <div class="p-6">
        <router-view />
      </div>
    </main>

    <!-- 에이전트 추론 로딩 오버레이 -->
    <Transition name="overlay-fade">
      <div v-if="store.isPageLoading" class="fixed inset-0 z-40 flex items-center justify-center bg-slate-50/75 backdrop-blur-sm">
        <div class="rounded-xl border border-slate-200 bg-white p-8 shadow-xl">
          <div class="flex flex-col items-center gap-4">
            <div class="h-12 w-12 rounded-full border-4 border-slate-200 border-t-emerald-600 animate-spin"></div>
            <p class="text-base font-bold text-slate-900">에이전트 추론 중...</p>
            <p class="text-sm font-medium text-slate-500">LangGraph 워크플로우 실행 중</p>
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

const currentTime = ref('')
let clockTimer = null

function updateClock() {
  currentTime.value = new Date().toLocaleTimeString('ko-KR', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  })
}

onMounted(() => { 
  updateClock()
  clockTimer = setInterval(updateClock, 1000) 
})

onUnmounted(() => {
  clearInterval(clockTimer)
})

const navItems = [
  { path: '/', label: '통합 대시보드' },
  { path: '/reports', label: 'AI 리포트 아카이브' },
]
</script>

<style scoped>
:deep(.chat-message-content),
:deep(.report-content),
.whitespace-pre-wrap {
    white-space: pre-wrap;
    word-break: break-word;
}
.overlay-fade-enter-active, .overlay-fade-leave-active { transition: opacity 0.4s ease; }
.overlay-fade-enter-from, .overlay-fade-leave-to       { opacity: 0; }
</style>
