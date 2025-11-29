<template>
  <!-- 容器 -->
  <div class="h-[700px] w-full border border-slate-200 rounded-xl bg-slate-50 overflow-hidden relative group">

    <!-- 1. 加载状态 -->
    <div v-if="isLoading" class="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm transition-all">
      <div class="flex items-center space-x-3 text-indigo-600">
        <i class="fa-solid fa-circle-notch fa-spin text-3xl"></i>
        <span class="font-medium animate-pulse text-lg">正在解析文档结构...</span>
      </div>
      <p class="text-slate-400 text-xs mt-2">Connecting to /api/tree</p>
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
      :default-viewport="{ zoom: 1 }"
      :min-zoom="0.1"
      :max-zoom="4"
      :nodes-connectable="isConnectMode"
      class="bg-slate-50"
      @node-click="onNodeClick"
      @connect="onConnectEdge"
      @pane-click="onPaneClick"
    >
      <Background pattern-color="#cbd5e1" :gap="20" />
      <Controls />

      <!-- 4. 自定义节点模板 -->
      <template #node-custom="{ label, data, selected }">
        <div class="relative group/node">
          <!-- 节点卡片主体 (先渲染主体) -->
          <div
            class="px-4 py-3 shadow-sm rounded-lg border-2 w-56 transition-all duration-200 bg-white cursor-pointer relative"
            :class="[
              getNodeStyle(data.type),
              selected ? '!border-indigo-500 ring-2 ring-indigo-500/20' : ''
            ]"
          >
            <!-- 顶部元信息 -->
            <div class="flex items-center justify-between mb-1.5">
               <span class="text-[10px] uppercase font-bold tracking-wider opacity-60 bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                 {{ data.type || 'NODE' }}
               </span>
               <div class="flex space-x-1">
                 <i v-if="data.metadata" class="fa-solid fa-circle-info text-indigo-300 group-hover/node:text-indigo-500 transition-colors"></i>
               </div>
            </div>

            <!-- 标题内容 -->
            <div class="font-bold text-slate-700 text-sm leading-snug line-clamp-2" :title="label">
              {{ label }}
            </div>

            <!-- 选中时的快捷删除按钮 -->
            <button
              v-if="selected"
              @click.stop="deleteSelectedNodes"
              class="absolute -top-2 -right-2 bg-red-500 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs shadow-md hover:bg-red-600 transition-transform hover:scale-110 z-50"
              title="删除节点"
            >
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <!-- 悬浮摘要 Tooltip -->
          <div v-if="data.metadata" class="absolute left-1/2 -translate-x-1/2 bottom-full mb-3 w-72 p-4 bg-slate-800 text-white text-xs rounded-xl shadow-xl opacity-0 group-hover/node:opacity-100 transition-all duration-200 pointer-events-none z-50 transform translate-y-2 group-hover/node:translate-y-0">
            <div class="font-semibold mb-2 border-b border-slate-600 pb-2 flex items-center">
              <i class="fa-solid fa-wand-magic-sparkles text-yellow-400 mr-2"></i>
              AI 摘要
            </div>
            <div class="leading-relaxed text-slate-300">{{ data.metadata }}</div>
            <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-8 border-transparent border-t-slate-800"></div>
          </div>
        </div>

        <!-- 连接句柄 (Handles) -->
        <Handle
          type="target"
          :position="Position.Top"
          :connectable="isConnectMode"
          class="!bg-slate-400 !w-3 !h-3 transition-opacity duration-200 !z-50"
          :class="isConnectMode ? 'opacity-100 cursor-crosshair' : 'opacity-0 pointer-events-none'"
        />
        <Handle
          type="source"
          :position="Position.Bottom"
          :connectable="isConnectMode"
          class="!bg-slate-400 !w-3 !h-3 transition-opacity duration-200 !z-50"
          :class="isConnectMode ? 'opacity-100 cursor-crosshair' : 'opacity-0 pointer-events-none'"
        />
      </template>

    </VueFlow>

    <!-- 顶部操作工具栏 -->
    <div class="absolute top-4 right-4 z-10 flex flex-col space-y-2">
      <!-- 提示条 -->
      <div v-if="isConnectMode" class="bg-indigo-600/90 backdrop-blur border border-indigo-500 px-3 py-1.5 rounded-lg shadow-md text-xs text-white flex items-center animate-fade-in">
        <i class="fa-solid fa-link mr-2"></i>
        <span>请拖拽节点上下的句柄进行连线</span>
      </div>
      <div v-else class="bg-white/90 backdrop-blur border border-slate-200 px-3 py-1.5 rounded-lg shadow-sm text-xs text-slate-500 flex items-center">
        <i class="fa-solid fa-mouse-pointer mr-2 text-indigo-500"></i>
        <span>点击节点编辑 / 拖拽移动</span>
      </div>

      <!-- 操作按钮组 -->
      <div class="flex flex-col space-y-2 bg-white p-2 rounded-xl shadow-lg border border-slate-100 w-40">

        <!-- 1. 连线按钮 (Toggle) -->
        <button
          @click="isConnectMode = !isConnectMode"
          class="flex items-center space-x-2 px-3 py-2 rounded-lg transition-all text-sm font-medium w-full"
          :class="isConnectMode ? 'bg-indigo-50 text-indigo-600 border border-indigo-200' : 'bg-white text-slate-600 border border-transparent hover:bg-slate-50 hover:text-indigo-600'"
        >
          <div class="w-6 h-6 rounded-full flex items-center justify-center" :class="isConnectMode ? 'bg-indigo-200' : 'bg-slate-100'">
            <i class="fa-solid fa-draw-polygon text-xs"></i>
          </div>
          <span>{{ isConnectMode ? '完成连线' : '开始连线' }}</span>
        </button>

        <!-- 2. 新增节点 -->
        <button
          @click="handleAddNode"
          class="flex items-center space-x-2 px-3 py-2 rounded-lg transition-all text-sm font-medium w-full bg-white text-slate-600 border border-transparent hover:bg-slate-50 hover:text-indigo-600"
        >
          <div class="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center">
            <i class="fa-solid fa-plus text-xs"></i>
          </div>
          <span>新增节点</span>
        </button>

        <!-- 3. 删除选中 -->
        <button
          @click="deleteSelectedNodes"
          class="flex items-center space-x-2 px-3 py-2 rounded-lg transition-all text-sm font-medium w-full bg-white text-slate-600 border border-transparent hover:bg-slate-50 hover:text-red-600"
        >
          <div class="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center">
            <i class="fa-regular fa-trash-can text-xs"></i>
          </div>
          <span>删除选中</span>
        </button>

        <div class="h-px bg-slate-100 my-1"></div>

        <!-- 保存按钮 (保持独立醒目样式) -->
        <button @click="handleSave" class="flex items-center space-x-2 px-3 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-900 transition text-sm font-medium shadow-md w-full justify-center">
          <i class="fa-solid fa-floppy-disk text-xs"></i>
          <span>保存结构</span>
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

// 引入样式
import '@vue-flow/core/dist/style.css';
import '@vue-flow/core/dist/theme-default.css';
import '@vue-flow/controls/dist/style.css';

const store = useModoraStore();

// 获取 Vue Flow 实例控制权
const {
  addNodes,
  removeNodes,
  addEdges,
  onConnect,
  getSelectedElements,
  fitView,
  project,
  dimensions // 1. 引入 dimensions 以获取容器尺寸
} = useVueFlow();

// 状态
const elements = ref([]);
const isLoading = ref(false);
const error = ref(null);
const isConnectMode = ref(false); // 控制连线模式的状态

// --- 预留的后端 API 接口 (Mock) ---
const api = {
  addNode: async (nodeData) => {
    console.log('[API Mock] Adding node:', nodeData);
  },
  deleteNodes: async (ids) => {
    console.log('[API Mock] Deleting nodes:', ids);
  },
  addEdge: async (edgeData) => {
    console.log('[API Mock] Connecting:', edgeData);
  },
  saveAll: async (allElements) => {
    console.log('[API Mock] Saving full tree:', allElements);
    alert('保存成功！(数据已打印到控制台，待接入后端)');
  }
};

// 样式映射
const getNodeStyle = (type) => {
  const map = {
    root: 'border-indigo-500 ring-4 ring-indigo-50',
    chapter: 'border-blue-400 hover:border-blue-500',
    section: 'border-slate-300 border-dashed hover:border-slate-400',
    new: 'border-emerald-400 bg-emerald-50/20'
  };
  return map[type] || 'border-slate-200 hover:border-indigo-300 hover:shadow-md';
};

// --- 编辑功能实现 ---

// 1. 连线功能
const onConnectEdge = (params) => {
  const edge = {
    ...params,
    animated: true,
    style: { stroke: '#6366f1', strokeWidth: 2 }
  };
  addEdges([edge]);
  api.addEdge(edge);
};

// 2. 新增节点 (核心修改：居中逻辑)
const handleAddNode = () => {
  const id = crypto.randomUUID();

  // 获取当前容器的中心点 (屏幕/像素坐标)
  const { width, height } = dimensions.value;
  // 将屏幕中心点投影到图谱坐标系中 (考虑了缩放和平移)
  const centeredPosition = project({ x: width / 2, y: height / 2 });

  const newNode = {
    id: id,
    type: 'custom',
    label: '新章节/节点',
    // 稍微偏移一点点，让视觉重心更自然，且减去节点宽度的一半(约100)让其完美居中
    position: {
      x: centeredPosition.x - 100,
      y: centeredPosition.y - 25
    },
    data: {
      type: 'new',
      metadata: '这是刚刚创建的新节点，请修改内容。'
    }
  };

  addNodes([newNode]);
  api.addNode(newNode);
};

// 3. 删除选中
const deleteSelectedNodes = () => {
  const selected = getSelectedElements.value;
  if (selected.length === 0) return;

  removeNodes(selected);
  api.deleteNodes(selected.map(el => el.id));
};

// 4. 保存所有
const handleSave = () => {
  api.saveAll(elements.value);
};

// --- 基础加载逻辑 ---
const fetchTreeData = async () => {
  const currentDoc = store.state.viewingDocTree;
  if (!currentDoc) return;

  isLoading.value = true;
  error.value = null;
  elements.value = [];
  // 重置连线模式
  isConnectMode.value = false;

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
      await nextTick();
      setTimeout(() => fitView({ padding: 0.2, duration: 800 }), 50);
    }
  } catch (err) {
    console.error('Tree Fetch Error:', err);
    error.value = err.message || '网络连接错误';
  } finally {
    isLoading.value = false;
  }
};

const onNodeClick = (event) => {
  console.log('点击节点:', event.node);
};

const onPaneClick = () => {
  // 点击空白区域取消选中等
};

onMounted(() => {
  fetchTreeData();
});
</script>

<style>
/* 覆盖 Vue Flow 默认连接点样式 */
.vue-flow__handle {
  width: 10px;
  height: 10px;
  background-color: #94a3b8;
  border: 2px solid white;
}
.vue-flow__handle:hover {
  background-color: #4f46e5;
  transform: scale(1.2);
  transition: all 0.2s;
}

/* 简单的淡入动画 */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fade-in 0.3s ease-out;
}
</style>
