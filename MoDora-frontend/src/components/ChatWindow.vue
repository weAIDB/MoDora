<template>
  <main class="flex-1 flex flex-col h-full bg-slate-50 relative">
    <!-- 顶部 -->
    <header class="h-16 border-b border-slate-200 bg-white px-6 flex items-center justify-between shadow-sm">
      <h1 class="font-bold text-slate-800">Modora 助手</h1>
    </header>

    <!-- 消息列表 -->
    <div id="chat-container" class="flex-1 overflow-y-auto p-6 space-y-6">
      <div v-for="(msg, idx) in store.state.messages" :key="idx"
           class="flex w-full"
           :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">

        <!-- 头像 -->
        <div v-if="msg.role === 'assistant'" class="w-8 h-8 rounded-full bg-white border border-indigo-100 flex items-center justify-center text-indigo-600 mr-2 mt-1 shadow-sm flex-shrink-0">
           <i class="fa-solid fa-robot"></i>
        </div>

        <div class="max-w-[85%] lg:max-w-[75%]">
          <!-- 消息气泡 -->
          <div class="p-4 rounded-2xl text-sm shadow-sm border"
               :class="msg.role === 'user' ? 'bg-indigo-600 text-white border-indigo-600 rounded-br-none' : 'bg-white text-slate-700 border-slate-200 rounded-bl-none'">
            <div class="whitespace-pre-wrap leading-relaxed">{{ msg.content }}<span v-if="msg.isTyping" class="inline-block w-2 h-4 bg-indigo-500 ml-1 animate-pulse align-middle"></span></div>
          </div>

          <!-- 核心修复：引用来源卡片 (PDF Source Cards) -->
          <!-- 只有当 msg.citations 存在且不为空时才显示 -->
          <div v-if="!msg.isTyping && msg.citations && msg.citations.length > 0" class="mt-3 grid grid-cols-1 gap-2 animate-fade-in">
             <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-1 flex items-center">
               <i class="fa-solid fa-quote-left mr-1"></i> 参考来源
             </div>

             <div
                v-for="(citation, cIdx) in msg.citations"
                :key="cIdx"
                @click="store.openPdf(citation.fileId, citation.page, citation.bboxes || [])"
                class="bg-white border border-slate-200 rounded-lg p-3 hover:border-indigo-400 hover:shadow-md transition-all cursor-pointer group flex items-start"
             >
                <!-- PDF 图标 -->
                <div class="bg-red-50 text-red-500 rounded p-2 mr-3 group-hover:bg-red-100 transition flex-shrink-0">
                  <i class="fa-regular fa-file-pdf text-lg"></i>
                </div>

                <!-- 来源详情 -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between mb-1">
                    <span class="text-xs font-bold text-slate-700 group-hover:text-indigo-600 transition truncate mr-2">
                      {{ citation.fileName }}
                    </span>
                    <span class="bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded text-[10px] whitespace-nowrap font-medium group-hover:bg-indigo-50 group-hover:text-indigo-600">
                      第 {{ citation.page }} 页
                    </span>
                  </div>
                  <div class="text-[11px] text-slate-500 leading-snug line-clamp-2 bg-slate-50/50 p-1 rounded group-hover:bg-transparent">
                    “{{ citation.snippet }}”
                  </div>
                </div>

                <!-- 跳转箭头 -->
                <div class="ml-2 text-slate-300 group-hover:text-indigo-500 self-center">
                  <i class="fa-solid fa-chevron-right text-xs"></i>
                </div>
             </div>
          </div>
        </div>
      </div>

      <!-- 思考中状态 -->
      <div v-if="store.state.isThinking" class="flex w-full justify-start animate-fade-in">
        <div class="w-8 h-8 rounded-full bg-white border border-indigo-100 flex items-center justify-center text-indigo-600 mr-2 mt-1 shadow-sm flex-shrink-0">
           <i class="fa-solid fa-robot"></i>
        </div>
        <div class="max-w-[85%] lg:max-w-[75%]">
          <div class="p-4 rounded-2xl text-sm shadow-sm border bg-white text-slate-700 border-slate-200 rounded-bl-none">
             <div class="flex items-center space-x-1 h-5">
                <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
             </div>
             <span class="text-xs text-slate-400 mt-2 block font-medium">深度思考中...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="p-4 bg-white border-t border-slate-200">
      <div class="relative max-w-4xl mx-auto">
        <input
          v-model="store.state.inputMessage"
          @keyup.enter="handleSend"
          :disabled="store.state.isThinking"
          type="text"
          class="w-full pl-4 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all placeholder:text-slate-400"
          placeholder="请输入您的问题..."
        >
        <button
          @click="handleSend"
          :disabled="!store.state.inputMessage || store.state.isThinking"
          class="absolute right-2 top-2 p-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors shadow-sm">
          <i class="fa-solid fa-paper-plane"></i>
        </button>
      </div>
    </div>
  </main>
</template>

<script setup>
import { nextTick, watch } from 'vue';
import { useModoraStore } from '../composables/useModoraStore';

// 注意：这里不需要引入 MermaidDiagram 了，因为我们要专注显示 PDF 卡片

const store = useModoraStore();

const handleSend = () => {
  store.sendMessage();
};

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    const container = document.getElementById('chat-container');
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    }
  });
};

watch(() => [store.state.messages.length, store.state.isThinking], scrollToBottom, { deep: true });
</script>

<style scoped>
@keyframes fade-in {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fade-in 0.4s ease-out forwards;
}
</style>
