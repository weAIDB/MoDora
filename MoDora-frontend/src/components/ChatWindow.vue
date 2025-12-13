<template>
  <main class="flex-1 flex flex-col h-full bg-transparent relative">
    <!-- 顶部 -->
    <header class="h-16 border-b border-white/20 bg-white/40 backdrop-blur-sm px-6 flex items-center justify-between shrink-0 z-10">
      <div class="flex items-center space-x-3">
        <div class="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.6)]"></div>
        <h1 class="font-bold text-slate-800 text-sm tracking-wide">MoDora Assistant</h1>
      </div>
      <div class="text-xs text-slate-400 font-medium">v1.1.0</div>
    </header>

    <!-- 消息列表 -->
    <div id="chat-container" class="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar scroll-smooth pb-32">
      <!-- 欢迎语 (空状态) -->
      <div v-if="store.state.messages.length === 0" class="flex flex-col items-center justify-center h-full text-slate-400 opacity-60">
        <div class="w-20 h-20 rounded-3xl bg-gradient-to-br from-primary-100 to-secondary-100 flex items-center justify-center mb-6 animate-float">
          <i class="fa-solid fa-robot text-4xl text-primary-400"></i>
        </div>
        <p class="text-sm">有什么我可以帮你的吗？</p>
      </div>

      <div v-for="(msg, idx) in store.state.messages" :key="idx"
           class="flex w-full group animate-fade-in"
           :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">

        <!-- AI 头像 -->
        <div v-if="msg.role === 'assistant'" class="w-10 h-10 rounded-xl bg-white border border-white/50 flex items-center justify-center text-primary-500 mr-4 mt-1 shadow-sm flex-shrink-0 backdrop-blur-sm">
           <i class="fa-solid fa-robot text-lg"></i>
        </div>

        <div class="max-w-[85%] lg:max-w-[75%] flex flex-col" :class="msg.role === 'user' ? 'items-end' : 'items-start'">
          <!-- 消息气泡 -->
          <div class="p-5 rounded-3xl text-sm shadow-sm border backdrop-blur-sm relative"
               :class="[
                 msg.role === 'user' 
                   ? 'bg-gradient-to-br from-primary-600 to-primary-700 text-white border-transparent rounded-br-sm shadow-primary-500/20' 
                   : 'bg-white/80 text-slate-700 border-white/40 rounded-bl-sm shadow-slate-200/50'
               ]">
            <!-- Markdown 渲染 -->
            <MarkdownRenderer 
              :content="msg.content" 
              :is-user="msg.role === 'user'" 
            />
            <span v-if="msg.isTyping" class="inline-block w-2 h-4 bg-primary-400 ml-1 animate-pulse align-middle"></span>
          </div>

          <!-- 引用来源卡片 (PDF Source Cards) -->
          <div v-if="!msg.isTyping && msg.citations && msg.citations.length > 0" class="mt-4 grid grid-cols-1 gap-3 w-full max-w-lg">
             <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-1 flex items-center pl-1">
               <i class="fa-solid fa-quote-left mr-2 text-primary-300"></i> 参考来源
             </div>

             <div
                v-for="(citation, cIdx) in msg.citations"
                :key="cIdx"
                @click="store.openPdf(citation.fileId, citation.page, citation.bboxes || [])"
                class="bg-white/60 border border-white/60 rounded-xl p-3 hover:border-primary-300 hover:bg-white hover:shadow-lg hover:shadow-primary-500/10 transition-all cursor-pointer group/card flex items-start backdrop-blur-sm"
             >
                <!-- PDF 图标 -->
                <div class="bg-red-50 text-red-500 rounded-lg p-2.5 mr-3 group-hover/card:bg-red-100 transition flex-shrink-0">
                  <i class="fa-regular fa-file-pdf text-lg"></i>
                </div>

                <!-- 来源详情 -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between mb-1.5">
                    <span class="text-xs font-bold text-slate-700 group-hover/card:text-primary-700 transition truncate mr-2">
                      {{ citation.fileName }}
                    </span>
                    <span class="bg-slate-100/80 text-slate-500 px-2 py-0.5 rounded-md text-[10px] whitespace-nowrap font-medium group-hover/card:bg-primary-50 group-hover/card:text-primary-600">
                      Page {{ citation.page }}
                    </span>
                  </div>
                  <div class="text-[11px] text-slate-500 leading-snug line-clamp-2 bg-slate-50/50 p-1.5 rounded-md group-hover/card:bg-transparent">
                    “{{ citation.snippet }}”
                  </div>
                </div>

                <!-- 跳转箭头 -->
                <div class="ml-2 text-slate-300 group-hover/card:text-primary-500 self-center transition-transform group-hover/card:translate-x-1">
                  <i class="fa-solid fa-chevron-right text-xs"></i>
                </div>
             </div>
          </div>
        </div>
      </div>

      <!-- 思考中状态 -->
      <div v-if="store.state.isThinking" class="flex w-full justify-start animate-fade-in">
        <div class="w-10 h-10 rounded-xl bg-white border border-white/50 flex items-center justify-center text-primary-500 mr-4 mt-1 shadow-sm flex-shrink-0 backdrop-blur-sm">
           <i class="fa-solid fa-robot text-lg"></i>
        </div>
        <div class="max-w-[85%] lg:max-w-[75%]">
          <div class="p-5 rounded-3xl text-sm shadow-sm border bg-white/80 text-slate-700 border-white/40 rounded-bl-sm backdrop-blur-sm">
             <div class="flex items-center space-x-1.5 h-6">
                <div class="w-2.5 h-2.5 bg-primary-300 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-2.5 h-2.5 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-2.5 h-2.5 bg-primary-500 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
             </div>
             <span class="text-xs text-primary-400 mt-2 block font-medium tracking-wide">正在思考最佳答案...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部输入区 (悬浮胶囊样式) -->
    <div class="absolute bottom-6 left-0 right-0 px-6 z-20">
      <div class="max-w-4xl mx-auto relative group">
        <!-- 背景光晕 -->
        <div class="absolute -inset-1 bg-gradient-to-r from-primary-400 to-secondary-400 rounded-2xl opacity-20 group-focus-within:opacity-40 blur transition duration-500"></div>
        
        <div class="relative bg-white/80 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 flex items-center p-2 transition-all group-focus-within:bg-white group-focus-within:shadow-2xl group-focus-within:scale-[1.01]">
          <input
            v-model="store.state.inputMessage"
            @keyup.enter="handleSend"
            :disabled="store.state.isThinking"
            type="text"
            class="flex-1 bg-transparent border-none focus:ring-0 text-slate-700 placeholder:text-slate-400 px-4 py-3 text-sm font-medium"
            placeholder="问点什么吧..."
          >
          <button
            @click="handleSend"
            :disabled="!store.state.inputMessage || store.state.isThinking"
            class="p-3 bg-gradient-to-br from-primary-600 to-primary-500 text-white rounded-xl hover:shadow-lg hover:shadow-primary-500/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none transition-all duration-300 transform active:scale-95 flex items-center justify-center aspect-square"
          >
            <i class="fa-solid fa-paper-plane"></i>
          </button>
        </div>
        
        <div class="text-center mt-2">
           <span class="text-[10px] text-slate-400 font-medium">MoDora AI can make mistakes. Check important info.</span>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup>
import { useModoraStore } from '../composables/useModoraStore';
import { nextTick, watch } from 'vue';
import MarkdownRenderer from './MarkdownRenderer.vue';

const store = useModoraStore();

const handleSend = async () => {
  if (!store.state.inputMessage.trim() || store.state.isThinking) return;
  await store.sendMessage();
};

// 自动滚动到底部
watch(
  () => store.state.messages.length,
  () => {
    nextTick(() => {
      const container = document.getElementById('chat-container');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    });
  }
);
</script>
