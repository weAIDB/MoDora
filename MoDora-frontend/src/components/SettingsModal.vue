<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- 背景遮罩 -->
    <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" @click="close"></div>
    
    <!-- 弹窗主体 -->
    <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in duration-200">
      <!-- 头部 -->
      <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/50">
        <h3 class="font-bold text-slate-800 dark:text-slate-100 flex items-center">
          <i class="fa-solid fa-gear text-primary-500 mr-2"></i>
          Global Settings
        </h3>
        <button @click="close" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <!-- 内容表单 -->
      <div class="p-6 overflow-y-auto custom-scrollbar space-y-5">
        
        <!-- API Configuration -->
        <div class="space-y-3">
          <label class="text-xs font-bold text-slate-500 uppercase tracking-wider block">API Configuration</label>
          
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Base URL</label>
            <input 
              v-model="form.baseUrl" 
              type="text" 
              placeholder="e.g. https://api.openai.com/v1"
              class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">API Key</label>
            <div class="relative">
              <input 
                v-model="form.apiKey" 
                :type="showKey ? 'text' : 'password'" 
                placeholder="sk-..."
                class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200 pr-10"
              >
              <button 
                @click="showKey = !showKey"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <i class="fa-solid" :class="showKey ? 'fa-eye-slash' : 'fa-eye'"></i>
              </button>
            </div>
          </div>
        </div>

        <div class="h-px bg-slate-100 dark:bg-slate-700"></div>

        <!-- Model Selection -->
        <div class="space-y-3">
          <label class="text-xs font-bold text-slate-500 uppercase tracking-wider block">LLM Running Mode</label>
          
          <div class="grid grid-cols-2 gap-3">
            <button 
              @click="form.selectedMode = 'local'"
              :class="form.selectedMode === 'local' ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/30' : 'bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700'"
              class="px-4 py-3 rounded-xl text-sm font-bold transition-all flex flex-col items-center justify-center space-y-1 active:scale-95"
            >
              <i class="fa-solid fa-server text-lg"></i>
              <span>Local LLM</span>
            </button>
            <button 
              @click="form.selectedMode = 'remote'"
              :class="form.selectedMode === 'remote' ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/30' : 'bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700'"
              class="px-4 py-3 rounded-xl text-sm font-bold transition-all flex flex-col items-center justify-center space-y-1 active:scale-95"
            >
              <i class="fa-solid fa-cloud text-lg"></i>
              <span>Remote API</span>
            </button>
          </div>
          <p class="text-[10px] text-slate-400 dark:text-slate-500 italic px-1">
            * Selected mode will be passed to backend factory for client initialization.
          </p>
        </div>

        <div class="h-px bg-slate-100 dark:bg-slate-700"></div>

        <!-- Model Options -->
        <div class="space-y-3">
          <label class="text-xs font-bold text-slate-500 uppercase tracking-wider block">Model Options</label>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Tree Model</label>
            <select
              v-model="form.treeModel"
              class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200"
            >
              <option v-for="opt in activeModelOptions" :key="`tree-${opt.value}`" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">QA Model</label>
            <select
              v-model="form.qaModel"
              class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200"
            >
              <option v-for="opt in activeModelOptions" :key="`qa-${opt.value}`" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>

      </div>

      <!-- 底部按钮 -->
      <div class="p-4 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-700 flex justify-end space-x-3">
        <button 
          @click="close"
          class="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button 
          @click="save"
          class="px-4 py-2 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 active:scale-95 rounded-lg shadow-lg shadow-primary-500/30 transition-all flex items-center"
        >
          <i class="fa-solid fa-check mr-2"></i>
          Save Changes
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useModoraStore } from '../composables/useModoraStore';
import { DEFAULT_SETTINGS, normalizeSettings } from '../config/settingsContract';

const props = defineProps({
  isOpen: Boolean
});

const emit = defineEmits(['close']);
const store = useModoraStore();

const LOCAL_MODELS = [
  { value: 'qwen-vl-local', label: 'Qwen-VL Local' },
];

const REMOTE_MODELS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
];

const showKey = ref(false);
const form = ref({ ...DEFAULT_SETTINGS });
const activeModelOptions = computed(() =>
  form.value.selectedMode === 'local' ? LOCAL_MODELS : REMOTE_MODELS
);

// 初始化表单数据
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    form.value = normalizeSettings(store.state.settings);
  }
});

watch(
  () => form.value.selectedMode,
  () => {
    const options = activeModelOptions.value;
    const values = new Set(options.map((opt) => opt.value));
    if (!values.has(form.value.treeModel)) {
      form.value.treeModel = options[0].value;
    }
    if (!values.has(form.value.qaModel)) {
      form.value.qaModel = options[0].value;
    }
  }
);

const close = () => {
  emit('close');
};

const save = () => {
  store.updateSettings(form.value);
  close();
};
</script>
