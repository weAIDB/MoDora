<template>
  <aside class="w-full md:w-72 bg-white border-r border-slate-200 flex flex-col h-full z-20 shadow-sm">
    <!-- 头部 -->
    <div class="p-5 border-b border-slate-100 flex items-center">
      <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white mr-3">
        <i class="fa-solid fa-book"></i>
      </div>
      <h2 class="font-bold text-slate-800">知识库管理</h2>
    </div>

    <!-- 列表区 -->
    <div class="flex-1 overflow-y-auto p-4 custom-scrollbar">
      <!-- 上传按钮 -->
      <div class="mb-6">
        <label class="group flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer hover:border-indigo-500 hover:bg-indigo-50/50 transition-all relative">
          <div v-if="!store.state.isUploading" class="text-center text-slate-400 group-hover:text-indigo-500">
            <i class="fa-solid fa-cloud-arrow-up text-2xl mb-2"></i>
            <p class="text-xs">点击上传文档</p>
          </div>
          <div v-else class="text-indigo-600 flex flex-col items-center w-full px-4">
            <div class="flex items-center mb-2">
              <i class="fa-solid fa-circle-notch fa-spin text-lg mr-2"></i>
              <span class="text-xs font-medium">解析中... {{ store.state.uploadProgress }}%</span>
            </div>
            <!-- Progress Bar -->
            <div class="w-full bg-indigo-100 rounded-full h-1.5 overflow-hidden">
              <div 
                class="bg-indigo-600 h-1.5 rounded-full transition-all duration-300 ease-out"
                :style="{ width: `${store.state.uploadProgress}%` }"
              ></div>
            </div>
          </div>
          <input type="file" class="hidden" @change="onFileChange" :disabled="store.state.isUploading" />
        </label>
      </div>

      <div class="border-t border-slate-100 my-4"></div>

      <!-- 文件列表 -->
      <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">已收录 ({{ store.state.knowledgeBase.length }})</h3>
      <ul class="space-y-2">
        <li v-for="doc in store.state.knowledgeBase" :key="doc.id"
            @click="store.setActiveDoc(doc.id)"
            class="group flex items-center justify-between p-2 rounded-lg border transition-all cursor-pointer"
            :class="[
              store.state.activeDocId === doc.id
                ? 'bg-indigo-50 border-indigo-200 shadow-sm ring-1 ring-indigo-200'
                : 'bg-white border-transparent hover:bg-slate-50 hover:border-slate-200'
            ]"
        >

          <!-- 文件名区域 -->
          <div class="flex items-center overflow-hidden flex-1 min-w-0 mr-2" :title="doc.name">
            <!-- 选中的文件图标更亮 -->
            <i :class="getFileIcon(doc.type)" class="mr-3 text-lg flex-shrink-0 transition-transform group-hover:scale-110"></i>
            <div class="flex flex-col min-w-0">
              <span class="text-sm truncate select-none transition-colors"
                :class="store.state.activeDocId === doc.id ? 'font-bold text-indigo-900' : 'text-slate-700'"
              >
                {{ doc.name }}
              </span>
              <!-- 选中状态的标记 -->
              <span v-if="store.state.activeDocId === doc.id" class="text-[10px] text-indigo-500 font-medium">当前对话中</span>
            </div>
          </div>

          <!-- 操作按钮组 (悬浮显示) -->
          <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">

             <!-- 预览 PDF 按钮 -->
             <button
                @click.stop="store.openPdf(doc.id, 1)"
                class="p-1.5 rounded-md transition-colors"
                :class="store.state.activeDocId === doc.id ? 'text-indigo-400 hover:text-red-500 hover:bg-red-50' : 'text-slate-400 hover:text-red-500 hover:bg-red-50'"
                title="预览文档内容"
             >
                <i class="fa-regular fa-eye"></i>
             </button>

             <!-- 查看结构树按钮 -->
             <button
                @click.stop="store.setViewingDoc(doc)"
                class="p-1.5 rounded-md transition-colors"
                :class="store.state.activeDocId === doc.id ? 'text-indigo-400 hover:text-indigo-600 hover:bg-indigo-100' : 'text-slate-400 hover:text-indigo-600 hover:bg-indigo-50'"
                title="查看知识图谱结构"
             >
                <i class="fa-solid fa-sitemap"></i>
             </button>
          </div>

        </li>
      </ul>
    </div>
  </aside>
</template>

<script setup>
import { useModoraStore } from '../composables/useModoraStore';

const store = useModoraStore();

const onFileChange = (e) => {
  store.handleFileUpload(e.target.files[0]);
};

const getFileIcon = (type) => {
  const map = {
    pdf: 'fa-regular fa-file-pdf text-red-500',
    docx: 'fa-regular fa-file-word text-blue-600',
    txt: 'fa-regular fa-file-lines text-slate-500'
  };
  return map[type] || 'fa-regular fa-file';
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
