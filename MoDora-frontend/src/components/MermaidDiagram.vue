<template>
  <div class="mermaid-container w-full flex justify-center bg-white p-4 rounded-lg overflow-x-auto">
    <!--
      Important: the unique ID prevents conflicts across multiple charts
      key binds chartCode to force Vue to recreate the DOM when code changes
    -->
    <pre
      ref="mermaidRef"
      class="mermaid text-xs text-center"
      style="background: transparent;"
    >{{ chartCode }}</pre>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue';
import mermaid from 'mermaid'; // Core fix: explicitly import npm package

const props = defineProps({
  chartCode: {
    type: String,
    required: true
  }
});

const mermaidRef = ref(null);

// Initialize Mermaid configuration
mermaid.initialize({
  startOnLoad: false, // Must be false because run is called manually
  theme: 'neutral',
  securityLevel: 'loose',
  fontFamily: 'sans-serif'
});

const renderChart = async () => {
  await nextTick();

  if (mermaidRef.value) {
    try {
      // 1. Reset DOM content to raw code (avoid duplicate render errors)
      mermaidRef.value.removeAttribute('data-processed');
      mermaidRef.value.innerHTML = props.chartCode;

      // 2. Run rendering manually
      await mermaid.run({
        nodes: [mermaidRef.value]
      });
    } catch (error) {
      console.error('Mermaid render failed:', error);
      // Show a simple error message to avoid breaking the UI
      if (mermaidRef.value) {
        mermaidRef.value.innerHTML = `<span class="text-red-400">Diagram render error</span>`;
      }
    }
  }
};

onMounted(() => {
  renderChart();
});

// Re-render when data changes
watch(() => props.chartCode, () => {
  renderChart();
});
</script>

<style scoped>
/* Avoid default pre styles interfering */
pre.mermaid {
  margin: 0;
  white-space: pre-wrap;
}
</style>
