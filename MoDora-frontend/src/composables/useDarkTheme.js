import { ref, onMounted } from 'vue';

const isDark = ref(false);

export function useDarkTheme() {
  
  // 切换主题
  const toggleTheme = () => {
    isDark.value = !isDark.value;
    applyTheme();
  };

  // 应用主题到 html 标签
  const applyTheme = () => {
    if (isDark.value) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  // 初始化
  onMounted(() => {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
      isDark.value = true;
    } else {
      isDark.value = false;
    }
    applyTheme();
  });

  return {
    isDark,
    toggleTheme
  };
}
