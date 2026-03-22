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
        <div
          v-if="feedbackMessage"
          class="rounded-xl border px-4 py-3 text-sm"
          :class="feedbackType === 'error'
            ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/20 dark:text-rose-300'
            : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/20 dark:text-emerald-300'"
        >
          {{ feedbackMessage }}
        </div>

        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <label class="text-xs font-bold text-slate-500 uppercase tracking-wider block">Model Instances</label>
            <button
              @click="toggleCreateModel"
              class="px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 rounded-lg transition-colors"
            >
              <i class="fa-solid fa-plus mr-2"></i>
              Add Model
            </button>
          </div>

          <div
            v-if="modelOptions.length > 0"
            class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/20 divide-y divide-slate-100 dark:divide-slate-800"
          >
            <div
              v-for="item in modelItems"
              :key="item.id"
              class="flex items-center justify-between gap-4 p-4"
            >
              <div class="min-w-0">
                <div class="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{{ item.model || item.id }}</div>
                <div class="text-xs text-slate-500 truncate">{{ item.base_url || 'No base URL' }}</div>
              </div>
              <button
                @click="handleDeleteModel(item.id)"
                class="px-3 py-1.5 text-sm font-medium text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 rounded-lg transition-colors"
              >
                <i class="fa-solid fa-trash-can mr-2"></i>
                Delete
              </button>
            </div>
          </div>

          <div
            v-if="showCreateModel"
            class="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-900/20 p-4 space-y-3"
          >
            <div class="grid gap-3 md:grid-cols-2">
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Model Name</label>
                <input
                  v-model="newModel.modelName"
                  type="text"
                  placeholder="e.g. gpt-4.1"
                  class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Base URL</label>
                <input
                  v-model="newModel.baseUrl"
                  type="text"
                  placeholder="https://api.example.com/v1"
                  class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200"
                />
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">API Key</label>
              <input
                v-model="newModel.apiKey"
                type="password"
                placeholder="sk-..."
                class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all dark:text-slate-200"
              />
            </div>
            <p v-if="createError" class="text-sm text-rose-600">{{ createError }}</p>
            <div class="flex justify-end gap-2">
              <button
                @click="cancelCreateModel"
                class="px-3 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                @click="submitCreateModel"
                :disabled="isCreatingModel"
                class="px-3 py-2 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 rounded-lg transition-colors disabled:opacity-60"
              >
                {{ isCreatingModel ? 'Adding...' : 'Create Instance' }}
              </button>
            </div>
          </div>
        </div>

        <div class="h-px bg-slate-100 dark:bg-slate-700"></div>

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
const showCreateModel = ref(false);
const isCreatingModel = ref(false);
const feedbackMessage = ref('');
const feedbackType = ref('error');
const newModel = ref({
  modelName: '',
  baseUrl: '',
  apiKey: '',
});

const moduleConfigs = computed(() =>
  MODULE_KEYS.map((key) => ({
    key,
    label: MODULE_LABELS[key],
    cfg: form.value.pipelines[key],
  }))
);

const modelItems = computed(() =>
  Array.isArray(store.state.modelInstances) ? store.state.modelInstances : []
);

const modelOptions = computed(() => {
  return modelItems.value.map((item) => {
    const label = item.model || item.id;
    return { value: item.id, label };
  });
});

watch(() => props.isOpen, async (newVal) => {
  if (newVal) {
    await store.loadSettings();
    await store.loadModelInstances();
    form.value = normalizeSettings(store.state.settings);
    cancelCreateModel();
  }
});

const close = () => {
  emit('close');
};

const resetNewModel = () => {
  newModel.value = {
    modelName: '',
    baseUrl: '',
    apiKey: '',
  };
};

const toggleCreateModel = () => {
  showCreateModel.value = !showCreateModel.value;
  if (!showCreateModel.value) {
    resetNewModel();
  }
};

const cancelCreateModel = () => {
  showCreateModel.value = false;
  isCreatingModel.value = false;
  resetNewModel();
};

const submitCreateModel = async () => {
  feedbackMessage.value = '';
  isCreatingModel.value = true;
  try {
    const instance = await store.createModelInstance(newModel.value);
    const instanceId = instance?.id || newModel.value.modelName.trim();
    for (const key of MODULE_KEYS) {
      const current = form.value.pipelines[key]?.modelInstance;
      if (!current || !modelOptions.value.some((item) => item.value === current)) {
        form.value.pipelines[key].modelInstance = instanceId;
      }
    }
    feedbackType.value = 'success';
    feedbackMessage.value = `Model instance "${instanceId}" created.`;
    cancelCreateModel();
  } catch (error) {
    feedbackType.value = 'error';
    feedbackMessage.value = error instanceof Error ? error.message : 'Failed to create model instance';
  } finally {
    isCreatingModel.value = false;
  }
};

const handleDeleteModel = async (instanceId) => {
  feedbackMessage.value = '';
  try {
    await store.deleteModelInstance(instanceId);
  } catch (error) {
    feedbackType.value = 'error';
    feedbackMessage.value = error instanceof Error ? error.message : 'Failed to delete model instance';
    return;
  }

  for (const key of MODULE_KEYS) {
    if (form.value.pipelines[key]?.modelInstance === instanceId) {
      form.value.pipelines[key].modelInstance = modelOptions.value[0]?.value || '';
    }
  }
  feedbackType.value = 'success';
  feedbackMessage.value = `Model instance "${instanceId}" deleted.`;
};

const save = async () => {
  feedbackMessage.value = '';
  await store.updateSettings(form.value);
  close();
};
</script>
