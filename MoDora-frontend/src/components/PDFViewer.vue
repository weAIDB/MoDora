<template>
  <div class="flex flex-col h-full bg-slate-100">
    <!-- 1. 顶部工具栏 -->
    <div class="flex items-center justify-between px-4 py-2 bg-white border-b border-slate-200 shadow-sm z-10 shrink-0">
      <div class="flex items-center space-x-2 min-w-0">
        <span class="font-bold text-slate-700 text-sm truncate max-w-[150px]" :title="fileName">
          <i class="fa-regular fa-file-pdf text-red-500 mr-2"></i>{{ fileName }}
        </span>
        <span class="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded whitespace-nowrap">
          {{ currentPage }} / {{ pageCount }}
        </span>
      </div>

      <div class="flex items-center space-x-2 shrink-0">
        <!-- 缩放控制 -->
        <div class="flex items-center bg-slate-100 rounded-lg p-1 mr-2">
          <button @click="changeScale(-0.1)" class="w-6 h-6 flex items-center justify-center hover:bg-white rounded text-slate-600 transition">
            <i class="fa-solid fa-minus text-[10px]"></i>
          </button>
          <span class="text-xs w-8 text-center text-slate-500">{{ Math.round(scale * 100) }}%</span>
          <button @click="changeScale(0.1)" class="w-6 h-6 flex items-center justify-center hover:bg-white rounded text-slate-600 transition">
            <i class="fa-solid fa-plus text-[10px]"></i>
          </button>
        </div>

        <a :href="source" download class="p-2 text-slate-400 hover:text-indigo-600 transition" title="下载原文件">
          <i class="fa-solid fa-download"></i>
        </a>
      </div>
    </div>

    <!-- 2. PDF 内容区域 (可滚动) -->
    <div class="flex-1 overflow-auto p-4 md:p-8 flex justify-center custom-scrollbar bg-slate-200/50 relative" ref="containerRef">

      <!-- 渲染区域 -->
      <!-- 只有当 pdfWidth > 0 时才渲染，避免动画期间的闪烁 -->
      <div v-if="source && pdfWidth > 0" class="relative shadow-lg transition-all duration-75 ease-out bg-white h-max" :style="{ width: pdfWidth + 'px' }">
        <!-- 模式 A: 普通 PDF 阅读模式 -->
        <VuePdfEmbed
          v-show="!useImageMode"
          ref="pdfRef"
          :source="source"
          :page="currentPage"
          :width="pdfWidth"
          @loaded="handleLoaded"
        />

        <!-- 模式 B: 原文溯源图片模式 (高精度) -->
        <img 
          v-if="useImageMode"
          :src="imageUrl"
          class="w-full h-auto block"
          alt="Page View"
          @load="handleImageLoad"
        />
        
        <!-- 高亮覆盖层 -->
        <div v-for="(hl, idx) in highlights" :key="idx"
             class="absolute bg-yellow-300/30 border border-yellow-500/50 pointer-events-none z-10"
             :style="hl"
        ></div>
      </div>

      <!-- 加载中或初始化状态 -->
      <div v-else class="absolute inset-0 flex items-center justify-center">
        <div class="flex flex-col items-center text-slate-400">
          <i class="fa-solid fa-circle-notch fa-spin text-2xl mb-2"></i>
          <span class="text-xs">正在渲染文档...</span>
        </div>
      </div>
    </div>

    <!-- 3. 底部翻页控制 -->
    <div class="bg-white border-t border-slate-200 p-2 flex justify-center space-x-4 z-10 shrink-0">
      <button
        @click="changePage(-1)"
        :disabled="currentPage <= 1"
        class="px-3 py-1.5 rounded-md text-xs font-medium transition-colors border border-slate-200"
        :class="currentPage <= 1 ? 'text-slate-300 cursor-not-allowed bg-slate-50' : 'text-slate-700 hover:bg-slate-50 hover:border-indigo-300'"
      >
        <i class="fa-solid fa-chevron-left mr-1"></i> 上一页
      </button>

      <button
        @click="changePage(1)"
        :disabled="currentPage >= pageCount"
        class="px-3 py-1.5 rounded-md text-xs font-medium transition-colors border border-slate-200"
        :class="currentPage >= pageCount ? 'text-slate-300 cursor-not-allowed bg-slate-50' : 'text-slate-700 hover:bg-slate-50 hover:border-indigo-300'"
      >
        下一页 <i class="fa-solid fa-chevron-right ml-1"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from 'vue';
import VuePdfEmbed from 'vue-pdf-embed';

const props = defineProps({
  source: { type: String, required: true },
  initialPage: { type: Number, default: 1 },
  fileName: { type: String, default: 'Document.pdf' },
  highlightBboxes: { type: Array, default: () => [] }
});

const scale = ref(1.0); // 默认缩放倍率 (相对于容器宽度)
const currentPage = ref(props.initialPage);
const pageCount = ref(0);
const containerRef = ref(null);
const containerWidth = ref(0); // 响应式容器宽度
let resizeObserver = null;

const pdfDocRef = ref(null);
const originalPageViewport = ref(null);
const imageAspectRatio = ref(null);
const imageNaturalWidth = ref(0);
const imageNaturalHeight = ref(0);

// --- 模式切换逻辑 ---
const useImageMode = computed(() => {
    // 修改：强制关闭图片模式，始终使用 PDF 渲染
    // return props.highlightBboxes && props.highlightBboxes.length > 0;
    return false;
});

const imageUrl = computed(() => {
    if (!props.fileName || !currentPage.value) return '';
    // 注意：请确保此 URL 与你的后端地址匹配
    return `http://localhost:8000/api/pdf/${props.fileName}/${currentPage.value}/image`;
});

const handleImageLoad = (e) => {
    const { naturalWidth, naturalHeight } = e.target;
    if (naturalHeight > 0) {
        imageAspectRatio.value = naturalWidth / naturalHeight;
        imageNaturalWidth.value = naturalWidth;
        imageNaturalHeight.value = naturalHeight;
    }
};

// 核心计算：PDF 实际渲染宽度 = 容器宽度 * 缩放倍率
const pdfWidth = computed(() => {
  // 减去 64px 是为了留出左右 padding (p-8 = 2rem = 32px, 左右共 64px)
  // 确保 PDF 不会贴边，视觉更舒适
  const availableWidth = containerWidth.value - 64;
  if (availableWidth <= 0) return 0;
  return Math.floor(availableWidth * scale.value);
});

// 计算高亮框样式
const highlights = computed(() => {
    if (!props.highlightBboxes || props.highlightBboxes.length === 0) return [];
    // 在图片模式下，只要有 renderWidth 即可，不一定非要 originalPageViewport
    if (pdfWidth.value <= 0) return [];
    if (!useImageMode.value && !originalPageViewport.value) return [];
    
    return props.highlightBboxes.map(item => {
        let bbox = item;
        let page = props.initialPage;

        if (!Array.isArray(item) && item.range) {
             bbox = item.range;
             if (item.page) page = item.page;
        }

        if (page !== currentPage.value) return null;

        if (!Array.isArray(bbox) || bbox.length < 4) return null;
        
        const renderWidth = pdfWidth.value;
        const ratio = imageAspectRatio.value || (originalPageViewport.value ? (originalPageViewport.value.width / originalPageViewport.value.height) : 1.414);
        const renderHeight = renderWidth / ratio;

        const [x1, y1, x2, y2] = bbox;
        
        let sx1, sy1, sx2, sy2;

        // 判断是否为归一化坐标 (0.0 ~ 1.0)
        // 阈值设为 2.0 是为了容错
        const isNormalized = x2 <= 2.0 && y2 <= 2.0;

        if (isNormalized) {
            sx1 = x1 * renderWidth;
            sy1 = y1 * renderHeight;
            sx2 = x2 * renderWidth;
            sy2 = y2 * renderHeight;
        } else {
            // 绝对坐标 (PDF Point 或 Image Pixel)
            let scaleX, scaleY;

            // 修正：后端 LayoutDetection 输出的 bbox 是基于 2x 缩放图片的
            // 而前端 PDF 渲染器基于 1x PDF Point 尺寸
            // 所以需要先将坐标除以 2，还原到 1x 尺度
            const coordScale = 0.5;

            // 优先使用 PDF 原始尺寸 (1x) 来计算缩放比
            if (originalPageViewport.value) {
                scaleX = renderWidth / originalPageViewport.value.width;
                scaleY = renderHeight / originalPageViewport.value.height;
            } else if (useImageMode.value && imageNaturalWidth.value > 0) {
                // 兜底：如果没有 PDF 尺寸 (极少情况)，尝试用图片尺寸反推
                // 假设后端图片是 2x 缩放，所以要乘以 2.0
                scaleX = (renderWidth / imageNaturalWidth.value) * 2.0;
                scaleY = (renderHeight / imageNaturalHeight.value) * 2.0;
            } else {
                // 最后的兜底
                scaleX = 1;
                scaleY = 1;
            }
            
            sx1 = x1 * coordScale * scaleX;
            sy1 = y1 * coordScale * scaleY;
            sx2 = x2 * coordScale * scaleX;
            sy2 = y2 * coordScale * scaleY;
        }

        sx1 = Math.max(0, Math.min(sx1, renderWidth));
        sx2 = Math.max(0, Math.min(sx2, renderWidth));
        sy1 = Math.max(0, Math.min(sy1, renderHeight));
        sy2 = Math.max(0, Math.min(sy2, renderHeight));

        const w = sx2 - sx1;
        const h = sy2 - sy1;

        if (w <= 0 || h <= 0) return null;

        return {
            left: `${sx1}px`,
            top: `${sy1}px`,
            width: `${w}px`,
            height: `${h}px`
        };
    }).filter(Boolean);
});

// 监听页码变化
watch(() => props.initialPage, (newPage) => {
  currentPage.value = newPage;
});

// 监听当前页变化，获取原始尺寸
watch(currentPage, async (newPage) => {
    if (pdfDocRef.value) {
        try {
            const page = await pdfDocRef.value.getPage(newPage);
            const viewport = page.getViewport({ scale: 1.0 });
            originalPageViewport.value = { width: viewport.width, height: viewport.height };
        } catch (e) {
            console.error("Failed to fetch page info", e);
        }
    }
});

// 核心修复：使用 ResizeObserver 监听容器大小变化
onMounted(() => {
  if (containerRef.value) {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        // 获取容器的内容区域宽度
        if (entry.contentRect.width > 0) {
          containerWidth.value = entry.contentRect.width;
        }
      }
    });

    resizeObserver.observe(containerRef.value);
  }
});

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect();
});

const handleLoaded = async (pdfDoc) => {
  pageCount.value = pdfDoc.numPages;
  pdfDocRef.value = pdfDoc;
  
  // 加载完成后立即获取当前页信息
  try {
      const page = await pdfDoc.getPage(currentPage.value);
      const viewport = page.getViewport({ scale: 1.0 });
      originalPageViewport.value = { width: viewport.width, height: viewport.height };
  } catch (e) {
      console.error("Failed to fetch initial page info", e);
  }
};

const changePage = (delta) => {
  const newPage = currentPage.value + delta;
  if (newPage >= 1 && newPage <= pageCount.value) {
    currentPage.value = newPage;
    // 翻页时自动滚回到顶部
    if (containerRef.value) containerRef.value.scrollTop = 0;
  }
};

const changeScale = (delta) => {
  const newScale = scale.value + delta;
  // 限制缩放范围 0.5 ~ 3.0
  if (newScale >= 0.5 && newScale <= 3.0) {
    scale.value = Number(newScale.toFixed(1));
  }
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
