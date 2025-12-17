<template>
  <!-- 
    整体容器：
    1. 移除 bg-slate-50，改用透明背景（因为 body 已经有了渐变）
    2. 增加 padding (p-4)，让主要区域悬浮在背景之上，更有层次感
  -->
  <div class="flex h-screen w-screen overflow-hidden p-4 md:p-6 gap-4 md:gap-6">
    
    <!-- 1. 左侧侧边栏 -->
    <!-- 添加 glass-panel 类，实现磨砂和圆角 -->
    <AppSidebar 
      class="glass-panel w-full md:w-72 shrink-0 h-full border-none shadow-2xl" 
      @open-settings="showSettings = true"
    />

    <!-- 2. 中间聊天区 -->
    <div class="glass-panel flex-1 flex flex-col min-w-0 relative overflow-hidden border-none shadow-2xl">
      <ChatWindow />
    </div>

    <!-- 3. 右侧通用侧边栏 (PDF 或 Tree) -->
    <transition name="slide-right">
      <div
        v-if="store.state.viewingPdf || store.state.viewingDocTree"
        class="glass-panel w-[45%] h-full z-20 relative flex flex-col shrink-0 overflow-hidden border-none shadow-2xl"
      >
        <!-- 侧边栏头部 (仅在 Tree 模式下显示标题，PDFViewer 自带头部) -->
        <div v-if="store.state.viewingDocTree" class="h-16 flex items-center justify-between px-6 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 z-10 shrink-0">
          <h3 class="font-bold text-primary-900 dark:text-primary-100 flex items-center text-sm">
            <i class="fa-solid fa-sitemap mr-2 text-primary-600 dark:text-primary-400"></i>
            {{ store.state.viewingDocTree.name }}
            <span class="ml-2 text-[10px] bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-300 px-2 py-0.5 rounded-full uppercase tracking-wide">Graph View</span>
          </h3>
          <button
            @click="store.closeSidePanel()"
            class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        <!-- PDF 关闭按钮 -->
        <button
          v-if="store.state.viewingPdf"
          @click="store.closeSidePanel()"
          class="absolute top-3 right-4 z-50 bg-white/80 hover:bg-white dark:bg-slate-800/80 dark:hover:bg-slate-700 text-slate-500 hover:text-red-500 w-8 h-8 rounded-full flex items-center justify-center transition shadow-lg backdrop-blur-sm"
          title="关闭侧边栏"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>

        <!-- 内容区域 -->
        <div class="flex-1 overflow-hidden relative">
          <!-- A. PDF 阅读器 -->
          <PDFViewer
            v-if="store.state.viewingPdf"
            :key="'pdf-' + store.state.viewingPdf.url"
            :source="store.state.viewingPdf.url"
            :initial-page="store.state.viewingPdf.page"
            :file-name="store.state.viewingPdf.name"
            :highlight-bboxes="store.state.viewingPdf.bboxes"
          />

          <!-- B. 文档结构树 (Vue Flow) -->
          <InteractiveTree
            v-else-if="store.state.viewingDocTree"
            :key="'tree-' + store.state.viewingDocTree.id"
          />
        </div>

      </div>
    </transition>

    <!-- 设置弹窗 -->
    <SettingsModal :is-open="showSettings" @close="showSettings = false" />

  </div>
</template>

<script setup>
import { ref } from 'vue';
import AppSidebar from './components/AppSidebar.vue';
import ChatWindow from './components/ChatWindow.vue';
import InteractiveTree from './components/InteractiveTree.vue';
import PDFViewer from './components/PDFViewer.vue';
import SettingsModal from './components/SettingsModal.vue';
import { useModoraStore } from './composables/useModoraStore';

const store = useModoraStore();
const showSettings = ref(false);
</script>

<style>
/* 右侧滑入动画 */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(20px); /* 稍微平移即可，配合 opacity */
  width: 0 !important;
  opacity: 0;
}

.slide-right-enter-to,
.slide-right-leave-from {
  transform: translateX(0);
  width: 45%;
  opacity: 1;
}
</style>
