<template>
  <!-- 
    Main Container:
    1. Remove bg-slate-50, use transparent background (since body already has gradient)
    2. Add padding (p-4), make main area float above background for better layering
  -->
  <div class="flex h-screen w-screen overflow-hidden p-4 md:p-6 gap-4 md:gap-6">
    
    <!-- 1. Left Sidebar -->
    <!-- Add glass-panel class for frosted glass and rounded corners -->
    <AppSidebar 
      class="glass-panel w-full md:w-72 shrink-0 h-full border-none shadow-2xl" 
      @open-settings="showSettings = true"
    />

    <!-- 2. Center Chat Area -->
    <div class="glass-panel flex-1 flex flex-col min-w-0 relative overflow-hidden border-none shadow-2xl">
      <ChatWindow />
    </div>

    <!-- 3. Right General Sidebar (PDF or Tree) -->
    <transition name="slide-right">
      <div
        v-if="store.state.viewingPdf || store.state.viewingDocTree"
        class="glass-panel w-[45%] h-full z-20 relative flex flex-col shrink-0 overflow-hidden border-none shadow-2xl"
      >
        <!-- Sidebar Header (Show title only in Tree mode, PDFViewer has its own header) -->
        <div v-if="store.state.viewingDocTree" class="h-16 flex items-center justify-between px-6 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 z-10 shrink-0">
          <h3 class="font-bold text-primary-900 dark:text-primary-100 flex items-center text-sm">
            <i class="fa-solid fa-sitemap mr-2 text-primary-600 dark:text-primary-400"></i>
            {{ store.state.viewingDocTree.name }}
            <span class="ml-2 text-[10px] bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-300 px-2 py-0.5 rounded-full uppercase tracking-wide">Tree View</span>
          </h3>
          <button
            @click="store.closeSidePanel()"
            class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        <!-- PDF Close Button -->
        <button
          v-if="store.state.viewingPdf"
          @click="store.closeSidePanel()"
          class="absolute top-3 right-4 z-50 bg-white/80 hover:bg-white dark:bg-slate-800/80 dark:hover:bg-slate-700 text-slate-500 hover:text-red-500 w-8 h-8 rounded-full flex items-center justify-center transition shadow-lg backdrop-blur-sm"
          title="Close Sidebar"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>

        <!-- Content Area -->
        <div class="flex-1 overflow-hidden relative">
          <!-- A. PDF Viewer -->
          <PDFViewer
            v-if="store.state.viewingPdf"
            :key="'pdf-' + store.state.viewingPdf.url"
            :source="store.state.viewingPdf.url"
            :initial-page="store.state.viewingPdf.page"
            :file-name="store.state.viewingPdf.name"
            :highlight-bboxes="store.state.viewingPdf.bboxes"
          />

          <!-- B. Document Structure Tree (Vue Flow) -->
          <InteractiveTree
            v-else-if="store.state.viewingDocTree"
            :key="'tree-' + store.state.viewingDocTree.id"
          />
        </div>

      </div>
    </transition>

    <!-- Settings Modal -->
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
/* Right Slide Animation */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(20px); /* Slight translation, combined with opacity */
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
