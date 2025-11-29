<template>
  <div class="flex h-screen w-screen overflow-hidden bg-slate-50 font-sans text-slate-800">
    <!-- 1. 左侧侧边栏 -->
    <AppSidebar />

    <!-- 2. 右侧聊天区 -->
    <ChatWindow />

    <!-- 3. 文档结构树弹窗 (Overlay) -->
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div v-if="store.state.viewingDocTree" class="absolute top-20 left-0 right-0 z-50 flex justify-center px-4 pointer-events-none">
        <!-- 宽度调整为 max-w-5xl 以提供更大的编辑视野 -->
        <div class="bg-white rounded-xl shadow-xl border border-indigo-100 p-4 w-full max-w-7xl pointer-events-auto">
          <div class="flex justify-between items-center mb-4 border-b border-slate-100 pb-2">
            <h3 class="font-bold text-indigo-900 flex items-center">
              <i class="fa-solid fa-sitemap mr-2"></i>
              {{ store.state.viewingDocTree.name }}
              <span class="ml-2 text-xs bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-full">编辑模式</span>
            </h3>
            <button @click="store.setViewingDoc(null)" class="text-slate-400 hover:text-slate-600 transition-colors">
              <i class="fa-solid fa-xmark text-xl"></i>
            </button>
          </div>

          <!-- 核心修改：这里替换成了新的交互式组件 -->
          <InteractiveTree />
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import AppSidebar from './components/AppSidebar.vue';
import ChatWindow from './components/ChatWindow.vue';
// 1. 引入我们刚写好的 Vue Flow 组件
import InteractiveTree from './components/InteractiveTree.vue';
import { useModoraStore } from './composables/useModoraStore';

const store = useModoraStore();

// 注意：Mermaid 相关的代码和 import 已经被移除了，因为 App.vue 现在不需要它们了
// (ChatWindow 内部仍然在使用 MermaidDiagram，互不影响)
</script>

<style>
/* 确保没有任何全局样式冲突 */
</style>
