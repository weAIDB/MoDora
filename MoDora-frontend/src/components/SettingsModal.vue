<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" @click="close"></div>

    <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[92vh] animate-in fade-in zoom-in duration-200">
      <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/50">
        <h3 class="font-bold text-slate-800 dark:text-slate-100 flex items-center">
          <i class="fa-solid fa-gear text-primary-500 mr-2"></i>
          Global Settings
        </h3>
        <button @click="close" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <div class="p-6 overflow-y-auto custom-scrollbar space-y-5">
        <div class="space-y-3">
          <label class="text-xs font-bold text-slate-500 uppercase tracking-wider block">OCR Model</label>
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Layout Engine</label>
            <select
              v-model="form.ocr.provider"
              class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200"
            >
              <option v-for="opt in OCR_MODEL_OPTIONS" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>

        <div class="h-px bg-slate-100 dark:bg-slate-700"></div>

        <div class="space-y-3">
          <label class="text-xs font-bold text-slate-500 uppercase tracking-wider block">Module Configurations</label>
          <div class="space-y-4">
            <div
              v-for="item in moduleConfigs"
              :key="item.key"
              class="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/20 p-4 space-y-3"
            >
              <div class="flex items-center justify-between">
                <span class="text-sm font-semibold text-slate-700 dark:text-slate-200">{{ item.label }}</span>
                <div class="grid grid-cols-2 gap-2 w-[220px]">
                  <button
                    @click="item.cfg.mode = 'local'"
                    :class="item.cfg.mode === 'local' ? 'bg-primary-500 text-white shadow-md shadow-primary-500/20' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700'"
                    class="px-2 py-1.5 rounded-lg text-xs font-semibold transition-all"
                  >
                    Local
                  </button>
                  <button
                    @click="item.cfg.mode = 'remote'"
                    :class="item.cfg.mode === 'remote' ? 'bg-primary-500 text-white shadow-md shadow-primary-500/20' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700'"
                    class="px-2 py-1.5 rounded-lg text-xs font-semibold transition-all"
                  >
                    Remote
                  </button>
                </div>
              </div>

              <div :class="item.cfg.mode === 'remote' ? 'grid grid-cols-1 md:grid-cols-2 gap-3' : 'grid grid-cols-1 gap-3'">
                <div>
                  <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Model</label>
                  <select
                    v-model="item.cfg.model"
                    class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200"
                  >
                    <option v-for="opt in ALL_MODEL_OPTIONS" :key="`${item.key}-${opt.value}`" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                </div>

                <div v-if="item.cfg.mode === 'remote'">
                  <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Base URL</label>
                  <input
                    v-model="item.cfg.baseUrl"
                    type="text"
                    placeholder="https://api.openai.com/v1"
                    class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200"
                  >
                </div>
              </div>

              <div v-if="item.cfg.mode === 'remote'">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">API Key</label>
                <div class="relative">
                  <input
                    v-model="item.cfg.apiKey"
                    :type="showKeys[item.key] ? 'text' : 'password'"
                    placeholder="sk-..."
                    class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200 pr-10"
                  >
                  <button
                    @click="toggleShowKey(item.key)"
                    class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                  >
                    <i class="fa-solid" :class="showKeys[item.key] ? 'fa-eye-slash' : 'fa-eye'"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

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
import { computed, reactive, ref, watch } from 'vue';
import { useModoraStore } from '../composables/useModoraStore';
import {
  ALL_MODEL_OPTIONS,
  DEFAULT_SETTINGS,
  MODULE_KEYS,
  MODULE_LABELS,
  OCR_MODEL_OPTIONS,
  normalizeSettings,
} from '../config/settingsContract';

const props = defineProps({
  isOpen: Boolean
});

const emit = defineEmits(['close']);
const store = useModoraStore();

const form = ref(normalizeSettings(DEFAULT_SETTINGS));
const showKeys = reactive(
  MODULE_KEYS.reduce((acc, key) => {
    acc[key] = false;
    return acc;
  }, {})
);

const moduleConfigs = computed(() =>
  MODULE_KEYS.map((key) => ({
    key,
    label: MODULE_LABELS[key],
    cfg: form.value.pipelines[key],
  }))
);

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    form.value = normalizeSettings(store.state.settings);
  }
});

const toggleShowKey = (key) => {
  showKeys[key] = !showKeys[key];
};

const close = () => {
  emit('close');
};

const save = () => {
  store.updateSettings(form.value);
  close();
};
</script>
