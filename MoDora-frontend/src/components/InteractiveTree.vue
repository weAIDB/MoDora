<template>
  <div class="h-full w-full bg-slate-50 relative group flex flex-col">

    <!-- 1. 加载状态 -->
    <div v-if="isLoading" class="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm transition-all">
      <div class="flex items-center space-x-3 text-indigo-600">
        <i class="fa-solid fa-circle-notch fa-spin text-3xl"></i>
        <span class="font-medium animate-pulse text-lg">正在解析文档结构...</span>
      </div>
      <p class="text-slate-400 text-xs mt-2">Analyzing document topology...</p>
    </div>

    <!-- 2. 错误状态 -->
    <div v-else-if="error" class="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/95">
      <div class="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4">
        <i class="fa-solid fa-triangle-exclamation text-3xl text-red-500"></i>
      </div>
      <h3 class="text-lg font-bold text-slate-700 mb-1">加载失败</h3>
      <p class="text-slate-500 mb-4 px-8 text-center">{{ error }}</p>
      <button @click="fetchTreeData" class="px-5 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition shadow-sm">
        <i class="fa-solid fa-rotate-right mr-2"></i> 重试
      </button>
    </div>

    <!-- 3. Vue Flow 核心组件 -->
    <VueFlow
      v-else
      v-model="elements"
      :default-viewport="{ zoom: 1.0 }"
      :min-zoom="0.1"
      :max-zoom="4"
      :nodes-connectable="isEditMode"
      class="bg-slate-50 flex-1"
      @node-click="onNodeClick"
      @connect="onConnectEdge"
      @pane-click="onPaneClick"
    >
      <Background pattern-color="#cbd5e1" :gap="20" />
      <Controls position="bottom-left" />

      <!-- 4. 自定义节点模板 -->
      <template #node-custom="{ id, label, data, selected }">
        <div class="relative group/node">
          <!-- 节点卡片主体 -->
          <div
            class="px-3 py-2 shadow-sm rounded-lg border-2 w-48 transition-all duration-200 bg-white cursor-pointer relative"
            :class="[
              getNodeStyle(data.type),
              selected ? '!border-indigo-500 ring-2 ring-indigo-500/20' : ''
            ]"
            @dblclick.stop="openEditModal({ id, label, ...data })"
          >
            <!-- 顶部元信息 -->
            <div class="flex items-center justify-between mb-1">
               <span class="text-[9px] uppercase font-bold tracking-wider opacity-60 bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                 {{ data.type || 'NODE' }}
               </span>
               <div class="flex space-x-1" v-if="data.metadata">
                 <i class="fa-solid fa-circle-info text-indigo-300 group-hover/node:text-indigo-500 transition-colors text-xs"></i>
               </div>
            </div>

            <!-- 标题内容 -->
            <div class="font-bold text-slate-700 text-xs leading-snug line-clamp-2" :title="label">
              {{ label }}
            </div>
          </div>

          <!-- 悬浮摘要 Tooltip -->
          <div v-if="data.metadata" class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover/node:opacity-100 transition-all duration-200 pointer-events-none z-50 transform translate-y-2 group-hover/node:translate-y-0">
            <div class="font-semibold mb-1 border-b border-slate-600 pb-1 flex items-center">
              <i class="fa-solid fa-wand-magic-sparkles text-yellow-400 mr-2"></i>
              AI 摘要
            </div>
            <div class="leading-relaxed text-slate-300 text-[10px]">{{ data.metadata }}</div>
          </div>
        </div>

        <Handle type="target" :position="Position.Top" :connectable="isEditMode" class="!bg-slate-400 !w-2 !h-2" :class="isEditMode ? 'opacity-100' : 'opacity-0 pointer-events-none'" />
        <Handle type="source" :position="Position.Bottom" :connectable="isEditMode" class="!bg-slate-400 !w-2 !h-2" :class="isEditMode ? 'opacity-100' : 'opacity-0 pointer-events-none'" />
      </template>
    </VueFlow>

    <!-- Node Edit Modal -->
    <NodeEditModal 
      v-model="showEditModal"
      :initial-data="editingNodeData"
      @save="onSaveNode"
    />

    <!-- 顶部操作工具栏 -->
    <div class="absolute top-4 right-4 z-10 flex flex-col space-y-2">
      <!-- 视图控制 -->
      <div class="bg-white p-1.5 rounded-lg shadow-md border border-slate-100 flex flex-col space-y-2">
         <button @click="focusRoot" class="flex items-center justify-center w-8 h-8 rounded hover:bg-indigo-50 text-slate-500 hover:text-indigo-600 transition" title="回到根节点">
            <i class="fa-solid fa-crosshairs"></i>
         </button>
      </div>

      <!-- 编辑模式开关 -->
      <div class="bg-white p-1.5 rounded-lg shadow-md border border-slate-100 flex flex-col space-y-2 items-center">
         <button 
            @click="isEditMode = !isEditMode" 
            class="flex items-center justify-center w-8 h-8 rounded transition"
            :class="isEditMode ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'text-slate-500 hover:bg-indigo-50 hover:text-indigo-600'"
            title="切换编辑模式"
         >
            <i class="fa-solid fa-pen-to-square"></i>
         </button>
      </div>

      <!-- 编辑操作 (仅在编辑模式下显示) -->
      <div v-if="isEditMode" class="bg-white p-1.5 rounded-lg shadow-md border border-slate-100 flex flex-col space-y-2 items-center animate-fade-in-down">
         <button @click="addFreeNode" class="flex items-center justify-center w-8 h-8 rounded hover:bg-emerald-50 text-emerald-600 transition" title="添加新节点">
            <i class="fa-solid fa-plus"></i>
         </button>
         <button @click="deleteSelected" class="flex items-center justify-center w-8 h-8 rounded hover:bg-red-50 text-red-500 transition" title="删除选中元素">
            <i class="fa-solid fa-trash"></i>
         </button>
         <div class="h-px w-6 bg-slate-200 my-1"></div>
         <button @click="saveTree" class="flex items-center justify-center w-8 h-8 rounded bg-indigo-50 text-indigo-600 hover:bg-indigo-600 hover:text-white transition" title="保存树结构">
            <i class="fa-solid fa-save"></i>
         </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { VueFlow, useVueFlow, Handle, Position } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import { useModoraStore } from '../composables/useModoraStore';
import NodeEditModal from './NodeEditModal.vue';

import '@vue-flow/core/dist/style.css';
import '@vue-flow/core/dist/theme-default.css';
import '@vue-flow/controls/dist/style.css';

const store = useModoraStore();

const {
  addNodes, removeNodes, addEdges,
  setCenter, getNodes, getEdges,
  onNodesChange, onEdgesChange,
  getSelectedElements,
  project, dimensions, viewport
} = useVueFlow();

const elements = ref([]);
const isLoading = ref(false);
const error = ref(null);
const isEditMode = ref(false); // 控制编辑模式
const showEditModal = ref(false);
const editingNodeData = ref({});

// --- 编辑状态 ---
const openEditModal = (nodeData) => {
    if (!isEditMode.value) return; // Only allow editing in edit mode
    editingNodeData.value = { ...nodeData };
    showEditModal.value = true;
};

const onSaveNode = (formData) => {
    const node = elements.value.find(n => n.id === formData.id);
    if (node) {
        // Update label
        node.label = formData.label;
        
        // Update data fields
        // Ensure data object exists
        if (!node.data) node.data = {};
        
        node.data.type = formData.type;
        node.data.metadata = formData.metadata;
        node.data.data = formData.data;
        node.data.label = formData.label; // Also store label in data for consistency
    }
    showEditModal.value = false;
};

const addFreeNode = () => {
    const newId = 'node-' + Math.random().toString(36).substr(2, 9);
    
    // Calculate center of current view
    const { x, y, zoom } = viewport.value;
    const { width, height } = dimensions.value;
    
    // Project screen center to graph coordinates
    // Graph X = (Screen X - Viewport X) / Zoom
    const centerX = (width / 2 - x) / zoom;
    const centerY = (height / 2 - y) / zoom;
    
    // Add random offset to avoid perfect overlap
    const randomOffset = () => (Math.random() - 0.5) * 60;

    addNodes([{
        id: newId,
        type: 'custom',
        label: 'New Node',
        position: { 
            x: centerX + randomOffset(), 
            y: centerY + randomOffset() 
        },
        data: { type: 'new', title: 'New Node' }
    }]);
};

const deleteSelected = () => {
    const selected = getSelectedElements.value;
    if (selected.length === 0) return;
    if (confirm(`确定要删除选中的 ${selected.length} 个元素吗？`)) {
        removeNodes(selected.filter(e => e.type !== 'default' && e.source === undefined)); // 删除节点
        // Vue Flow 会自动处理关联边的删除
        // 但为了保险，我们也可以手动处理
        // 注意：removeNodes 也可以接受 edges
        // 这里直接用 elements.value 过滤比较麻烦，直接用 hook
        // removeNodes 实际上是内部 hook，我们这里用传入的 removeNodes
        removeNodes(selected);
    }
};

const saveTree = async () => {
    if (!confirm("确定要保存当前的树结构吗？后端将重新编译文档树。")) return;
    
    const fileName = store.state.viewingDocTree.name;
    // 获取当前的 nodes 和 edges
    // Vue Flow 的 elements 是 ref，包含了 nodes 和 edges
    // 或者用 toObject()
    
    // 过滤掉不必要的信息，只保留核心结构
    // 实际上直接传 elements 给后端，后端处理比较好
    // 注意：elements.value 包含了 Vue Flow 的内部状态，最好深拷贝一下
    const currentElements = JSON.parse(JSON.stringify(elements.value));
    
    try {
        isLoading.value = true;
        await store.saveTreeStructure(fileName, currentElements);
        alert("保存成功！");
        await fetchTreeData(); // 重新加载以确保同步
    } catch (e) {
        alert(`保存失败: ${e.message}`);
        isLoading.value = false;
    }
};

const getNodeStyle = (type) => {
  const map = {
    root: 'border-indigo-500 ring-4 ring-indigo-50',
    chapter: 'border-blue-400 hover:border-blue-500',
    section: 'border-slate-300 border-dashed hover:border-slate-400',
    new: 'border-emerald-400 bg-emerald-50/20'
  };
  return map[type] || 'border-slate-200 hover:border-indigo-300 hover:shadow-md';
};

const onConnectEdge = (params) => {
  const edge = { ...params, animated: true, style: { stroke: '#6366f1', strokeWidth: 2 } };
  addEdges([edge]);
};

const focusRoot = async () => {
    if (!elements.value || elements.value.length === 0) return;
    const nodes = elements.value.filter(el => el.position);
    if (nodes.length > 0) {
        const rootNode = nodes.reduce((prev, curr) => prev.position.y < curr.position.y ? prev : curr);
        await nextTick();
        setCenter(rootNode.position.x + 96, rootNode.position.y + 50, { zoom: 1.0, duration: 800 });
    }
};

const fetchTreeData = async () => {
  const currentDoc = store.state.viewingDocTree;
  if (!currentDoc) return;

  isLoading.value = true;
  error.value = null;
  elements.value = [];

  try {
    const response = await fetch('/api/tree', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_name: currentDoc.name })
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    if (data.elements) {
      elements.value = data.elements;
      setTimeout(() => {
          focusRoot();
      }, 100);
    }
  } catch (err) {
    console.error('Tree Fetch Error:', err);
    error.value = err.message || '网络连接错误';
  } finally {
    isLoading.value = false;
  }
};

const onNodeClick = (event) => console.log('点击节点:', event.node);
const onPaneClick = () => {};

onMounted(() => {
  fetchTreeData();
});
</script>

<style>
.vue-flow__handle {
  width: 8px;
  height: 8px;
  background-color: #94a3b8;
  border: 2px solid white;
}
.vue-flow__handle:hover {
  background-color: #4f46e5;
  transform: scale(1.2);
  transition: all 0.2s;
}
</style>
