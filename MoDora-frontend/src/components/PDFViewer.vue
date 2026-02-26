<template>
  <div class="flex flex-col h-full bg-transparent">
    <!-- 1. Top toolbar -->
    <div class="h-16 flex items-center justify-between px-4 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 shadow-sm z-10 shrink-0">
      <div class="flex items-center space-x-2 min-w-0">
        <span class="font-bold text-slate-700 dark:text-slate-200 text-sm truncate max-w-[150px]" :title="fileName">
          <i class="fa-regular fa-file-pdf text-red-500 mr-2"></i>{{ fileName }}
        </span>
        <span class="text-xs text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded whitespace-nowrap">
          {{ currentPage }} / {{ pageCount }}
        </span>
      </div>

      <div class="flex items-center space-x-2 shrink-0">
        <!-- Zoom controls -->
        <div class="flex items-center bg-slate-100 dark:bg-slate-700 rounded-lg p-1 mr-2">
          <button @click="changeScale(-0.1)" class="w-6 h-6 flex items-center justify-center hover:bg-white dark:hover:bg-slate-600 rounded text-slate-600 dark:text-slate-300 transition">
            <i class="fa-solid fa-minus text-[10px]"></i>
          </button>
          <span class="text-xs w-8 text-center text-slate-500 dark:text-slate-400">{{ Math.round(scale * 100) }}%</span>
          <button @click="changeScale(0.1)" class="w-6 h-6 flex items-center justify-center hover:bg-white dark:hover:bg-slate-600 rounded text-slate-600 dark:text-slate-300 transition">
            <i class="fa-solid fa-plus text-[10px]"></i>
          </button>
        </div>

        <a :href="source" download class="p-2 text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 transition" title="Download Original File">
          <i class="fa-solid fa-download"></i>
        </a>
      </div>
    </div>

    <!-- 2. PDF content area (scrollable) -->
    <div class="flex-1 overflow-auto p-4 md:p-8 flex justify-center custom-scrollbar bg-transparent relative" ref="containerRef">

      <!-- Render area -->
      <!-- Only render when pdfWidth > 0 to avoid flicker during transitions -->
      <div v-if="source && pdfWidth > 0" class="relative shadow-lg transition-all duration-75 ease-out bg-white h-max" :style="{ width: pdfWidth + 'px' }">
        <!-- Mode A: standard PDF reading -->
        <VuePdfEmbed
          v-show="!useImageMode"
          ref="pdfRef"
          :source="source"
          :page="currentPage"
          :width="pdfWidth"
          @loaded="handleLoaded"
          c-map-url="https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/cmaps/"
          c-map-packed
          standard-font-data-url="https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/standard_fonts/"
          text-layer
          annotation-layer
        />

        <!-- Mode B: source image mode (high precision) -->
        <img 
          v-if="useImageMode"
          :src="imageUrl"
          class="w-full h-auto block"
          alt="Page View"
          @load="handleImageLoad"
        />
        
        <!-- Highlight overlay -->
        <div v-for="(hl, idx) in highlights" :key="idx"
             class="absolute bg-purple-500/30 animate-pulse pointer-events-none z-10 mix-blend-multiply dark:mix-blend-normal rounded-md transform scale-[1.05]"
             :style="hl"
        ></div>
      </div>

      <!-- Loading or initial state -->
      <div v-else class="absolute inset-0 flex items-center justify-center">
        <div class="flex flex-col items-center text-slate-400 dark:text-slate-500">
          <i class="fa-solid fa-circle-notch fa-spin text-2xl mb-2"></i>
          <span class="text-xs">Rendering document...</span>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div class="bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 p-2 flex justify-center space-x-4 z-10 shrink-0">
      <button
        @click="changePage(-1)"
        :disabled="currentPage <= 1"
        class="px-3 py-1.5 rounded-md text-xs font-medium transition-colors border border-slate-200 dark:border-slate-600"
        :class="currentPage <= 1 ? 'text-slate-300 dark:text-slate-600 cursor-not-allowed bg-slate-50 dark:bg-slate-800' : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:border-primary-300 dark:hover:border-primary-500'"
      >
        <i class="fa-solid fa-chevron-left mr-1"></i> Previous
      </button>
      <button
        @click="changePage(1)"
        :disabled="currentPage >= pageCount"
        class="px-3 py-1.5 rounded-md text-xs font-medium transition-colors border border-slate-200 dark:border-slate-600"
        :class="currentPage >= pageCount ? 'text-slate-300 dark:text-slate-600 cursor-not-allowed bg-slate-50 dark:bg-slate-800' : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 hover:border-primary-300 dark:hover:border-primary-500'"
      >
        Next <i class="fa-solid fa-chevron-right ml-1"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from 'vue';
import VuePdfEmbed from 'vue-pdf-embed';
import * as pdfjs from 'pdfjs-dist';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

// Import required styles to render text and annotation layers
import 'vue-pdf-embed/dist/styles/textLayer.css';
import 'vue-pdf-embed/dist/styles/annotationLayer.css';

const props = defineProps({
  source: { type: String, required: true },
  initialPage: { type: Number, default: 1 },
  fileName: { type: String, default: 'Document.pdf' },
  highlightBboxes: { type: Array, default: () => [] }
});

const scale = ref(1.0); // Default zoom (relative to container width)
const currentPage = ref(props.initialPage);
const pageCount = ref(0);
const containerRef = ref(null);
const containerWidth = ref(0); // Reactive container width
let resizeObserver = null;

const pdfDocRef = ref(null);
const originalPageViewport = ref(null);
const imageAspectRatio = ref(null);
const imageNaturalWidth = ref(0);
const imageNaturalHeight = ref(0);

// --- Mode switching logic ---
const useImageMode = computed(() => {
    // Use image mode only when highlights exist (for source tracing)
    return props.highlightBboxes && props.highlightBboxes.length > 0;
});

const imageUrl = computed(() => {
    if (!props.fileName || !currentPage.value) return '';
    // Use relative path to go through the Vite proxy
    return `/api/pdf/${props.fileName}/${currentPage.value}/image`;
});

const handleImageLoad = (e) => {
    const { naturalWidth, naturalHeight } = e.target;
    if (naturalHeight > 0) {
        imageAspectRatio.value = naturalWidth / naturalHeight;
        imageNaturalWidth.value = naturalWidth;
        imageNaturalHeight.value = naturalHeight;
    }
};

// Core calculation: PDF render width = container width * zoom
const pdfWidth = computed(() => {
  // Subtract 64px to leave horizontal padding (p-8 = 2rem = 32px on each side)
  // Keep the PDF from touching edges for better readability
  const availableWidth = containerWidth.value - 64;
  if (availableWidth <= 0) return 0;
  return Math.floor(availableWidth * scale.value);
});

// Compute highlight styles
const highlights = computed(() => {
    if (!props.highlightBboxes || props.highlightBboxes.length === 0) return [];
    // In image mode, renderWidth is enough; originalPageViewport is optional
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

        // Check if coordinates are normalized (0.0 ~ 1.0)
        // Threshold set to 2.0 for tolerance
        const isNormalized = x2 <= 2.0 && y2 <= 2.0;

        if (isNormalized) {
            sx1 = x1 * renderWidth;
            sy1 = y1 * renderHeight;
            sx2 = x2 * renderWidth;
            sy2 = y2 * renderHeight;
        } else {
            // Absolute coordinates (PDF points or image pixels)
            let scaleX, scaleY;

            // Coordinate correction: use backend coordinates directly
            const coordScale = 1.0;

            // Prefer original PDF size (1x) for scale calculation
            if (originalPageViewport.value) {
                scaleX = renderWidth / originalPageViewport.value.width;
                scaleY = renderHeight / originalPageViewport.value.height;
            } else if (useImageMode.value && imageNaturalWidth.value > 0) {
                // Fallback: if PDF size missing (rare), infer from image size
                // Assume backend image is 2x scale, so multiply by 2.0
                scaleX = (renderWidth / imageNaturalWidth.value) * 2.0;
                scaleY = (renderHeight / imageNaturalHeight.value) * 2.0;
            } else {
                // Final fallback
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

// Watch page number changes
watch(() => props.initialPage, (newPage) => {
  currentPage.value = newPage;
});

// Watch current page changes to get original size
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

// Core fix: use ResizeObserver to track container size changes
onMounted(() => {
  if (containerRef.value) {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        // Get container content width
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
  
  // Fetch current page info immediately after load
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
    // Auto-scroll to top when changing pages
    if (containerRef.value) containerRef.value.scrollTop = 0;
  }
};

const changeScale = (delta) => {
  const newScale = scale.value + delta;
  // Limit zoom range to 0.5 ~ 3.0
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
