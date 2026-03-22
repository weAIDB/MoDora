<template>
  <div class="relative min-h-screen w-screen overflow-hidden flex items-center justify-center bg-slate-50 dark:bg-slate-950">
    <!-- Animated background elements -->
    <div class="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary-400/20 blur-[120px] animate-pulse pointer-events-none"></div>
    <div class="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-secondary-400/20 blur-[120px] animate-pulse pointer-events-none" style="animation-delay: 2s;"></div>
    
    <div class="relative z-10 w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
      <div class="glass-panel grid w-full overflow-hidden shadow-2xl lg:grid-cols-2 rounded-[2rem] border border-white/60 dark:border-white/10 bg-white/40 dark:bg-slate-900/50 backdrop-blur-2xl">
        
        <!-- Left Section (Branding) -->
        <section class="relative hidden overflow-hidden p-12 lg:flex flex-col justify-between bg-gradient-to-br from-white/60 to-slate-50/40 dark:from-slate-800/60 dark:to-slate-900/40 border-r border-white/40 dark:border-white/5">
          <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMSIgY3k9IjEiIHI9IjEiIGZpbGw9InJnYmEoMTQ4LCAxNjMsIDE4NCwgMC4xKSIvPjwvc3ZnPg==')] [mask-image:linear-gradient(to_bottom_right,white,transparent)]"></div>
          
          <div class="relative z-10">
            <div class="flex items-center gap-3 mb-12">
              <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 text-white shadow-lg shadow-primary-500/30">
                <i class="fa-solid fa-book-open text-xl"></i>
              </div>
              <span class="text-2xl font-black tracking-tight text-slate-900 dark:text-white">MoDora</span>
            </div>
            
            <h1 class="text-4xl font-black leading-tight text-slate-900 dark:text-white mb-6">
              Unlock the power of <br/>
              <span class="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-secondary-500">Multimodal AI</span>
            </h1>
            <p class="text-lg text-slate-600 dark:text-slate-300 max-w-md leading-relaxed">
              Upload documents, ask questions, and explore visual citations with our intelligent analysis assistant.
            </p>
          </div>
        </section>

        <!-- Right Section (Form) -->
        <section class="flex flex-col justify-center px-6 py-10 sm:px-12 sm:py-16 bg-white/70 dark:bg-slate-900/70">
          <div class="mx-auto w-full max-w-sm">
            <div class="text-center mb-8">
              <h2 class="text-3xl font-black tracking-tight text-slate-900 dark:text-white mb-2">Welcome back</h2>
              <p class="text-sm text-slate-500 dark:text-slate-400">
                {{ mode === 'login' ? 'Please enter your details to sign in.' : 'Create an account to get started.' }}
              </p>
            </div>

            <!-- Tab Switcher -->
            <div class="mb-8 flex rounded-xl bg-slate-200/50 dark:bg-slate-800/80 p-1 backdrop-blur-sm">
              <button
                class="flex-1 rounded-lg py-2.5 text-sm font-semibold transition-all duration-200"
                :class="mode === 'login' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'"
                @click="mode = 'login'"
              >
                Sign in
              </button>
              <button
                class="flex-1 rounded-lg py-2.5 text-sm font-semibold transition-all duration-200"
                :class="mode === 'register' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'"
                @click="mode = 'register'"
              >
                Register
              </button>
            </div>

            <form class="space-y-5" @submit.prevent="submit">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">Email address</label>
                <div class="relative">
                  <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
                    <i class="fa-regular fa-envelope"></i>
                  </div>
                  <input
                    v-model.trim="form.email"
                    type="email"
                    autocomplete="email"
                    required
                    class="block w-full rounded-xl border-0 py-3 pl-10 pr-4 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white ring-1 ring-inset ring-slate-200 dark:ring-slate-700 focus:ring-2 focus:ring-inset focus:ring-primary-500 transition-all placeholder:text-slate-400 dark:placeholder:text-slate-500 shadow-sm"
                    placeholder="you@example.com"
                  />
                </div>
              </div>

              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">Password</label>
                <div class="relative">
                  <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
                    <i class="fa-solid fa-lock"></i>
                  </div>
                  <input
                    v-model="form.password"
                    type="password"
                    autocomplete="current-password"
                    required
                    minlength="8"
                    class="block w-full rounded-xl border-0 py-3 pl-10 pr-4 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white ring-1 ring-inset ring-slate-200 dark:ring-slate-700 focus:ring-2 focus:ring-inset focus:ring-primary-500 transition-all placeholder:text-slate-400 dark:placeholder:text-slate-500 shadow-sm"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div v-if="error" class="flex items-center gap-2 rounded-xl bg-rose-50 dark:bg-rose-900/30 p-3 text-sm text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800/50 animate-fade-in">
                <i class="fa-solid fa-circle-exclamation"></i>
                <p>{{ error }}</p>
              </div>

              <button
                type="submit"
                :disabled="submitting"
                class="relative mt-2 w-full rounded-xl bg-gradient-to-r from-primary-600 to-secondary-500 py-3.5 text-sm font-bold text-white shadow-lg shadow-primary-500/25 transition-all duration-300 hover:shadow-primary-500/40 hover:-translate-y-0.5 disabled:translate-y-0 disabled:shadow-none disabled:opacity-70 disabled:cursor-not-allowed overflow-hidden group"
              >
                <div class="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"></div>
                <span class="relative flex items-center justify-center gap-2">
                  <i v-if="submitting" class="fa-solid fa-circle-notch fa-spin"></i>
                  {{ submitting ? 'Processing...' : (mode === 'login' ? 'Sign In' : 'Create Account') }}
                </span>
              </button>
            </form>
          </div>
        </section>
      </div>
      
      <!-- Footer links -->
      <div class="mt-8 text-center text-sm text-slate-500 dark:text-slate-500 font-medium">
        <p>&copy; 2026 MoDora. All rights reserved.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useModoraStore } from '../composables/useModoraStore';

const store = useModoraStore();
const mode = ref('login');
const submitting = ref(false);
const error = ref('');
const form = reactive({
  email: '',
  password: ''
});

const submit = async () => {
  error.value = '';
  submitting.value = true;
  try {
    await store.authenticate(mode.value, {
      email: form.email,
      password: form.password
    });
  } catch (err) {
    error.value = err.message || 'Authentication failed';
  } finally {
    submitting.value = false;
  }
};
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
