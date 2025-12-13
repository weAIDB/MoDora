<template>
  <div class="flex h-screen w-screen overflow-hidden bg-slate-50 font-sans text-slate-800">
    <!-- 1. 左侧侧边栏 (保持不变) -->
    <AppSidebar />

    <!-- 2. 中间聊天区 (自适应宽度) -->
    <div class="flex-1 flex flex-col min-w-0 bg-white relative">
      <ChatWindow />
    </div>

    <!-- 3. 右侧通用侧边栏 (PDF 或 Tree) -->
    <transition name="slide-right">
      <div
        v-if="store.state.viewingPdf || store.state.viewingDocTree"
        class="w-[45%] h-full border-l border-slate-200 bg-white shadow-xl z-20 relative flex flex-col shrink-0"
      >
        <!-- 侧边栏头部 (仅在 Tree 模式下显示标题，PDFViewer 自带头部) -->
        <div v-if="store.state.viewingDocTree" class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-white z-10 shrink-0">
          <h3 class="font-bold text-indigo-900 flex items-center text-sm">
            <i class="fa-solid fa-sitemap mr-2"></i>
            {{ store.state.viewingDocTree.name }}
            <span class="ml-2 text-[10px] bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-full uppercase tracking-wide">Graph View</span>
          </h3>
          <button
            @click="store.closeSidePanel()"
            class="text-slate-400 hover:text-slate-600 transition-colors w-6 h-6 flex items-center justify-center rounded-md hover:bg-slate-100"
          >
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        <!-- PDF 关闭按钮 (PDFViewer 内部没有统一关闭，我们悬浮在角落) -->
        <button
          v-if="store.state.viewingPdf"
          @click="store.closeSidePanel()"
          class="absolute top-2.5 right-3 z-50 bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-red-500 w-8 h-8 rounded-full flex items-center justify-center transition shadow-sm border border-slate-200"
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

  </div>
</template>

<script setup>
import AppSidebar from './components/AppSidebar.vue';
import ChatWindow from './components/ChatWindow.vue';
import InteractiveTree from './components/InteractiveTree.vue';
import PDFViewer from './components/PDFViewer.vue';
import { useModoraStore } from './composables/useModoraStore';

const store = useModoraStore();
</script>

<style>
/* 右侧滑入动画 */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); /* 更平滑的曲线 */
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
  width: 0 !important;
  opacity: 0.5;
}

.slide-right-enter-to,
.slide-right-leave-from {
  transform: translateX(0);
  width: 45%;
  opacity: 1;
}
</style>
