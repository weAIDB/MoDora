<template>
  <div class="prose prose-sm md:prose-base max-w-none break-words select-text cursor-text" 
       :class="[
         isUser ? 'prose-invert text-white' : 'prose-slate text-slate-700 dark:text-slate-200 dark:prose-invert'
       ]"
       v-html="renderedContent">
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const props = defineProps({
  content: {
    type: String,
    required: true,
    default: ''
  },
  isUser: {
    type: Boolean,
    default: false
  }
});

// Configure marked
marked.setOptions({
  gfm: true, // Enable GitHub-flavored Markdown
  breaks: true, // Enable line breaks
});

const renderedContent = computed(() => {
  if (!props.content) return '';
  const rawHtml = marked.parse(props.content);
  return DOMPurify.sanitize(rawHtml);
});
</script>

<style>
/* Minor custom tweaks for prose */
.prose p {
  margin-bottom: 0.5em;
  margin-top: 0.5em;
}
.prose p:first-child {
  margin-top: 0;
}
.prose p:last-child {
  margin-bottom: 0;
}
.prose pre {
  background-color: #1e293b; /* slate-800 */
  border-radius: 0.5rem;
  padding: 0.75rem;
}
.prose code {
  color: #ef4444; /* red-500 */
  background-color: rgba(241, 245, 249, 0.5); /* slate-100 */
  padding: 0.1rem 0.3rem;
  border-radius: 0.25rem;
  font-weight: 500;
}
.prose-invert code {
  color: #fca5a5; /* red-300 */
  background-color: rgba(255, 255, 255, 0.1);
}
.prose a {
  color: #6366f1; /* indigo-500 */
  text-decoration: none;
}
.prose a:hover {
  text-decoration: underline;
}
.prose-invert a {
  color: #a5b4fc; /* indigo-300 */
}
</style>
