<template>
  <section class="flex h-full flex-col bg-white border-t-0 border-transparent overflow-hidden">
  
    <Transition name="banner-slide">
      <div
        v-if="store.isRagActive"
        class="mx-5 mt-4 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-slate-700"
      >
        <div class="flex items-center gap-3">
          <div class="h-9 w-9 rounded-md bg-white grid place-items-center text-lg">🔎</div>
          <div>
            <p class="text-sm font-semibold text-slate-900">농진청 가이드북 DB 탐색 중</p>
            <p class="text-xs text-slate-500 mt-1">ChromaDB 벡터 검색 기반</p>
          </div>
        </div>
      </div>
    </Transition>

    <div ref="chatContainerRef" class="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4 min-h-0">
      <div v-if="store.chatHistory.length === 0" class="flex flex-1 flex-col items-center justify-center text-center py-8 gap-4">
        <div class="w-12 h-12 rounded-lg border border-slate-200 grid place-items-center text-slate-400 bg-slate-50 shadow-sm">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="h-5 w-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501c1.153-.086 2.294-.213 3.423-.379 1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
          </svg>
        </div>
        <div>
          <p class="text-sm font-semibold text-slate-900">스마트팜 에이전트</p>
          <p class="mt-2 text-xs text-slate-500 leading-relaxed">온실 환경 질문으로 실시간 진단 및 제어 명령을 생성합니다.</p>
        </div>
        <div class="grid w-full max-w-2xl gap-2">
          <button
            v-for="hint in QUICK_HINTS"
            :key="hint"
            type="button"
            class="rounded-md border border-slate-200 bg-white px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-50"
            @click="$emit('quickHint', hint)"
          >{{ hint }}</button>
        </div>
      </div>

      <TransitionGroup name="msg-slide" tag="div" class="flex flex-col gap-4">
        <div
          v-for="(msg, idx) in store.chatHistory"
          :key="idx"
          :class="['flex flex-col gap-2', msg.role === 'user' ? 'items-end' : 'items-start']"
        >
          <div class="text-[10px] text-slate-400">
            {{ msg.role === 'user' ? '나' : '에이전트' }} · {{ formatTime(msg.timestamp) }}
          </div>
          <div :class="['max-w-[85%] rounded-md border px-4 py-3', msg.role === 'user' ? 'bg-slate-100 border-slate-200 text-slate-900' : 'bg-slate-50 border-slate-200 text-slate-900']">
            <div v-if="msg.isFallback" class="mb-2 inline-flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-1 text-[11px] font-medium text-amber-700">
              오프라인 시연 모드
            </div>
            
            <!-- 답변 출처 배지 추가 -->
            <div v-if="msg.role === 'agent' && msg.answerSource" class="mb-3 flex flex-wrap gap-2">
              <span v-if="msg.answerSource === 'RAG'" class="inline-flex items-center gap-1.5 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700 shadow-sm">
                <span class="relative flex h-2 w-2">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                공인 농업 지침 기반
              </span>
              <span v-else-if="msg.answerSource === 'LLM_PARAMETRIC'" class="inline-flex items-center gap-1.5 rounded-md border border-blue-200 bg-blue-50 px-2 py-1 text-[10px] font-bold text-blue-700 shadow-sm">
                <span class="text-blue-500">ℹ️</span> AI 일반 지식 기반
              </span>
              <span v-else-if="msg.answerSource === 'LLM_ERROR'" class="inline-flex items-center gap-1.5 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-[10px] font-bold text-rose-700 shadow-sm">
                ⚠️ 시스템 통신 오류
              </span>
            </div>

            <div class="prose prose-sm text-slate-800" v-html="renderMarkdown(msg.text)"></div>
          </div>
        </div>
      </TransitionGroup>

      <div v-if="store.isPageLoading" class="flex items-center gap-3 text-slate-500">
        <span class="inline-flex h-3 w-3 rounded-full bg-[#2F6D43] animate-pulse"></span>
        <span class="text-sm">에이전트 추론 중...</span>
      </div>
    </div>

    <div class="px-5 pb-5 pt-3 shrink-0 border-t border-slate-200 bg-white">
      <div class="flex items-end gap-3">
        <textarea
          id="chat-input"
          ref="textareaRef"
          v-model="inputText"
          placeholder="온실 상태를 문의하세요..."
          rows="1"
          class="flex-1 min-h-[48px] resize-none rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-[#2F6D43] focus:outline-none focus:ring-1 focus:ring-[#2F6D43]/20"
          :disabled="store.isPageLoading"
          @keydown.enter.prevent="handleEnter($event)"
          @input="autoResize"
        ></textarea>

        <button
          id="send-button"
          type="button"
          :disabled="store.isPageLoading || !inputText.trim()"
          class="shrink-0 rounded-md bg-[#2F6D43] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#254f38] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500"
          @click="handleSend"
        >
          <template v-if="store.isPageLoading">
            <span class="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-white/60 border-t-white"></span>
          </template>
          <template v-else>전송</template>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useAgentStore } from '../stores/agentStore'

const store = useAgentStore()
const inputText = ref('')
const textareaRef = ref(null)
const chatContainerRef = ref(null)

const QUICK_HINTS = [
  '지난 24시간 동안 작물이 스트레스를 받았을 만한 환경 변화가 있었는지 분석해줘',
  '내일 비 예보가 있어. 일조량 부족에 대비해서 오늘 어떤 조치를 해야 할까?',
  '토마토 당도를 높이고 싶어. 농진청 가이드에 나온 수분 조절법 알려줘',
  '요즘 아침마다 안개가 심하네. 온실 내부 습도를 어떻게 관리해야 작물에 무리가 안 갈까?'
]

const emit = defineEmits(['quickHint'])

function scrollToBottom() {
  nextTick(() => {
    chatContainerRef.value?.scrollTo({
      top: chatContainerRef.value.scrollHeight,
      behavior: 'smooth',
    })
  })
}

watch(() => store.chatHistory.length, scrollToBottom)
watch(() => store.isPageLoading, scrollToBottom)

function handleEnter(e) { if (!e.shiftKey) handleSend() }
function autoResize() {
  const el = textareaRef.value
  if (el) { el.style.height = 'auto'; el.style.height = `${Math.min(el.scrollHeight, 128)}px` }
}
async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  if (textareaRef.value) textareaRef.value.style.height = 'auto'
  await store.sendAgentQuery(text)
}

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>')
    .replace(/`(.+?)`/g, '<code class="font-mono text-slate-700 bg-slate-100 px-1 rounded text-[11px]">$1</code>')
    .replace(/\n/g, '<br>')
}
function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.banner-slide-enter-active, .banner-slide-leave-active { transition: all 0.35s ease; overflow: hidden; }
.banner-slide-enter-from, .banner-slide-leave-to       { opacity: 0; transform: translateY(-6px); max-height: 0; }
.banner-slide-enter-to, .banner-slide-leave-from       { max-height: 80px; }

.msg-slide-enter-active { transition: all 0.35s ease-out; }
.msg-slide-leave-active { transition: all 0.2s ease; position: absolute; width: 100%; }
.msg-slide-enter-from   { opacity: 0; transform: translateY(12px); }
.msg-slide-leave-to     { opacity: 0; }
</style>