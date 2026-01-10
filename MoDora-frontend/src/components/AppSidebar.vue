<template>
  <!-- 
    AppSidebar.vue Refactoring:
    1. Remove border and bg of outer container (handled by parent glass-panel)
    2. Use bg-transparent 
  -->
  <aside class="flex flex-col h-full bg-transparent">
    <!-- Header -->
    <div class="h-16 px-6 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0 rounded-t-3xl">
      <div class="flex items-center">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center text-white mr-3 shadow-lg shadow-primary-500/30">
          <i class="fa-solid fa-book text-lg"></i>
        </div>
        <h2 class="font-bold text-slate-800 dark:text-slate-100 text-lg tracking-tight">MoDora</h2>
      </div>
      
      <div class="flex items-center">
        <!-- 设置按钮 -->
        <button 
          @click="$emit('open-settings')"
          class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary-500 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors mr-2"
          title="Global Settings"
        >
          <i class="fa-solid fa-gear"></i>
        </button>

        <!-- 主题切换按钮 -->
        <button 
          @click="toggleTheme" 
          class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-primary-500 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
        >
          <i v-if="isDark" class="fa-solid fa-sun text-yellow-400"></i>
          <i v-else class="fa-solid fa-moon"></i>
        </button>
      </div>
    </div>

    <!-- List Area -->
    <div class="flex-1 overflow-y-auto p-4 custom-scrollbar flex flex-col space-y-6">
      
      <!-- Session Management Area -->
      <div>
        <div class="flex items-center justify-between mb-2 px-2">
           <h3 class="text-[10px] font-extrabold text-slate-400 dark:text-slate-500 uppercase tracking-widest">Sessions</h3>
           <button @click="store.createNewSession()" class="text-xs bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 px-2 py-1 rounded hover:bg-primary-100 dark:hover:bg-primary-900/50 transition">
             <i class="fa-solid fa-plus mr-1"></i> New
           </button>
        </div>
        
        <ul class="space-y-2">
           <li v-for="sess in store.state.sessions" :key="sess.id"
               @click="store.setActiveSession(sess.id)"
               class="group relative flex items-center justify-between p-2.5 rounded-lg transition-all cursor-pointer"
               :class="store.state.activeSessionId === sess.id 
                  ? 'bg-white dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700' 
                  : 'hover:bg-white/50 dark:hover:bg-slate-800/50 border border-transparent'"
           >
              <div class="flex items-center min-w-0">
                 <div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 shrink-0"
                      :class="store.state.activeSessionId === sess.id ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-400'">
                    <i class="fa-regular fa-comments text-xs"></i>
                 </div>
                 <div class="flex flex-col min-w-0 flex-1">
                    <div v-if="editingSessionId === sess.id" class="mr-2">
                       <input 
                         ref="editInputRef"
                         v-model="editingName"
                         @blur="saveEditing(sess.id)"
                         @keyup.enter="saveEditing(sess.id)"
                         @click.stop
                         class="w-full text-xs font-bold bg-white dark:bg-slate-700 border border-primary-300 dark:border-primary-600 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-primary-500"
                       />
                    </div>
                    <span v-else class="text-xs font-bold truncate" :class="store.state.activeSessionId === sess.id ? 'text-slate-800 dark:text-slate-200' : 'text-slate-600 dark:text-slate-400'">{{ sess.name }}</span>
                    <span class="text-[10px] text-slate-400 truncate">{{ sess.docs.length }} docs · {{ sess.messages.length }} msgs</span>
                 </div>
              </div>
              
              <div class="flex items-center">
                  <!-- Rename Session (Icon) -->
                  <button @click.stop="startEditing(sess)" class="w-6 h-6 rounded flex items-center justify-center text-slate-300 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition opacity-0 group-hover:opacity-100">
                     <i class="fa-solid fa-pen text-[10px]"></i>
                  </button>
                  
                  <!-- Delete Session -->
                  <button @click.stop="store.deleteSession(sess.id)" class="w-6 h-6 rounded flex items-center justify-center text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition opacity-0 group-hover:opacity-100">
                     <i class="fa-solid fa-trash text-[10px]"></i>
                  </button>
              </div>
          </li>
        </ul>
      </div>

      <div class="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent"></div>

      <!-- Current Session Documents Area -->
      <div v-if="store.getActiveSession()">
         <div class="flex items-center justify-between mb-3 px-2">
            <h3 class="text-[10px] font-extrabold text-slate-400 dark:text-slate-500 uppercase tracking-widest">
               Current Docs ({{ store.getActiveSession().docs.length }})
            </h3>
            <button 
              v-if="store.getActiveSession().docs.length > 0"
              @click="openSessionStats" 
              class="text-[10px] text-primary-500 hover:text-primary-600 font-bold flex items-center"
            >
              <i class="fa-solid fa-chart-line mr-1"></i> Stats
            </button>
         </div>
         
         <!-- Statistics Panel (Session) -->
         <div v-if="showingSessionStats" class="mb-4 p-3 bg-primary-50 dark:bg-primary-900/20 rounded-xl border border-primary-100 dark:border-primary-800 relative animate-in fade-in slide-in-from-top-2">
            <button @click="showingSessionStats = false" class="absolute top-2 right-2 text-primary-400 hover:text-primary-600">
               <i class="fa-solid fa-xmark text-xs"></i>
            </button>
            <h4 class="text-[10px] font-bold text-primary-700 dark:text-primary-300 uppercase mb-2">Session Overview</h4>
            <div v-if="store.state.sessionStats" class="grid grid-cols-2 gap-2 text-[10px]">
               <div class="flex flex-col">
                  <span class="text-slate-400">Avg Pages</span>
                  <span class="font-bold text-slate-700 dark:text-slate-200">{{ store.state.sessionStats.avg_pages.toFixed(1) }}</span>
               </div>
               <div class="flex flex-col">
                  <span class="text-slate-400">Avg Nodes</span>
                  <span class="font-bold text-slate-700 dark:text-slate-200">{{ store.state.sessionStats.avg_nodes.toFixed(1) }}</span>
               </div>
               <div class="flex flex-col col-span-2 mt-1">
                  <span class="text-slate-400 mb-1">Total Elements</span>
                  <div class="flex flex-wrap gap-2">
                     <span v-for="(v, k) in store.state.sessionStats.total_counts" :key="k" class="bg-white dark:bg-slate-800 px-1.5 py-0.5 rounded border border-slate-100 dark:border-slate-700">
                        {{ k }}: {{ v }}
                     </span>
                  </div>
               </div>
            </div>
            <div v-else class="text-[10px] text-primary-400 animate-pulse">Calculating...</div>
         </div>
         
        <!-- Add Document Button Area -->
        <div class="mb-3 flex gap-2">
           <!-- Local Upload -->
           <div 
            @click="triggerUpload"
            class="flex-1 group flex items-center justify-center h-12 border border-dashed border-primary-300/50 rounded-lg cursor-pointer hover:border-primary-500 hover:bg-white/50 transition-all relative overflow-hidden"
          >
            <div v-if="!store.state.isUploading" class="flex flex-col items-center text-slate-400 group-hover:text-primary-600">
               <i class="fa-solid fa-cloud-arrow-up text-sm mb-1"></i>
               <span class="text-[10px] font-bold uppercase tracking-tighter">Local</span>
            </div>
            <div v-else class="text-primary-600 flex items-center text-xs font-bold px-4 w-full">
               <i class="fa-solid fa-circle-notch fa-spin"></i>
            </div>
            <input ref="fileInputRef" type="file" class="hidden" @change="onFileChange" :disabled="store.state.isUploading" accept=".pdf,.txt,.md" />
          </div>

          <!-- Knowledge Base Import -->
          <div 
            @click="openKbSelector"
            class="flex-1 group flex items-center justify-center h-12 border border-dashed border-indigo-300/50 rounded-lg cursor-pointer hover:border-indigo-500 hover:bg-white/50 transition-all"
          >
            <div class="flex flex-col items-center text-slate-400 group-hover:text-indigo-600">
               <i class="fa-solid fa-database text-sm mb-1"></i>
               <span class="text-[10px] font-bold uppercase tracking-tighter">KB</span>
            </div>
          </div>
        </div>

        <ul class="space-y-2">
          <template v-for="doc in store.getActiveSession().docs" :key="doc.id">
            <li class="group relative flex items-center justify-between p-2 rounded-lg border border-transparent hover:bg-white dark:hover:bg-slate-800 hover:shadow-sm hover:border-slate-100 dark:hover:border-slate-700 transition-all cursor-default"
            >
              <div class="flex items-center overflow-hidden flex-1 min-w-0 mr-2">
                <div class="w-6 h-6 rounded flex items-center justify-center mr-2 shrink-0 bg-slate-50 text-slate-400">
                  <i :class="getFileIcon(doc.type)" class="text-xs"></i>
                </div>
                <div class="flex flex-col min-w-0 flex-1">
                  <span class="text-xs text-slate-600 dark:text-slate-300 truncate font-medium" :title="doc.name">{{ doc.name }}</span>
                  
                  <!-- Tag Display -->
                  <div class="flex flex-wrap gap-1 mt-0.5" v-if="store.state.kbDocs[doc.name]">
                    <!-- Show top 3 tags -->
                    <span 
                      v-for="tag in store.state.kbDocs[doc.name].tags.slice(0, 3)" 
                      :key="tag"
                      :class="getTagStyle(tag)"
                      class="px-1 py-0.5 text-[8px] rounded leading-none"
                    >
                      {{ tag }}
                    </span>
                    <!-- Semantic tags (different color) -->
                    <span 
                      v-for="tag in store.state.kbDocs[doc.name].semantic_tags.slice(0, 1)" 
                      :key="tag"
                      :class="getTagStyle(tag, true)"
                      class="px-1 py-0.5 text-[8px] rounded leading-none italic font-medium"
                    >
                      {{ tag }}
                    </span>
                    <!-- More collapsed -->
                    <span 
                      v-if="store.state.kbDocs[doc.name].tags.length > 3"
                      class="px-1 py-0.5 bg-slate-50 dark:bg-slate-800 text-[8px] text-slate-400 rounded leading-none"
                    >
                      +{{ store.state.kbDocs[doc.name].tags.length - 3 }}
                    </span>
                  </div>
                </div>
              </div>
              
              <!-- Document Operations -->
              <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-all text-xs">
                 <button @click.stop="startTagEditing(doc)" class="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20" title="Manage Tags">
                    <i class="fa-solid fa-tags text-[10px]"></i>
                 </button>
                 <button @click.stop="openDocStats(doc)" class="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20" title="Statistics">
                    <i class="fa-solid fa-chart-pie text-[10px]"></i>
                 </button>
                 <button @click.stop="store.openPdf(doc.id, 1)" class="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20" title="Preview">
                    <i class="fa-regular fa-eye text-[10px]"></i>
                 </button>
                 <button @click.stop="store.setViewingDoc(doc)" class="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20" title="Graph">
                    <i class="fa-solid fa-sitemap text-[10px]"></i>
                 </button>
              </div>

              <!-- Remove Button (Top Right Badge) -->
              <button 
                @click.stop="store.removeDocFromSession(doc.id)" 
                class="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-red-500 hover:text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all shadow-sm z-10 border border-white dark:border-slate-800"
                title="Remove from Session"
              >
                 <i class="fa-solid fa-xmark text-[8px]"></i>
              </button>
            </li>

            <!-- Single Document Statistics Panel -->
            <div v-if="showingDocStatsId === doc.id" class="mt-1 mb-2 p-2.5 bg-orange-50/50 dark:bg-orange-900/10 rounded-lg border border-orange-100 dark:border-orange-900/30 animate-in zoom-in-95 duration-200">
               <div v-if="store.state.docStats" class="space-y-2">
                  <div class="flex justify-between items-center border-b border-orange-100 dark:border-orange-900/30 pb-1 mb-1">
                     <span class="text-[9px] font-bold text-orange-700 dark:text-orange-400">DOC INSIGHTS</span>
                     <button @click="showingDocStatsId = null" class="text-orange-400 hover:text-orange-600">
                        <i class="fa-solid fa-xmark text-[9px]"></i>
                     </button>
                  </div>
                  <div class="grid grid-cols-3 gap-2 text-[9px]">
                     <div class="flex flex-col">
                        <span class="text-slate-400">Pages</span>
                        <span class="font-bold text-slate-700 dark:text-slate-200">{{ store.state.docStats.pages }}</span>
                     </div>
                     <div class="flex flex-col">
                        <span class="text-slate-400">Nodes</span>
                        <span class="font-bold text-slate-700 dark:text-slate-200">{{ store.state.docStats.nodes }}</span>
                     </div>
                     <div class="flex flex-col">
                        <span class="text-slate-400">Depth</span>
                        <span class="font-bold text-slate-700 dark:text-slate-200">{{ store.state.docStats.depth }}</span>
                     </div>
                  </div>
                  <div class="flex flex-wrap gap-1 mt-1">
                     <span v-for="(v, k) in store.state.docStats.counts" :key="k" class="bg-white/80 dark:bg-slate-800/80 px-1 py-0.5 rounded text-[8px] text-slate-500 border border-orange-50 dark:border-orange-900/20">
                        {{ k }}: {{ v }}
                     </span>
                  </div>
               </div>
               <div v-else class="text-[9px] text-orange-400 animate-pulse py-1">Fetching metrics...</div>
            </div>
          </template>
          
          <li v-if="store.getActiveSession().docs.length === 0" class="text-center py-4 text-xs text-slate-400 italic">
             No documents yet.
          </li>
        </ul>
      </div>
    </div>

    <!-- Knowledge Base Selection Modal -->
    <Teleport to="body">
      <div v-if="showingKbSelector" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md transition-all duration-300">
        <div class="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl w-full max-w-4xl overflow-hidden border border-slate-200 dark:border-slate-700 animate-in fade-in zoom-in-95 duration-300 flex flex-col max-h-[90vh]">
          <div class="px-8 py-5 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/50">
            <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center">
              <div class="w-10 h-10 rounded-2xl bg-indigo-500/10 flex items-center justify-center mr-3">
                <i class="fa-solid fa-database text-indigo-500"></i>
              </div>
              Knowledge Base
            </h3>
            <button @click="showingKbSelector = false" class="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <div class="p-6 bg-slate-50/30 dark:bg-slate-900/20 border-b border-slate-100 dark:border-slate-700">
            <div class="relative">
              <i class="fa-solid fa-magnifying-glass absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm"></i>
              <input 
                v-model="kbSearchQuery"
                placeholder="Search by filename or tags..."
                class="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all shadow-sm"
              />
            </div>
          </div>
          
          <div class="flex-1 overflow-y-auto p-6 custom-scrollbar">
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div 
                v-for="(info, name) in filteredKbDocs" 
                :key="name"
                @click="toggleKbDocSelection(name)"
                class="p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between group relative"
                :class="selectedKbDocs.includes(name) 
                  ? 'bg-indigo-50/50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800 ring-2 ring-indigo-500/20' 
                  : 'bg-white dark:bg-slate-800 border-slate-100 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-md'"
              >
                <div class="flex items-center min-w-0 mr-4">
                  <div class="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center mr-3 shrink-0 text-slate-400 group-hover:text-indigo-500 transition-colors">
                    <i class="fa-solid fa-file-pdf text-lg"></i>
                  </div>
                  <div class="flex flex-col min-w-0">
                    <span class="text-sm font-bold text-slate-700 dark:text-slate-200 truncate">{{ name }}</span>
                    <div class="flex flex-wrap gap-1 mt-1.5">
                      <span v-for="tag in info.tags" :key="tag" :class="getTagStyle(tag)" class="text-[9px] px-1.5 py-0.5 rounded-md">
                        {{ tag }}
                      </span>
                      <span v-for="tag in info.semantic_tags" :key="tag" :class="getTagStyle(tag, true)" class="text-[9px] px-1.5 py-0.5 rounded-md italic">
                        {{ tag }}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="shrink-0">
                  <div v-if="selectedKbDocs.includes(name)" class="w-6 h-6 rounded-full bg-indigo-500 text-white flex items-center justify-center shadow-lg shadow-indigo-500/30 scale-110 transition-transform">
                    <i class="fa-solid fa-check text-xs"></i>
                  </div>
                  <div v-else class="w-6 h-6 rounded-full border-2 border-slate-200 dark:border-slate-700 group-hover:border-indigo-300 transition-colors"></div>
                </div>
              </div>
            </div>
            <div v-if="Object.keys(filteredKbDocs).length === 0" class="py-20 text-center text-slate-400">
              <div class="w-20 h-20 bg-slate-50 dark:bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                <i class="fa-solid fa-box-open text-4xl opacity-20"></i>
              </div>
              <p class="text-sm font-medium">No matching documents found</p>
              <p class="text-xs opacity-60 mt-1">Try a different search term</p>
            </div>
          </div>

          <div class="px-8 py-5 bg-slate-50/50 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-700 flex justify-between items-center">
            <div class="flex flex-col">
              <span class="text-xs font-bold text-slate-800 dark:text-slate-200">{{ selectedKbDocs.length }} Selected</span>
              <span class="text-[10px] text-slate-400">Documents will be added to current session</span>
            </div>
            <div class="flex items-center space-x-3">
              <button @click="showingKbSelector = false" class="px-5 py-2.5 text-sm font-bold text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
                Cancel
              </button>
              <button 
                @click="addSelectedFromKb"
                :disabled="selectedKbDocs.length === 0"
                class="px-8 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:grayscale disabled:cursor-not-allowed text-white rounded-2xl text-sm font-bold shadow-xl shadow-indigo-500/25 transition-all hover:-translate-y-0.5 active:translate-y-0"
              >
                Add to Session
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 标签编辑弹窗 -->
    <Teleport to="body">
      <div v-if="editingTagsDocId" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md transition-all duration-300">
        <div class="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl w-full max-w-2xl overflow-hidden border border-slate-200 dark:border-slate-700 animate-in fade-in zoom-in-95 duration-300">
          <div class="px-8 py-5 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/50">
            <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center">
              <div class="w-10 h-10 rounded-2xl bg-indigo-500/10 flex items-center justify-center mr-3">
                <i class="fa-solid fa-tags text-indigo-500"></i>
              </div>
              Manage Tags
            </h3>
            <button @click="editingTagsDocId = null" class="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          
          <div class="p-8 space-y-6">
            <!-- 文档信息展示 -->
            <div class="flex items-center p-4 bg-slate-50 dark:bg-slate-900/40 rounded-2xl border border-slate-100 dark:border-slate-800/50">
              <div class="w-12 h-12 rounded-2xl bg-white dark:bg-slate-800 flex items-center justify-center mr-4 shadow-sm text-indigo-500 text-xl">
                <i class="fa-solid fa-file-pdf"></i>
              </div>
              <div class="flex flex-col min-w-0">
                <span class="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-0.5">Editing tags for</span>
                <span class="text-base font-bold text-slate-700 dark:text-slate-200 truncate">{{ editingTagsDocName }}</span>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
              <!-- 左侧：添加与活跃标签 -->
              <div class="space-y-6">
                <!-- 添加标签 -->
                <div>
                  <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest mb-3 block">Create New Tag</label>
                  <div class="relative group">
                    <input 
                      v-model="newTagInput"
                      @keyup.enter="addTag"
                      placeholder="Type and press enter..."
                      class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl px-5 py-3.5 text-sm focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all shadow-sm group-hover:border-slate-300 dark:group-hover:border-slate-600"
                    />
                    <div class="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
                      <kbd class="text-[10px] text-slate-400 bg-white dark:bg-slate-800 px-2 py-1 rounded-md border border-slate-200 dark:border-slate-700 shadow-sm font-bold">ENTER</kbd>
                    </div>
                  </div>
                </div>

                <!-- 当前标签列表 -->
                <div>
                  <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest mb-3 block">Active Tags</label>
                  <div class="flex flex-wrap gap-2 min-h-[120px] p-4 bg-slate-50/30 dark:bg-slate-900/10 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800/50 overflow-y-auto max-h-[200px] custom-scrollbar">
                    <span 
                      v-for="tag in currentTags" 
                      :key="tag"
                      :class="getTagStyle(tag)"
                      class="flex items-center px-3 py-1.5 rounded-xl text-xs font-bold shadow-sm group/active"
                    >
                      {{ tag }}
                      <button @click="removeTag(tag)" class="ml-2 w-4 h-4 rounded-full flex items-center justify-center hover:bg-black/5 dark:hover:bg-white/10 transition-colors">
                        <i class="fa-solid fa-xmark text-[10px]"></i>
                      </button>
                    </span>
                    <div v-if="currentTags.length === 0" class="flex flex-col items-center justify-center text-xs text-slate-400 italic w-full h-full py-4 opacity-60">
                      <i class="fa-solid fa-tag text-2xl mb-2"></i>
                      No tags assigned
                    </div>
                  </div>
                </div>
              </div>

              <!-- 右侧：全局库建议 -->
              <div class="flex flex-col h-full">
                <label class="text-[11px] font-extrabold text-slate-400 uppercase tracking-widest mb-3 block flex items-center">
                  <i class="fa-solid fa-lightbulb text-amber-400 mr-2"></i>
                  Global Library
                </label>
                <div class="flex-1 bg-slate-50/50 dark:bg-slate-900/30 rounded-2xl p-4 border border-slate-100 dark:border-slate-800/50 overflow-y-auto max-h-[350px] custom-scrollbar pr-2">
                  <div class="flex flex-wrap gap-2">
                    <span 
                      v-for="tag in store.state.globalTags" 
                      :key="tag"
                      :class="getTagStyle(tag)"
                      class="group/tag inline-flex items-center text-[11px] px-3 py-1.5 rounded-xl transition-all cursor-pointer hover:scale-105 active:scale-95 shadow-sm"
                      @click="addExistingTag(tag)"
                    >
                      {{ tag }}
                      <button 
                        @click.stop="store.deleteGlobalTag(tag)" 
                        class="ml-2 w-4 h-4 rounded-full flex items-center justify-center hover:bg-black/5 dark:hover:bg-white/10 opacity-0 group-hover/tag:opacity-100 transition-all"
                        title="Remove from library"
                      >
                        <i class="fa-solid fa-xmark text-[9px]"></i>
                      </button>
                    </span>
                  </div>
                  <div v-if="store.state.globalTags.length === 0" class="flex flex-col items-center justify-center text-xs text-slate-400 italic py-10 opacity-60">
                    <i class="fa-solid fa-layer-group text-2xl mb-2"></i>
                    Library is empty
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="px-8 py-6 bg-slate-50/50 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-700 flex justify-end space-x-3">
            <button @click="editingTagsDocId = null" class="px-6 py-2.5 text-sm font-bold text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
              Cancel
            </button>
            <button 
              @click="saveTags"
              class="px-8 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl text-sm font-bold shadow-xl shadow-indigo-500/25 transition-all hover:-translate-y-0.5 active:translate-y-0"
            >
              Apply Changes
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>

<script setup>
import { useModoraStore } from '../composables/useModoraStore';
import { useDarkTheme } from '../composables/useDarkTheme';
import { ref, nextTick, computed, onMounted } from 'vue';

const store = useModoraStore();

// 初始化拉取知识库数据
onMounted(() => {
  store.fetchKbDocs();
  store.fetchGlobalTags();
});

const { isDark, toggleTheme } = useDarkTheme();
const fileInputRef = ref(null);
const editInputRef = ref(null);

const editingSessionId = ref(null);
const editingName = ref('');

// 统计相关状态
const showingSessionStats = ref(false);
const showingDocStatsId = ref(null);

// 标签编辑相关状态
const editingTagsDocId = ref(null);
const editingTagsDocName = ref('');
const currentTags = ref([]);
const newTagInput = ref('');

// 知识库选择相关状态
const showingKbSelector = ref(false);
const kbSearchQuery = ref('');
const selectedKbDocs = ref([]);

const filteredKbDocs = computed(() => {
  const query = kbSearchQuery.value.toLowerCase();
  if (!query) return store.state.kbDocs;
  
  const result = {};
  for (const [name, info] of Object.entries(store.state.kbDocs)) {
    const nameMatch = name.toLowerCase().includes(query);
    const tagMatch = (info.tags || []).some(t => t.toLowerCase().includes(query));
    const semanticTagMatch = (info.semantic_tags || []).some(t => t.toLowerCase().includes(query));
    if (nameMatch || tagMatch || semanticTagMatch) {
      result[name] = info;
    }
  }
  return result;
});

const openKbSelector = () => {
  showingKbSelector.value = true;
  selectedKbDocs.value = [];
  store.fetchKbDocs();
};

const toggleKbDocSelection = (name) => {
  if (selectedKbDocs.value.includes(name)) {
    selectedKbDocs.value = selectedKbDocs.value.filter(n => n !== name);
  } else {
    selectedKbDocs.value.push(name);
  }
};

const addSelectedFromKb = () => {
  selectedKbDocs.value.forEach(name => {
    store.addDocFromKb(name);
  });
  showingKbSelector.value = false;
  selectedKbDocs.value = [];
};


const startTagEditing = (doc) => {
  editingTagsDocId.value = doc.id;
  editingTagsDocName.value = doc.name;
  // 从 store 中获取当前标签 (合并规则标签和语义标签)
  const kbInfo = store.state.kbDocs[doc.name];
  if (kbInfo) {
    const tags = kbInfo.tags || [];
    const semanticTags = kbInfo.semantic_tags || [];
    currentTags.value = [...new Set([...tags, ...semanticTags])];
  } else {
    currentTags.value = [];
  }
  newTagInput.value = '';
};

const addTag = () => {
  const tag = newTagInput.value.trim();
  if (tag && !currentTags.value.includes(tag)) {
    currentTags.value.push(tag);
    newTagInput.value = '';
  }
};

const addExistingTag = (tag) => {
  if (!currentTags.value.includes(tag)) {
    currentTags.value.push(tag);
    newTagInput.value = '';
  }
};

const removeTag = (tag) => {
  currentTags.value = currentTags.value.filter(t => t !== tag);
};

const saveTags = async () => {
  await store.updateDocTags(editingTagsDocName.value, currentTags.value);
  editingTagsDocId.value = null;
  // 重新获取知识库数据以同步
  store.fetchKbDocs();
  store.fetchGlobalTags();
};

const openSessionStats = () => {
  showingSessionStats.value = !showingSessionStats.value;
  if (showingSessionStats.value) {
    store.fetchSessionStats();
  }
};

const openDocStats = (doc) => {
  if (showingDocStatsId.value === doc.id) {
    showingDocStatsId.value = null;
  } else {
    showingDocStatsId.value = doc.id;
    store.fetchDocStats(doc.name);
  }
};

const startEditing = (sess) => {
  editingSessionId.value = sess.id;
  editingName.value = sess.name;
  
  nextTick(() => {
    // 如果有多个输入框（虽然v-if保证同时只有一个），确保聚焦
    if (editInputRef.value && editInputRef.value[0]) {
       editInputRef.value[0].focus();
    } else if (editInputRef.value) {
       editInputRef.value.focus();
    }
  });
};

const saveEditing = (sessId) => {
  if (editingSessionId.value === sessId) {
    const newName = editingName.value.trim();
    if (newName) {
       store.renameSession(sessId, newName);
    }
    editingSessionId.value = null;
    editingName.value = '';
  }
};

// 触发文件选择
const triggerUpload = () => {
  if (store.state.isUploading) return;
  fileInputRef.value?.click();
};

// 简单的文件图标映射
const getFileIcon = (type) => {
  if (!type) return 'fa-regular fa-file';
  if (type.includes('pdf')) return 'fa-regular fa-file-pdf';
  if (type.includes('word') || type.includes('doc')) return 'fa-regular fa-file-word';
  if (type.includes('text') || type.includes('md')) return 'fa-regular fa-file-lines';
  return 'fa-regular fa-file';
};

const onFileChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  await store.uploadFile(file);
};

// 获取标签样式
const getTagStyle = (tag, isSemantic = false) => {
  const hash = tag.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  
  // 预定义颜色系列
  const colors = [
    'bg-blue-50 text-blue-500 border-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800/30',
    'bg-emerald-50 text-emerald-500 border-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800/30',
    'bg-amber-50 text-amber-500 border-amber-100 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800/30',
    'bg-rose-50 text-rose-500 border-rose-100 dark:bg-rose-900/20 dark:text-rose-400 dark:border-rose-800/30',
    'bg-indigo-50 text-indigo-500 border-indigo-100 dark:bg-indigo-900/20 dark:text-indigo-400 dark:border-indigo-800/30',
    'bg-purple-50 text-purple-500 border-purple-100 dark:bg-purple-900/20 dark:text-purple-400 dark:border-purple-800/30',
    'bg-cyan-50 text-cyan-500 border-cyan-100 dark:bg-cyan-900/20 dark:text-cyan-400 dark:border-cyan-800/30',
    'bg-teal-50 text-teal-500 border-teal-100 dark:bg-teal-900/20 dark:text-teal-400 dark:border-teal-800/30',
  ];

  // 规则标签映射
  const ruleMap = {
    'Long': colors[3],      // Rose
    'Medium': colors[2],    // Amber
    'Short': colors[1],     // Emerald
    'Table-Rich': colors[4], // Indigo
    'Chart-Rich': colors[5], // Purple
    'Image-Rich': colors[0], // Blue
    'Complex Layout': colors[6], // Cyan
    'Deep Hierarchy': colors[7]  // Teal
  };

  if (ruleMap[tag]) return ruleMap[tag] + ' border';
  
  // 语义标签使用 hash 选择颜色
  const colorIndex = hash % colors.length;
  return colors[colorIndex] + (isSemantic ? ' border border-dashed' : ' border');
};
</script>
