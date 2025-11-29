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
        <div v-if="msg.role === 'assistant'" class="w-8 h-8 rounded-full bg-white border border-indigo-100 flex items-center justify-center text-indigo-600 mr-2 mt-1">
           <i class="fa-solid fa-robot"></i>
        </div>

        <div class="max-w-[80%]">
          <!-- 气泡 -->
          <div class="p-4 rounded-2xl text-sm shadow-sm"
               :class="msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-white text-slate-700 border border-slate-200 rounded-bl-none'">
            <div class="whitespace-pre-wrap leading-relaxed">{{ msg.content }}<span v-if="msg.isTyping" class="animate-pulse">▋</span></div>
          </div>

          <!-- RAG 可视化图表 (仅 AI 回复且有数据时显示) -->
          <div v-if="msg.graphData" class="mt-2 border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm">
            <div class="bg-slate-50 px-3 py-1 text-xs text-slate-500 border-b border-slate-100">检索链路可视化</div>
            <MermaidDiagram :chart-code="msg.graphData" />
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
          :disabled="store.state.isThinking || store.state.isTyping"
          type="text"
          class="w-full pl-4 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all"
          placeholder="请输入您的问题..."
        >
        <button
          @click="handleSend"
          :disabled="!store.state.inputMessage || store.state.isThinking"
          class="absolute right-2 top-2 p-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors">
          <i class="fa-solid fa-paper-plane"></i>
        </button>
      </div>
    </div>

  </main>
</template>

<script setup>
import { nextTick, watch } from 'vue';
import { useModoraStore } from '../composables/useModoraStore';
import MermaidDiagram from './MermaidDiagram.vue';

const store = useModoraStore();

const handleSend = () => {
  store.sendMessage();
};

// 自动滚动到底部
watch(() => store.state.messages.length, () => {
  nextTick(() => {
    const container = document.getElementById('chat-container');
    if (container) container.scrollTop = container.scrollHeight;
  });
}, { deep: true });
</script>
