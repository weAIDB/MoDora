<template>
  <div class="mermaid-container w-full flex justify-center bg-white p-4 rounded-lg overflow-x-auto">
    <!--
      重要：这里的唯一 ID 是为了防止多个图表冲突
      key 绑定 chartCode 强制 Vue 在代码变更时重新创建 DOM 元素
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
import mermaid from 'mermaid'; // 核心修复：显式引入 npm 包

const props = defineProps({
  chartCode: {
    type: String,
    required: true
  }
});

const mermaidRef = ref(null);

// 初始化 Mermaid 配置
mermaid.initialize({
  startOnLoad: false, // 必须为 false，因为我们要手动调用 run
  theme: 'neutral',
  securityLevel: 'loose',
  fontFamily: 'sans-serif'
});

const renderChart = async () => {
  await nextTick();

  if (mermaidRef.value) {
    try {
      // 1. 重置 DOM 内容为原始代码 (防止 Mermaid 重复渲染报错)
      mermaidRef.value.removeAttribute('data-processed');
      mermaidRef.value.innerHTML = props.chartCode;

      // 2. 手动运行渲染
      await mermaid.run({
        nodes: [mermaidRef.value]
      });
    } catch (error) {
      console.error('Mermaid 渲染失败:', error);
      // 出错时显示简单的错误提示，避免界面崩坏
      if (mermaidRef.value) {
        mermaidRef.value.innerHTML = `<span class="text-red-400">图表渲染错误</span>`;
      }
    }
  }
};

onMounted(() => {
  renderChart();
});

// 监听数据变化重新渲染
watch(() => props.chartCode, () => {
  renderChart();
});
</script>

<style scoped>
/* 避免 pre 标签的默认样式干扰 */
pre.mermaid {
  margin: 0;
  white-space: pre-wrap;
}
</style>
