<template>
  <!-- 
    AppSidebar.vue 改造：
    1. 去掉外层容器的 border 和 bg (由父级 glass-panel 接管)
    2. 使用 bg-transparent 
  -->
  <aside class="flex flex-col h-full bg-transparent">
    <!-- 头部 -->
    <div class="h-16 px-6 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0 rounded-t-3xl">
      <div class="flex items-center">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white mr-3 shadow-lg shadow-primary-500/30">
          <i class="fa-solid fa-book text-lg"></i>
        </div>
        <h2 class="font-bold text-slate-800 dark:text-slate-100 text-lg tracking-tight">MoDora</h2>
      </div>
      
      <div class="flex items-center">
        <!-- 设置按钮 -->
        <button 
          @click="$emit('open-settings')"
          class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary-500 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors mr-2"
          title="Global Settings"
        >
          <i class="fa-solid fa-gear"></i>
        </button>

        <!-- 主题切换按钮 -->
        <button 
          @click="toggleTheme" 
          class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary-500 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
        >
          <i v-if="isDark" class="fa-solid fa-sun text-yellow-400"></i>
          <i v-else class="fa-solid fa-moon"></i>
        </button>
      </div>
    </div>

    <!-- 列表区 -->
    <div class="flex-1 overflow-y-auto p-4 custom-scrollbar">
      <!-- 上传按钮 -->
      <div class="mb-6">
        <div 
          @click="triggerUpload"
          class="group flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-primary-200/50 rounded-2xl cursor-pointer hover:border-primary-500 hover:bg-white/50 transition-all relative overflow-hidden"
        >
          <div v-if="!store.state.isUploading" class="text-center text-slate-400 group-hover:text-primary-600 z-10 pointer-events-none">
            <div class="w-10 h-10 rounded-full bg-primary-50 flex items-center justify-center mx-auto mb-2 group-hover:scale-110 transition-transform">
               <i class="fa-solid fa-cloud-arrow-up text-xl text-primary-400"></i>
            </div>
            <p class="text-xs font-medium">点击上传文档</p>
          </div>
          <div v-else class="text-primary-600 flex flex-col items-center w-full px-6 z-10 pointer-events-none">
            <div class="flex items-center mb-3">
              <i class="fa-solid fa-circle-notch fa-spin text-xl mr-2"></i>
              <span class="text-xs font-bold">解析中... {{ store.state.uploadProgress }}%</span>
            </div>
            <!-- Progress Bar -->
            <div class="w-full bg-primary-100 rounded-full h-2 overflow-hidden shadow-inner">
              <div 
                class="bg-gradient-to-r from-primary-500 to-secondary-500 h-2 rounded-full transition-all duration-300 ease-out shadow-[0_0_10px_rgba(139,92,246,0.5)]"
                :style="{ width: `${store.state.uploadProgress}%` }"
              ></div>
            </div>
          </div>
          <!-- 隐藏的 input -->
          <input 
            ref="fileInputRef"
            type="file" 
            class="hidden" 
            @change="onFileChange" 
            :disabled="store.state.isUploading" 
            accept=".pdf,.txt,.md"
          />
          
          <!-- 悬浮时的背景光晕 -->
          <div class="absolute inset-0 bg-gradient-to-br from-primary-50 to-secondary-50 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
        </div>
      </div>

      <div class="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent my-6"></div>

      <!-- 文件列表 -->
      <h3 class="text-[10px] font-extrabold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-4 px-2">Knowledge Base ({{ store.state.knowledgeBase.length }})</h3>
      <ul class="space-y-3">
        <li v-for="doc in store.state.knowledgeBase" :key="doc.id"
            @click="store.setActiveDoc(doc.id)"
            class="group relative flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer duration-300"
            :class="[
              store.state.activeDocId === doc.id
                ? 'bg-white dark:bg-slate-800 shadow-md border-primary-100 dark:border-primary-900 ring-1 ring-primary-100 dark:ring-primary-900/50'
                : 'bg-white/40 dark:bg-slate-800/40 border-transparent hover:bg-white dark:hover:bg-slate-800 hover:shadow-sm hover:border-white/60 dark:hover:border-slate-700'
            ]"
        >

          <!-- 文件名区域 -->
          <div class="flex items-center overflow-hidden flex-1 min-w-0 mr-2 relative z-10" :title="doc.name">
            <!-- 选中的文件图标更亮 -->
            <div 
              class="w-8 h-8 rounded-lg flex items-center justify-center mr-3 shrink-0 transition-colors"
              :class="store.state.activeDocId === doc.id ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400' : 'bg-slate-100 dark:bg-slate-700/50 text-slate-400 dark:text-slate-500 group-hover:bg-primary-50 dark:group-hover:bg-primary-900/30 group-hover:text-primary-500 dark:group-hover:text-primary-400'"
            >
              <i :class="getFileIcon(doc.type)"></i>
            </div>
            
            <div class="flex flex-col min-w-0">
              <span class="text-sm truncate select-none transition-colors font-medium"
                :class="store.state.activeDocId === doc.id ? 'text-slate-800 dark:text-slate-200' : 'text-slate-600 dark:text-slate-400'"
              >
                {{ doc.name }}
              </span>
              <!-- 选中状态的标记 -->
              <span v-if="store.state.activeDocId === doc.id" class="text-[10px] text-primary-500 dark:text-primary-400 font-bold flex items-center mt-0.5">
                <span class="w-1.5 h-1.5 bg-primary-500 dark:bg-primary-400 rounded-full mr-1 animate-pulse"></span>
                Active
              </span>
            </div>
          </div>

          <!-- 操作按钮组 (悬浮显示) -->
          <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-all duration-200 flex-shrink-0 z-10 translate-x-2 group-hover:translate-x-0">

             <!-- 预览 PDF 按钮 -->
             <button
                @click.stop="store.openPdf(doc.id, 1)"
                class="w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
                :class="store.state.activeDocId === doc.id ? 'text-slate-400 hover:text-red-500 hover:bg-red-50' : 'text-slate-400 hover:text-red-500 hover:bg-red-50'"
                title="预览文档内容"
             >
                <i class="fa-regular fa-eye text-xs"></i>
             </button>

             <!-- 查看结构树按钮 -->
             <button
                @click.stop="store.setViewingDoc(doc)"
                class="w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
                :class="store.state.activeDocId === doc.id ? 'text-slate-400 hover:text-primary-600 hover:bg-primary-50' : 'text-slate-400 hover:text-primary-600 hover:bg-primary-50'"
                title="查看知识图谱结构"
             >
                <i class="fa-solid fa-sitemap text-xs"></i>
             </button>
          </div>

        </li>
      </ul>
    </div>
  </aside>
</template>

<script setup>
import { useModoraStore } from '../composables/useModoraStore';
import { useDarkTheme } from '../composables/useDarkTheme';
import { ref } from 'vue';

const store = useModoraStore();
const { isDark, toggleTheme } = useDarkTheme();
const fileInputRef = ref(null);

// 触发文件选择
const triggerUpload = () => {
  if (store.state.isUploading) return;
  fileInputRef.value?.click();
};

// 简单的文件图标映射
const getFileIcon = (type) => {
  if (!type) return 'fa-regular fa-file';
  if (type.includes('pdf')) return 'fa-regular fa-file-pdf';
  if (type.includes('word') || type.includes('doc')) return 'fa-regular fa-file-word';
  if (type.includes('text') || type.includes('md')) return 'fa-regular fa-file-lines';
  return 'fa-regular fa-file';
};

const onFileChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  await store.uploadFile(file);
};
</script>
