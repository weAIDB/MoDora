<template>
  <div v-if="isOpen" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm" @click.self="cancel">
    <div class="bg-white rounded-xl shadow-2xl w-[600px] max-w-[90vw] flex flex-col max-h-[85vh] animate-scale-in">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50 rounded-t-xl">
        <h3 class="text-lg font-bold text-slate-700 flex items-center">
          <i class="fa-solid fa-pen-to-square mr-2 text-indigo-500"></i>
          Edit Node
        </h3>
        <button @click="cancel" class="text-slate-400 hover:text-slate-600 transition">
          <i class="fa-solid fa-xmark text-xl"></i>
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 overflow-y-auto space-y-4 custom-scrollbar">
        <!-- Node Label -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Node Name (Label)</label>
          <input 
            v-model="form.label" 
            type="text" 
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
            placeholder="Enter node name"
          />
        </div>

        <!-- Node Type -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Type</label>
          <select 
            v-model="form.type" 
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition bg-white"
          >
            <option value="text">Text</option>
            <option value="image">Image</option>
            <option value="table">Table</option>
            <option value="chart">Chart</option>
            <option value="root">Root</option>
            <option value="chapter">Chapter</option>
            <option value="section">Section</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        <!-- Metadata -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Metadata (Summary)</label>
          <textarea 
            v-model="form.metadata" 
            rows="3" 
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition resize-y text-sm"
            placeholder="Enter metadata or summary..."
          ></textarea>
        </div>

        <!-- Data -->
        <div class="flex-1 flex flex-col min-h-[150px]">
          <label class="block text-sm font-medium text-slate-700 mb-1">Data (Content)</label>
          <textarea 
            v-model="form.data" 
            rows="6" 
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition resize-y text-sm font-mono bg-slate-50"
            placeholder="Enter full content data..."
          ></textarea>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-slate-100 flex justify-end space-x-3 bg-slate-50 rounded-b-xl">
        <button 
          @click="cancel" 
          class="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition"
        >
          Cancel
        </button>
        <button 
          @click="save" 
          class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-md hover:shadow-lg transition flex items-center"
        >
          <i class="fa-solid fa-check mr-2"></i>
          Save Changes
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  initialData: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['update:modelValue', 'save']);

const isOpen = ref(false);
const form = ref({
  id: '',
  label: '',
  type: 'text',
  metadata: '',
  data: ''
});

watch(() => props.modelValue, (val) => {
  isOpen.value = val;
});

watch(() => props.initialData, (val) => {
  if (val) {
    form.value = {
      id: val.id,
      label: val.label || val.title || 'Untitled', // Compatible with different naming
      type: val.type || 'text',
      metadata: val.metadata || '',
      data: val.data || ''
    };
  }
}, { deep: true, immediate: true });

const cancel = () => {
  emit('update:modelValue', false);
};

const save = () => {
  emit('save', { ...form.value });
  emit('update:modelValue', false);
};
</script>

<style scoped>
.animate-scale-in {
  animation: scaleIn 0.2s ease-out;
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: #f1f5f9;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 3px;
}
</style>
