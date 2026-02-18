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
              <div>
                <label class="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">{{ item.label }}</label>
                <select
                  v-model="item.cfg.modelInstance"
                  :disabled="modelOptions.length === 0"
                  class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200 disabled:opacity-60"
                >
                  <option v-if="modelOptions.length === 0" value="">No model instances</option>
                  <option v-for="opt in modelOptions" :key="`${item.key}-${opt.value}`" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
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
import { computed, ref, watch } from 'vue';
import { useModoraStore } from '../composables/useModoraStore';
import {
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

const moduleConfigs = computed(() =>
  MODULE_KEYS.map((key) => ({
    key,
    label: MODULE_LABELS[key],
    cfg: form.value.pipelines[key],
  }))
);

const modelOptions = computed(() => {
  const items = Array.isArray(store.state.modelInstances) ? store.state.modelInstances : [];
  return items.map((item) => {
    const label = item.model || item.id;
    return { value: item.id, label };
  });
});

watch(() => props.isOpen, async (newVal) => {
  if (newVal) {
    await store.loadSettings();
    await store.loadModelInstances();
    form.value = normalizeSettings(store.state.settings);
  }
});

const close = () => {
  emit('close');
};

const save = () => {
  store.updateSettings(form.value);
  close();
};
</script>
