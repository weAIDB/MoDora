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
    <div class="flex-1 overflow-y-auto p-4">
      <!-- 上传按钮 -->
      <div class="mb-6">
        <label class="group flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer hover:border-indigo-500 hover:bg-indigo-50/50 transition-all relative">
          <div v-if="!store.state.isUploading" class="text-center text-slate-400 group-hover:text-indigo-500">
            <i class="fa-solid fa-cloud-arrow-up text-2xl mb-2"></i>
            <p class="text-xs">点击上传文档</p>
          </div>
          <div v-else class="text-indigo-600 flex flex-col items-center">
            <i class="fa-solid fa-circle-notch fa-spin text-xl mb-2"></i>
            <p class="text-xs">解析中...</p>
          </div>
          <input type="file" class="hidden" @change="onFileChange" :disabled="store.state.isUploading" />
        </label>
      </div>

      <div class="border-t border-slate-100 my-4"></div>

      <!-- 文件列表 -->
      <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">已收录 ({{ store.state.knowledgeBase.length }})</h3>
      <ul class="space-y-2">
        <li v-for="doc in store.state.knowledgeBase" :key="doc.id"
            class="group flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-all">
          <div class="flex items-center overflow-hidden">
            <i :class="getFileIcon(doc.type)" class="mr-3 text-lg"></i>
            <span class="text-sm text-slate-700 truncate">{{ doc.name }}</span>
          </div>
          <button @click="store.setViewingDoc(doc)" class="text-slate-300 hover:text-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity">
            <i class="fa-solid fa-sitemap"></i>
          </button>
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
