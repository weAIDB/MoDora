<template>
  <main class="flex-1 flex flex-col h-full bg-transparent relative">
    <!-- 顶部 -->
    <header class="h-16 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-6 flex items-center justify-between shrink-0 z-10 rounded-t-3xl">
      <div class="flex items-center space-x-3">
        <div class="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.6)]"></div>
        <h1 class="font-bold text-slate-800 dark:text-slate-100 text-sm tracking-wide">MoDora Assistant</h1>
      </div>
      <div class="text-xs text-slate-400 font-medium">v1.1.0</div>
    </header>

    <!-- Message List -->
    <div id="chat-container" class="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar scroll-smooth pb-32">
      <!-- Welcome Message (Empty State) -->
      <div v-if="!currentMessages || currentMessages.length === 0" class="flex flex-col items-center justify-center h-full text-slate-400 opacity-60">
        <div class="w-20 h-20 rounded-3xl bg-gradient-to-br from-primary-100 to-secondary-100 dark:from-primary-900/50 dark:to-secondary-900/50 flex items-center justify-center mb-6 animate-float">
          <i class="fa-solid fa-robot text-4xl text-primary-400"></i>
        </div>
        <p class="text-sm">How can I help you?</p>
      </div>

      <template v-if="currentMessages">
        <div v-for="(msg, idx) in currentMessages" :key="idx"
             class="flex w-full group animate-fade-in"
             :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">

          <!-- AI Avatar -->
        <div v-if="msg.role === 'assistant'" class="w-10 h-10 rounded-xl bg-white dark:bg-slate-800 border border-white/50 dark:border-white/10 flex items-center justify-center text-primary-500 mr-4 mt-1 shadow-sm flex-shrink-0 backdrop-blur-sm">
           <i class="fa-solid fa-robot text-lg"></i>
        </div>

        <div class="max-w-[85%] lg:max-w-[75%] flex flex-col group/message relative" :class="msg.role === 'user' ? 'items-end' : 'items-start'">
          <!-- Message Bubble -->
          <div class="p-5 rounded-3xl text-sm shadow-sm border backdrop-blur-sm relative select-text cursor-text"
               :class="[
                 msg.role === 'user' 
                   ? 'bg-gradient-to-br from-primary-600 to-primary-700 text-white border-transparent rounded-br-sm shadow-primary-500/20' 
                   : 'bg-white/80 dark:bg-slate-800/80 text-slate-700 dark:text-slate-200 border-white/40 dark:border-white/10 rounded-bl-sm shadow-slate-200/50 dark:shadow-none'
               ]">
            <!-- Markdown Render -->
            <MarkdownRenderer 
              :content="msg.content" 
              :is-user="msg.role === 'user'" 
            />
            <span v-if="msg.isTyping" class="inline-block w-2 h-4 bg-primary-400 ml-1 animate-pulse align-middle"></span>
          
            <!-- Copy Button (Floating outside) -->
            <button 
              @click="copyToClipboard(msg.content)"
              class="absolute bottom-0 p-1.5 rounded-lg opacity-0 group-hover/message:opacity-100 transition-all duration-200 text-slate-400 hover:text-primary-500 hover:bg-white/50 dark:hover:bg-slate-700/50"
              :class="msg.role === 'user' ? '-left-8' : '-right-8'"
              title="Copy text"
            >
              <i class="fa-regular fa-copy text-xs"></i>
            </button>
          </div>

          <!-- Reference Cards (PDF Source Cards) -->
          <div v-if="!msg.isTyping && msg.citations && msg.citations.length > 0" class="mt-4 grid grid-cols-1 gap-3 w-full max-w-lg">
             <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-1 flex items-center pl-1">
               <i class="fa-solid fa-quote-left mr-2 text-primary-300"></i> References
             </div>

             <div
                v-for="(citation, cIdx) in msg.citations"
                :key="cIdx"
                @click="store.openPdf(citation.fileId, citation.page, citation.bboxes || [])"
                class="bg-white/60 dark:bg-slate-700/60 border border-white/60 dark:border-slate-600 rounded-xl p-3 hover:border-primary-300 dark:hover:border-primary-500 hover:bg-white dark:hover:bg-slate-700 hover:shadow-lg hover:shadow-primary-500/10 transition-all cursor-pointer group/card flex items-start backdrop-blur-sm"
             >
                <!-- PDF Icon -->
                <div class="bg-red-50 dark:bg-red-900/30 text-red-500 rounded-lg p-2.5 mr-3 group-hover/card:bg-red-100 dark:group-hover/card:bg-red-900/50 transition flex-shrink-0">
                  <i class="fa-regular fa-file-pdf text-lg"></i>
                </div>

                <!-- Source Details -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between mb-1.5">
                    <span class="text-xs font-bold text-slate-700 dark:text-slate-200 group-hover/card:text-primary-700 dark:group-hover/card:text-primary-400 transition truncate mr-2">
                      {{ citation.fileName }}
                    </span>
                    <span class="bg-slate-100/80 dark:bg-slate-600/50 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-md text-[10px] whitespace-nowrap font-medium group-hover/card:bg-primary-50 dark:group-hover/card:bg-primary-900/30 group-hover/card:text-primary-600 dark:group-hover/card:text-primary-400">
                      Page {{ citation.page }}
                    </span>
                  </div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 leading-snug line-clamp-2 bg-slate-50/50 dark:bg-slate-800/50 p-1.5 rounded-md group-hover/card:bg-transparent">
                    “{{ citation.snippet }}”
                  </div>
                </div>

                <!-- Jump Arrow -->
                <div class="ml-2 text-slate-300 dark:text-slate-500 group-hover/card:text-primary-500 dark:group-hover/card:text-primary-400 self-center transition-transform group-hover/card:translate-x-1">
                  <i class="fa-solid fa-chevron-right text-xs"></i>
                </div>
             </div>
          </div>
        </div>
      </div>
      </template>

      <!-- Thinking State -->
      <div v-if="store.state.isThinking" class="flex w-full justify-start animate-fade-in">
        <div class="w-10 h-10 rounded-xl bg-white dark:bg-slate-800 border border-white/50 dark:border-white/10 flex items-center justify-center text-primary-500 mr-4 mt-1 shadow-sm flex-shrink-0 backdrop-blur-sm">
           <i class="fa-solid fa-robot text-lg"></i>
        </div>
        <div class="max-w-[85%] lg:max-w-[75%]">
          <div class="p-5 rounded-3xl text-sm shadow-sm border bg-white/80 dark:bg-slate-800/80 text-slate-700 dark:text-slate-200 border-white/40 dark:border-white/10 rounded-bl-sm backdrop-blur-sm">
             <div class="flex items-center space-x-1.5 h-6">
                <div class="w-2.5 h-2.5 bg-primary-300 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-2.5 h-2.5 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-2.5 h-2.5 bg-primary-500 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
             </div>
             <span class="text-xs text-primary-400 mt-2 block font-medium tracking-wide">Thinking of the best answer...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Input Area (Floating Capsule Style) -->
    <div class="absolute bottom-6 left-0 right-0 px-6 z-20">
      <div class="max-w-4xl mx-auto relative group">
        <!-- Background Glow (Wraps input only) -->
        <div class="absolute -inset-1 bg-gradient-to-r from-primary-400 to-secondary-400 rounded-2xl opacity-20 group-focus-within:opacity-40 blur transition duration-500 h-[calc(100%-20px)]"></div>
        
        <div class="relative bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 dark:border-white/10 flex items-center p-2 transition-all group-focus-within:bg-white dark:group-focus-within:bg-slate-900 group-focus-within:shadow-2xl group-focus-within:scale-[1.01]">
          <input
            v-model="store.state.inputMessage"
            @keyup.enter="handleSend"
            :disabled="store.state.isThinking"
            type="text"
            class="flex-1 bg-transparent border-none focus:ring-0 text-slate-700 dark:text-slate-200 placeholder:text-slate-400 px-4 py-3 text-sm font-medium"
            placeholder="Ask something..."
          >
          <button
            @click="handleSend"
            :disabled="!store.state.inputMessage || store.state.isThinking"
            class="w-11 h-11 shrink-0 bg-gradient-to-br from-primary-600 to-primary-500 text-white rounded-xl hover:shadow-lg hover:shadow-primary-500/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none transition-all duration-300 transform active:scale-95 flex items-center justify-center"
          >
            <i class="fa-solid fa-arrow-up text-lg font-bold" style="-webkit-text-stroke: 1px white;"></i>
          </button>
        </div>
        
        <div class="text-center mt-2 relative z-20">
           <span class="text-[10px] text-slate-400 font-medium">MoDora AI can make mistakes. Check important info.</span>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup>
import { nextTick, watch, onMounted, computed } from 'vue';
import { useModoraStore } from '../composables/useModoraStore';
import MarkdownRenderer from './MarkdownRenderer.vue';

const store = useModoraStore();

// Calculate current session message list
const currentMessages = computed(() => {
    const session = store.getActiveSession();
    return session ? session.messages : [];
});

const scrollToBottom = async () => {
  await nextTick();
  const container = document.getElementById('chat-container');
  if (container) {
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
  }
};

const handleSend = async () => {
  if (!store.state.inputMessage.trim() || store.state.isThinking) return;
  await store.sendMessage();
  scrollToBottom();
};

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    // Add toast notification here if needed
    console.log('Copied to clipboard');
  } catch (err) {
    console.error('Failed to copy: ', err);
  }
};

// Watch message list changes, auto scroll to bottom
watch(() => currentMessages.value.length, () => {
  scrollToBottom();
});

onMounted(() => {
  scrollToBottom();
});
</script>
