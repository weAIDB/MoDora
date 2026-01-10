<template>
  <div class="h-full w-full bg-transparent relative group flex flex-col">

    <!-- 1. Loading State -->
    <div v-if="isLoading" class="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm transition-all">
      <div class="flex items-center space-x-3 text-primary-600 dark:text-primary-400">
        <i class="fa-solid fa-circle-notch fa-spin text-3xl"></i>
        <span class="font-medium animate-pulse text-lg">Analyzing document structure...</span>
      </div>
      <p class="text-slate-400 dark:text-slate-500 text-xs mt-2">Analyzing document topology...</p>
    </div>

    <!-- 2. Error State -->
    <div v-else-if="error" class="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/95 dark:bg-slate-900/95">
      <div class="w-16 h-16 bg-red-50 dark:bg-red-900/20 rounded-full flex items-center justify-center mb-4">
        <i class="fa-solid fa-triangle-exclamation text-3xl text-red-500"></i>
      </div>
      <h3 class="text-lg font-bold text-slate-700 dark:text-slate-200 mb-1">Load Failed</h3>
      <p class="text-slate-500 dark:text-slate-400 mb-4 px-8 text-center">{{ error }}</p>
      <button @click="fetchTreeData" class="px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition shadow-sm">
        <i class="fa-solid fa-rotate-right mr-2"></i> Retry
      </button>
    </div>

    <!-- 3. Vue Flow Core Component -->
    <VueFlow
      v-else
      v-model="elements"
      :default-viewport="{ zoom: 1.0 }"
      :min-zoom="0.1"
      :max-zoom="4"
      :nodes-connectable="isEditMode"
      class="bg-transparent flex-1"
      @node-click="onNodeClick"
      @connect="onConnectEdge"
      @pane-click="onPaneClick"
    >
      <Background :pattern-color="isDark ? '#475569' : '#cbd5e1'" :gap="20" />
      <Controls position="bottom-left" class="!bg-white dark:!bg-slate-800 !border-slate-200 dark:!border-slate-700 !shadow-lg [&>button]:!bg-transparent [&>button]:!border-slate-100 dark:[&>button]:!border-slate-700 [&>button]:!text-slate-600 dark:[&>button]:!text-slate-300 hover:[&>button]:!bg-slate-50 dark:hover:[&>button]:!bg-slate-700" />

      <!-- 4. Custom Node Template -->
      <template #node-custom="{ id, label, data, selected }">
        <div class="relative group/node">
          <!-- Node Card Body -->
          <div
            class="px-3 py-2 shadow-sm rounded-xl border transition-all duration-200 cursor-pointer relative w-48 backdrop-blur-md"
            :class="[
              isHeatmapMode ? getHeatmapStyle(data.impact) : getNodeStyle(data.type),
              selected 
                ? '!border-primary-500 ring-2 ring-primary-500/20 dark:ring-primary-500/40' 
                : (isHeatmapMode ? '' : 'bg-white/80 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md')
            ]"
            @dblclick.stop="openEditModal({ id, label, ...data })"
          >
            <!-- Top Meta Info -->
            <div class="flex items-center justify-between mb-1">
               <span class="text-[9px] uppercase font-bold tracking-wider opacity-80 bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded text-slate-500 dark:text-slate-300">
                 {{ data.type || 'NODE' }}
               </span>
               <div class="flex space-x-1" v-if="data.metadata">
                 <i class="fa-solid fa-circle-info text-primary-300 dark:text-primary-600 group-hover/node:text-primary-500 dark:group-hover/node:text-primary-400 transition-colors text-xs"></i>
               </div>
            </div>

            <!-- Title Content -->
            <div class="font-bold text-slate-700 dark:text-slate-200 text-xs leading-snug line-clamp-2" :title="label">
              {{ label }}
            </div>
          </div>

          <!-- Hover Summary Tooltip -->
          <div v-if="data.metadata" class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-slate-800 dark:bg-slate-700 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover/node:opacity-100 transition-all duration-200 pointer-events-none z-50 transform translate-y-2 group-hover/node:translate-y-0 border border-slate-700 dark:border-slate-600">
            <div class="font-semibold mb-1 border-b border-slate-600 dark:border-slate-500 pb-1 flex items-center">
              <i class="fa-solid fa-wand-magic-sparkles text-yellow-400 mr-2"></i>
              AI Summary
            </div>
            <div class="leading-relaxed text-slate-300">{{ data.metadata }}</div>
          </div>
        </div>

        <Handle type="target" :position="Position.Top" :connectable="isEditMode" class="!bg-slate-400 dark:!bg-slate-500 !w-2 !h-2" :class="isEditMode ? 'opacity-100' : 'opacity-0 pointer-events-none'" />
        <Handle type="source" :position="Position.Bottom" :connectable="isEditMode" class="!bg-slate-400 dark:!bg-slate-500 !w-2 !h-2" :class="isEditMode ? 'opacity-100' : 'opacity-0 pointer-events-none'" />
      </template>
    </VueFlow>
    
    <!-- Top Operation Toolbar -->
    <div class="absolute top-4 right-4 z-10 flex flex-col space-y-2">
      <!-- View Control -->
      <div class="bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm p-1.5 rounded-lg shadow-md border border-slate-100 dark:border-slate-700 flex flex-col space-y-2">
         <button @click="focusRoot" class="flex items-center justify-center w-8 h-8 rounded hover:bg-primary-50 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 transition" title="Reset to Root">
            <i class="fa-solid fa-crosshairs"></i>
         </button>
      </div>

      <!-- Heatmap Toggle -->
      <div class="bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm p-1.5 rounded-lg shadow-md border border-slate-100 dark:border-slate-700">
         <button 
            @click="isHeatmapMode = !isHeatmapMode" 
            class="flex items-center justify-center w-8 h-8 rounded transition"
            :class="isHeatmapMode ? 'bg-orange-100 text-orange-600 dark:bg-orange-900/50 dark:text-orange-400 ring-2 ring-orange-200 dark:ring-orange-800' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'"
            title="Toggle Heatmap"
         >
            <i class="fa-solid fa-fire"></i>
         </button>
      </div>

      <!-- Edit Mode Toggle -->
      <div class="bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm p-1.5 rounded-lg shadow-md border border-slate-100 dark:border-slate-700">
         <button 
            @click="isEditMode = !isEditMode" 
            class="flex items-center justify-center w-8 h-8 rounded transition"
            :class="isEditMode ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/50 dark:text-primary-400' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'"
            title="Toggle Edit Mode"
         >
            <i class="fa-solid fa-pen-to-square"></i>
         </button>
      </div>

      <!-- Edit Operations (Only in Edit Mode) -->
      <div v-if="isEditMode" class="bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm p-1.5 rounded-lg shadow-md border border-slate-100 dark:border-slate-700 flex flex-col space-y-2 items-center animate-fade-in-down">
         <button @click="addFreeNode" class="flex items-center justify-center w-8 h-8 rounded hover:bg-emerald-50 dark:hover:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 transition" title="Add New Node">
            <i class="fa-solid fa-plus"></i>
         </button>
         <button @click="deleteSelected" class="flex items-center justify-center w-8 h-8 rounded hover:bg-red-50 dark:hover:bg-red-900/30 text-red-500 dark:text-red-400 transition" title="Delete Selected Elements">
            <i class="fa-solid fa-trash"></i>
         </button>
         <div class="h-px w-6 bg-slate-200 dark:bg-slate-600 my-1"></div>
         <button @click="saveTree" class="flex items-center justify-center w-8 h-8 rounded bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 hover:bg-primary-600 dark:hover:bg-primary-600 hover:text-white transition" title="Save Tree Structure">
            <i class="fa-solid fa-save"></i>
         </button>
      </div>
    </div>
    
    <!-- Node Edit Modal -->
    <NodeEditModal 
      v-model="showEditModal"
      :initial-data="editingNodeData"
      @save="onSaveNode"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue';
import { VueFlow, useVueFlow, Handle, Position } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import { useModoraStore } from '../composables/useModoraStore';
import { useDarkTheme } from '../composables/useDarkTheme';
import NodeEditModal from './NodeEditModal.vue';

import '@vue-flow/core/dist/style.css';
import '@vue-flow/core/dist/theme-default.css';
import '@vue-flow/controls/dist/style.css';

const store = useModoraStore();
const { isDark } = useDarkTheme();

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
const isHeatmapMode = ref(false); // 控制热力图模式
const showEditModal = ref(false);
const editingNodeData = ref({});

// --- 热力图样式 ---
const getHeatmapStyle = (impact) => {
  if (!impact || impact <= 0) return 'bg-slate-50/50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 opacity-60 grayscale'; // 无影响节点变淡
  if (impact <= 2) return 'bg-orange-50 dark:bg-orange-900/30 border-orange-300 dark:border-orange-700';
  if (impact <= 5) return 'bg-orange-100 dark:bg-orange-900/50 border-orange-400 dark:border-orange-600 shadow-md shadow-orange-200/50';
  if (impact <= 10) return 'bg-red-100 dark:bg-red-900/50 border-red-500 dark:border-red-500 shadow-md shadow-red-200/50 font-medium';
  return 'bg-red-500 text-white border-red-600 shadow-lg shadow-red-500/50 font-bold';
};

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
    if (confirm(`Are you sure you want to delete the selected ${selected.length} elements?`)) {
        removeNodes(selected.filter(e => e.type !== 'default' && e.source === undefined)); // Delete nodes
        // Vue Flow automatically handles related edge deletion
        // But for safety, we can also handle it manually
        // Note: removeNodes can also accept edges
        // Filtering elements.value here is troublesome, so use hook directly
        // removeNodes is actually an internal hook, we use the passed removeNodes here
        removeNodes(selected);
    }
};

const saveTree = async () => {
    if (!confirm("Are you sure you want to save the current tree structure? The backend will recompile the document tree.")) return;
    
    const fileName = store.state.viewingDocTree.name;
    // Get current nodes and edges
    // Vue Flow's elements is a ref containing nodes and edges
    // Or use toObject()
    
    // Filter out unnecessary info, keep core structure
    // Actually passing elements to backend is better, backend handles it
    // Note: elements.value contains Vue Flow internal state, better deep copy
    const currentElements = JSON.parse(JSON.stringify(elements.value));
    
    try {
        isLoading.value = true;
        await store.saveTreeStructure(fileName, currentElements);
        alert("Saved successfully!");
        await fetchTreeData(); // Reload to ensure sync
    } catch (e) {
        alert(`Save failed: ${e.message}`);
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
    error.value = err.message || 'Network Connection Error';
  } finally {
    isLoading.value = false;
  }
};

const onNodeClick = (event) => console.log('Node Clicked:', event.node);
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
