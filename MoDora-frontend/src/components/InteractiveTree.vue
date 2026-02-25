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

    <template v-else>
      <!-- 3. AI Recompose Input Area (Always visible above) -->
      <div class="z-10 px-6 pt-4 pb-2">
        <div class="max-w-3xl mx-auto bg-white/80 dark:bg-slate-800/80 backdrop-blur-md rounded-2xl shadow-lg border border-slate-200 dark:border-slate-700 p-2 flex items-center space-x-3 group/ai-input focus-within:ring-2 focus-within:ring-primary-500/20 focus-within:border-primary-500/50 transition-all">
          <div class="flex-1 relative">
            <input 
              v-model="aiQuery"
              type="text"
              placeholder="Describe how to restructure this tree (e.g. 'Group by topic')..."
              class="w-full bg-transparent border-none focus:ring-0 py-2.5 px-4 text-slate-700 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500 disabled:opacity-50"
              @keyup.enter="submitAIRecompose"
              ref="aiInputRef"
              :disabled="isRecomposing || isLoading"
            />
          </div>
          <div class="flex items-center pr-2">
            <button 
              @click="submitAIRecompose"
              class="group/ai-btn bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-xl flex items-center space-x-2 transition-all shadow-sm hover:shadow-md active:scale-95 disabled:opacity-50 disabled:pointer-events-none"
              :disabled="!aiQuery.trim() || isRecomposing || isLoading"
            >
              <span class="text-sm font-semibold">Recompose</span>
              <i class="fa-solid fa-wand-magic-sparkles" :class="{ 'animate-pulse': isRecomposing }"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- 4. Vue Flow Core Component -->
      <VueFlow
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
      <Controls position="bottom-left" />

      <!-- 4. Particle Node (3D rotating cards during AI recompose) -->
      <template #node-particle="{ label, data }">
        <div 
          class="px-3 py-2 shadow-xl rounded-xl border bg-white/90 dark:bg-slate-800/90 backdrop-blur-md transition-opacity duration-300 w-48"
          :class="getNodeStyle(data.type)"
          :style="{ 
            opacity: data.opacity || 1,
            transform: `scale(${data.scale || 1})`,
            zIndex: data.zIndex || 1,
            boxShadow: `0 10px 30px -10px rgba(99, 102, 241, ${0.2 * (data.scale || 1)})`
          }"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="text-[9px] uppercase font-bold tracking-wider opacity-80 bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded text-slate-500 dark:text-slate-300">
              {{ data.type || 'ANALYZING' }}
            </span>
            <i class="fa-solid fa-wand-magic-sparkles text-primary-500 animate-pulse text-[10px]"></i>
          </div>
          <div class="font-bold text-slate-700 dark:text-slate-200 text-xs leading-snug line-clamp-2">
            {{ label }}
          </div>
        </div>
      </template>

      <!-- 5. Custom Node Template -->
      <template #node-custom="{ id, label, data, selected }">
        <div class="relative group/node">
          <!-- Full card in normal mode -->
          <div
            class="px-3 py-2 shadow-sm rounded-xl border transition-all duration-300 cursor-pointer relative w-48 backdrop-blur-md"
            :class="[
              !isHeatmapMode ? getNodeStyle(data.type) : '',
              selected 
                ? '!border-primary-500 ring-2 ring-primary-500/20 dark:ring-primary-500/40' 
                : (!isHeatmapMode ? 'bg-white/80 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-md' : '')
            ]"
            :style="isHeatmapMode ? getHeatmapDynamicStyle(data.impact) : {}"
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

        <Handle type="target" :position="Position.Top" />
        <Handle type="source" :position="Position.Bottom" />
      </template>
    </VueFlow>

    <!-- 5. Recomposing Overlay (3D rotation effect during AI recompose) -->
    <!-- Removed original HTML Overlay, direct operations in Vue Flow -->
    
    <!-- Top Operation Toolbar -->
    <div class="absolute top-24 right-4 z-10 flex flex-col space-y-2">
      <!-- View Control -->
      <div class="bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm p-1.5 rounded-lg shadow-md border border-slate-100 dark:border-slate-700 flex flex-col space-y-2 relative">
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
  </template>
</div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue';
import { VueFlow, useVueFlow, Handle, Position } from '@vue-flow/core';
import gsap from 'gsap';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import dagre from '@dagrejs/dagre';
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
  setCenter,
  getSelectedElements,
  dimensions, viewport,
  getNodesBounds,
  nodes: flowNodes,
  edges: flowEdges
} = useVueFlow();

const elements = ref([]); // 保持数据源

// 渲染限制：最多渲染 20 个节点及其相关的连线
const renderedNodes = computed(() => {
  const nodes = elements.value.filter(el => el.position);
  if (nodes.length <= 20) return nodes;
  
  // 简单策略：按索引取前 20 个，后续可以优化为按层级或权重取
  return nodes.slice(0, 20);
});

const renderedEdges = computed(() => {
  const edges = elements.value.filter(el => !el.position);
  const nodeIds = new Set(renderedNodes.value.map(n => n.id));
  
  // 只渲染连接已存在节点的边
  return edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
});

// 内部追踪状态
let animationFrameId = null;
let currentInitialNodes = [];
const isLoading = ref(false);
const error = ref(null);
const isEditMode = ref(false); // 控制编辑模式
const isHeatmapMode = ref(false); // 控制热力图模式
const showEditModal = ref(false);
const editingNodeData = ref({});
const isRecomposing = ref(false)

// AI Input State
const aiQuery = ref('');
const aiInputRef = ref(null);

// 3D 旋转相关的配置
const rotationSpeed = 0.03
let activeParticleCount = 0
let rotationY = 0

/**
 * 使用 dagre 进行自动布局
 */
const layout = (els) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  
  // 设定方向: TB (Top to Bottom), LR (Left to Right)
  // nodesep: 同层节点之间的间距; ranksep: 不同层级之间的间距
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 50, ranksep: 60 });

  els.forEach((el) => {
    if (el.position) {
      // 节点
      dagreGraph.setNode(el.id, { width: 200, height: 100 });
    } else {
      // 连线
      dagreGraph.setEdge(el.source, el.target);
    }
  });

  dagre.layout(dagreGraph);

  return els.map((el) => {
    if (el.position) {
      const nodeWithPosition = dagreGraph.node(el.id);
      return {
        ...el,
        position: {
          x: nodeWithPosition.x - 100, // 减去宽度的一半使中心对齐
          y: nodeWithPosition.y - 50,  // 减去高度的一半
        },
      };
    }
    return el;
  });
};

// --- 热力图样式 ---
const maxImpact = computed(() => {
  const impacts = elements.value
    .filter(el => el.data && el.data.impact)
    .map(el => el.data.impact);
  return impacts.length > 0 ? Math.max(...impacts) : 1;
});

const getHeatmapDynamicStyle = (impact) => {
  if (!impact || impact <= 0) {
    return {
      backgroundColor: isDark.value ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 0.5)',
      borderColor: isDark.value ? '#334155' : '#e2e8f0',
      opacity: 0.6,
      filter: 'grayscale(1)'
    };
  }

  // 归一化 impact (0 到 1 之间)
  const normalized = Math.min(impact / maxImpact.value, 1);
  
  // 颜色插值逻辑: 浅黄 -> 橙色 -> 深红
  // HSL: 60 (黄) -> 30 (橙) -> 0 (红)
  const hue = 60 - (normalized * 60); 
  // Lightness: 95% (浅) -> 50% (深)
  const lightness = 95 - (normalized * 45);
  // Saturation: 80% (亮) -> 100% (鲜艳)
  const saturation = 80 + (normalized * 20);

  return {
    backgroundColor: `hsla(${hue}, ${saturation}%, ${lightness}%, 0.9)`,
    borderColor: `hsla(${hue}, ${saturation}%, ${lightness - 10}%, 1)`,
    color: lightness < 60 ? '#ffffff' : 'inherit',
    boxShadow: normalized > 0.5 ? `0 4px 12px hsla(${hue}, ${saturation}%, 50%, 0.3)` : 'none',
    fontWeight: normalized > 0.7 ? 'bold' : 'normal',
    transition: 'all 0.3s ease'
  };
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

const submitAIRecompose = () => {
  if (!aiQuery.value.trim() || isRecomposing.value || isLoading.value) return;
  const query = aiQuery.value;
  aiQuery.value = '';
  explodeAndReassemble(query);
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

const applyTransitionToElements = (els, duration) => {
  return els.map((el) => {
    if (!el.position) return el;
    return {
      ...el,
      style: {
        ...el.style,
        transition: `transform ${duration}ms cubic-bezier(0.2, 0.8, 0.2, 1)`,
        transform: el.style?.transform || '',
        opacity: el.style?.opacity || 1
      }
    };
  });
};

// 计算球体上节点的位置
const getSpherePosition = (index, total, radius, centerX, centerY) => {
  const phi = Math.acos(-1 + (2 * index) / total)
  const theta = Math.sqrt(total * Math.PI) * phi
  
  // 应用当前的旋转
  const x3d = radius * Math.sin(phi) * Math.cos(theta + rotationY)
  const y3d = radius * Math.sin(phi) * Math.sin(theta + rotationY)
  const z3d = radius * Math.cos(phi)
  
  // 将 3D 坐标投影到 2D 平面
  const rotatedX = x3d * Math.cos(rotationY) - z3d * Math.sin(rotationY)
  const rotatedZ = x3d * Math.sin(rotationY) + z3d * Math.cos(rotationY)
  
  // 计算缩放 (模拟远近)
  const scale = (rotatedZ + radius * 2) / (radius * 2)
  const opacity = 0.3 + (scale - 0.5) * 0.7
  
  return {
    x: centerX + rotatedX,
    y: centerY + y3d,
    scale,
    opacity,
    zIndex: Math.round(rotatedZ + radius)
  }
}

// 动画帧循环
 const updateSphereFrame = (radius, centerX, centerY) => {
   if (!isRecomposing.value) return
   
   rotationY += rotationSpeed
   
   elements.value = elements.value.map(el => {
     if (el.type === 'particle') {
       const index = parseInt(el.id.split('-')[1])
       const pos = getSpherePosition(index, activeParticleCount, radius, centerX, centerY)
       
       return {
         ...el,
         position: { x: pos.x - 96, y: pos.y - 40 }, // 减去卡片半宽(96)和半高(40)，使卡片中心对准球体坐标
         data: { 
           ...el.data, 
           opacity: pos.opacity,
           scale: pos.scale,
           zIndex: pos.zIndex
         }
       }
     }
     return el
   })
   
   animationFrameId = requestAnimationFrame(() => updateSphereFrame(radius, centerX, centerY))
 }
 
 const explodeAndReassemble = async (userQuery) => {
   if (isRecomposing.value) return
   
   // 1. 获取当前视口中心 (使用 Vue Flow 提供的 dimensions 和 viewport)
   const { x, y, zoom } = viewport.value
   const { width, height } = dimensions.value
   
   // 计算画布坐标系下的屏幕中心点，并应用偏移（向左和向上移动）
   // 减去 150 和 100 是为了让中心看起来更靠左上，避开右侧或下方的 UI 干扰
   const centerX = (width / 2 - x) / zoom 
   const centerY = (height / 2 - y) / zoom 
   
   // 2. 备份当前元素并提取真实节点数据
   const originalElements = [...elements.value]
   const existingNodes = elements.value.filter(el => el.position && el.type !== 'particle')
   
   // 如果当前没有节点，则使用默认的一组语义化标签
   const displayNodes = existingNodes.length > 0 ? existingNodes : [
     { label: 'Document Root', data: { type: 'root' } },
     { label: 'Core Concepts', data: { type: 'chapter' } },
     { label: 'Logical Flow', data: { type: 'section' } },
     { label: 'Data Schema', data: { type: 'section' } }
   ]

   // 限制旋转的卡片数量，避免性能问题
  const maxParticles = 20
  const nodesToAnimate = displayNodes.slice(0, maxParticles)
   activeParticleCount = nodesToAnimate.length
   
   // 3. 创建旋转卡片节点
   const particles = nodesToAnimate.map((node, i) => ({
     id: `particle-${i}`,
     type: 'particle',
     label: node.label,
     position: { x: centerX - 96, y: centerY - 40 }, // 初始位置设为计算出的中心(减去偏移使卡片居中)
     data: { 
       opacity: 0,
       type: node.data?.type || 'node',
       ...node.data
     }
   }))
   
   // 4. 切换到动画状态
  isRecomposing.value = true
  rotationY = 0 // 重置旋转角度
  elements.value = particles
   
   // 5. 启动 3D 旋转动画
   const radius = 320 
   updateSphereFrame(radius, centerX, centerY)
   
   // 自动平滑聚焦到旋转中心，确保用户视角正对动画
   setCenter(centerX, centerY, { zoom: zoom > 0.6 ? zoom : 0.8, duration: 1000 })
   
   try {
     const currentDoc = store.state.viewingDocTree
     const response = await fetch('/api/tree/recompose', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({
         file_name: currentDoc ? currentDoc.name : 'default',
         rule: 'ai',
         user_query: userQuery
       })
     })
     
     if (!response.ok) throw new Error('Failed to recompose tree')
     const data = await response.json()
     
     // 6. 停止 3D 动画
     isRecomposing.value = false
     if (animationFrameId) cancelAnimationFrame(animationFrameId)
     
     // 7. 更新数据并重置布局
     // 先把粒子替换成新节点，但初始位置设为当前粒子的平均位置或中心
     const newElements = data.elements.map(el => {
       if (el.type === 'custom') {
         return {
           ...el,
           position: { x: centerX - 96, y: centerY - 40 },
           style: { transition: 'all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)' }
         }
       }
       return el
     })
     
     elements.value = newElements
     
     // 触发自动布局
     setTimeout(() => {
       elements.value = layout(elements.value)
     }, 50)
     
   } catch (error) {
     console.error('Recompose failed:', error)
     isRecomposing.value = false
     if (animationFrameId) cancelAnimationFrame(animationFrameId)
     elements.value = originalElements
   }
 }

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
      elements.value = layout(data.elements);
      // 自动聚焦到根节点
      setTimeout(() => {
          focusRoot();
      }, 200);
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
.vue-flow__edge-path {
  stroke-dasharray: 6 10;
  animation: edge-flow 1.6s linear infinite;
}
@keyframes edge-flow {
  to {
    stroke-dashoffset: -32;
  }
}
</style>
