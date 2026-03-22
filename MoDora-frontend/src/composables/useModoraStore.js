import { reactive } from 'vue';
import { apiFetch, createApiXhr, getApiUrl } from '../config/api';
import { DEFAULT_SETTINGS, normalizeSettings } from '../config/settingsContract';

// 辅助：生成 ID
const generateId = () => 'sess_' + Math.random().toString(36).substr(2, 9);

// 辅助：创建初始欢迎消息
const createWelcomeMessage = () => [
    {
        role: "assistant",
        content: "Hello! Please upload a document, and I will analyze it and answer your questions.",
        isTyping: false
    }
];

// 辅助：创建默认文档列表
const createDefaultDocs = () => [];

// 初始默认会话
const DEFAULT_SESSION = {
    id: generateId(),
    name: "New Chat",
    docs: createDefaultDocs(),
    messages: createWelcomeMessage(),
    createdAt: new Date()
};

// 核心状态
const state = reactive({
    sessions: [DEFAULT_SESSION], // 会话列表
    activeSessionId: DEFAULT_SESSION.id, // 当前激活的会话 ID
    currentUser: null,
    isAuthLoading: true,
    authError: '',
    documentLibrary: [],
    
    // 界面状态
    isThinking: false,
    isUploading: false,
    uploadProgress: 0,
    
    // 侧边栏/预览状态
    viewingDocTree: null, // 当前查看树的文档对象 {name, id}
    viewingPdf: null,     // 当前查看的PDF对象
    inputMessage: '',
    
    // 统计状态
    docStats: null,
    sessionStats: null,
    
    // 知识库与标签状态
    kbDocs: {},      // { filename: { tags, semantic_tags, added_at } }
    globalTags: [],  // 所有已存在的标签
    
    // 全局设置
    settings: normalizeSettings(JSON.parse(localStorage.getItem('modora_settings')) || DEFAULT_SETTINGS),
    modelInstances: []
});

const uploadViaDirectApi = (formData, onProgress) => new Promise((resolve, reject) => {
    const xhr = createApiXhr();
    xhr.open('POST', getApiUrl('/api/upload'));
    xhr.responseType = 'json';

    xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable || typeof onProgress !== 'function') return;
        onProgress(event.loaded / event.total);
    };

    xhr.onerror = () => {
        reject(new Error('Upload request failed'));
    };

    xhr.ontimeout = () => {
        reject(new Error('Upload timed out'));
    };

    xhr.onload = () => {
        const response = xhr.response ?? {};
        if (xhr.status >= 200 && xhr.status < 300) {
            resolve(response);
            return;
        }

        const detail =
            response?.detail ||
            (typeof xhr.responseText === 'string' && xhr.responseText) ||
            `Upload failed with status ${xhr.status}`;
        reject(new Error(detail));
    };

    xhr.timeout = 30 * 60 * 1000;
    xhr.send(formData);
});

export function useModoraStore() {
    const createSessionShell = (overrides = {}) => ({
        id: generateId(),
        name: "New Chat",
        docs: createDefaultDocs(),
        messages: createWelcomeMessage(),
        createdAt: new Date(),
        ...overrides
    });

    const resetSessionState = () => {
        const fallbackSession = createSessionShell();
        state.sessions = [fallbackSession];
        state.activeSessionId = fallbackSession.id;
        state.viewingDocTree = null;
        state.viewingPdf = null;
        state.docStats = null;
        state.sessionStats = null;
    };

    const getKbKeyForDoc = (doc) => doc?.storageKey || doc?.kbKey || doc?.name || '';

    const getKbInfoForDoc = (doc) => {
        const key = getKbKeyForDoc(doc);
        if (!key) return null;
        return state.kbDocs[key] || state.kbDocs[doc?.name] || null;
    };

    const setDocumentLibrary = (documents) => {
        state.documentLibrary = documents.map((doc) => ({
            id: doc.id,
            name: doc.original_name,
            documentId: doc.id,
            storageKey: doc.storage_key || doc.original_name,
            kbKey: doc.storage_key || doc.original_name,
            type: (doc.original_name.split('.').pop() || '').toLowerCase(),
            status: doc.status,
            createdAt: doc.created_at
        }));
    };

    const getDocByReference = (reference) => {
        const session = getActiveSession();
        const sessionDocs = session ? session.docs : [];
        const allDocs = [...sessionDocs, ...state.documentLibrary];
        return allDocs.find(d => d.id === reference)
            || allDocs.find(d => d.documentId === reference)
            || allDocs.find(d => d.storageKey === reference)
            || allDocs.find(d => d.name === reference)
            || null;
    };

    const serializeSessionMessage = (message) => ({
        role: message.role,
        content: message.content || '',
        citations: Array.isArray(message.citations) ? message.citations : []
    });

    const serializeSession = (session) => ({
        title: session.name || 'New Chat',
        document_ids: session.docs.map(doc => doc.documentId).filter(Boolean),
        messages: session.messages.map(serializeSessionMessage)
    });

    const buildSessionFromConversation = (conversation) => ({
        id: conversation.id,
        name: conversation.title,
        docs: (conversation.documents || []).map((doc) => ({
            id: doc.id,
            name: doc.original_name,
            documentId: doc.id,
            storageKey: doc.storage_key || doc.original_name,
            kbKey: doc.storage_key || doc.original_name,
            type: (doc.original_name.split('.').pop() || '').toLowerCase(),
            status: doc.status,
            createdAt: doc.created_at
        })),
        messages: (conversation.messages || []).length > 0
            ? conversation.messages.map((message) => ({
                role: message.role,
                content: message.content,
                citations: message.citations || [],
                isTyping: false
            }))
            : createWelcomeMessage(),
        createdAt: conversation.created_at ? new Date(conversation.created_at) : new Date()
    });

    const loadConversations = async () => {
        if (!state.currentUser) {
            resetSessionState();
            return;
        }
        try {
            const res = await apiFetch('/api/conversations');
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            if (Array.isArray(data.conversations) && data.conversations.length > 0) {
                state.sessions = data.conversations.map(buildSessionFromConversation);
                state.activeSessionId = state.sessions[0].id;
            } else {
                state.sessions = [];
                const created = await createNewSession();
                state.activeSessionId = created.id;
            }
        } catch (e) {
            console.error("Failed to load conversations:", e);
            resetSessionState();
        }
    };

    const persistSession = async (session) => {
        if (!state.currentUser || !session?.id) return;
        try {
            await apiFetch(`/api/conversations/${encodeURIComponent(session.id)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(serializeSession(session))
            });
        } catch (e) {
            console.error("Failed to persist conversation:", e);
        }
    };

    // 获取当前会话对象
    const getActiveSession = () => {
        return state.sessions.find(s => s.id === state.activeSessionId) || state.sessions[0];
    };

    const syncCurrentSessionDocs = () => {
        const session = getActiveSession();
        if (!session) return;
        session.docs = session.docs.map((doc) => {
            const latest = getDocByReference(doc.documentId || doc.storageKey || doc.name);
            return latest ? { ...latest, id: doc.id || latest.id } : doc;
        });
    };

    // 动作：切换当前会话
    const setActiveSession = (sessionId) => {
        if (state.activeSessionId === sessionId) return;
        state.activeSessionId = sessionId;
        
        // 切换会话时，重置右侧面板（或者可以保留之前的状态？）
        // 简单起见，先关闭右侧面板，避免显示不属于当前会话的文档
        closeSidePanel();
    };

    // 动作：新建会话
    const createNewSession = async () => {
        if (!state.currentUser) {
            const localSession = createSessionShell();
            state.sessions.unshift(localSession);
            setActiveSession(localSession.id);
            return localSession;
        }
        const response = await apiFetch('/api/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New Chat' })
        });
        if (!response.ok) {
            throw new Error(`Failed to create conversation: HTTP ${response.status}`);
        }
        const payload = await response.json();
        const newSession = buildSessionFromConversation(payload);
        state.sessions.unshift(newSession);
        setActiveSession(newSession.id);
        return newSession;
    };

    // 动作：删除会话
    const deleteSession = async (sessionId) => {
        const index = state.sessions.findIndex(s => s.id === sessionId);
        if (index === -1) return;

        if (state.currentUser) {
            try {
                await apiFetch(`/api/conversations/${encodeURIComponent(sessionId)}`, {
                    method: 'DELETE'
                });
            } catch (e) {
                console.error("Failed to delete conversation:", e);
            }
        }

        state.sessions.splice(index, 1);
        
        // 如果删除了当前会话，需要激活另一个
        if (state.activeSessionId === sessionId) {
            if (state.sessions.length > 0) {
                state.activeSessionId = state.sessions[0].id;
            } else {
                // 如果删空了，自动创建一个新的
                await createNewSession();
            }
        }
    };

    // 动作：重命名会话
    const renameSession = async (sessionId, newName) => {
        const session = state.sessions.find(s => s.id === sessionId);
        if (session) {
            session.name = newName;
            await persistSession(session);
        }
    };

    // 打开 PDF 动作
    const openPdf = (fileId, page = 1, bboxes = []) => {
        const session = getActiveSession();
        let doc = getDocByReference(fileId);

        // 依然找不到？可能是跨会话引用（理论上不该发生），或者默认 fallback
        if (!doc && session.docs.length > 0) doc = session.docs[0];
        
        if (!doc) return; // 真的没有文档

        const fileUrl = doc.documentId
            ? getApiUrl(`/api/documents/${encodeURIComponent(doc.documentId)}/file`)
            : getApiUrl(`/api/files/${encodeURIComponent(doc.name)}`);

        state.viewingPdf = {
            url: fileUrl,
            page: page,
            name: doc.name,
            bboxes: bboxes || [],
            documentId: doc.documentId || null
        };

        // 互斥：关闭结构树
        state.viewingDocTree = null;
    };

    // 动作：打开结构树
    const setViewingDoc = (doc) => {
        state.viewingDocTree = doc;
        // 互斥：关闭 PDF
        state.viewingPdf = null;
    };

    const closeSidePanel = () => {
        state.viewingPdf = null;
        state.viewingDocTree = null;
    };

    const closePdf = closeSidePanel;

    // 动作：发送消息
    const sendMessage = async () => {
        const text = state.inputMessage.trim();
        if (!text) return;

        const session = getActiveSession();
        
        session.messages.push({ role: "user", content: text });
        const currentQuery = text;
        state.inputMessage = '';
        state.isThinking = true;

        // --- 获取当前会话的所有文档 ---
        const fileNames = session.docs.map(d => d.name);
        const documentIds = session.docs.map(d => d.documentId).filter(Boolean);
        
        // 如果没有文档，提示用户上传
        if (fileNames.length === 0) {
            state.isThinking = false;
            session.messages.push({
                role: "assistant",
                content: "Please upload at least one document so I can answer your questions.",
                isTyping: false
            });
            await persistSession(session);
            return;
        }

        // 默认激活的文件名（用于 fallback）
        const activeFile = fileNames[0];

        let answer = "";
        let citations = [];

        try {
            // 发起真实 API 请求
            const payload = { 
                file_names: fileNames,
                file_name: fileNames[0],
                document_ids: documentIds.length > 0 ? documentIds : undefined,
                document_id: documentIds[0] || undefined,
                query: currentQuery,
                settings: state.settings
            };
            console.log("Chat request payload:", payload);
            const response = await apiFetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                let errorMessage = `HTTP Error ${response.status}`;
                try {
                    const errData = await response.json();
                    if (errData.detail) errorMessage += `: ${errData.detail}`;
                } catch (error) {
                    console.error("Error parsing error response:", error);
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            answer = data.answer || "No valid answer returned from backend.";

            const retrievedDocs = data.retrieved_documents || [];

            citations = retrievedDocs.map((doc) => {
                let snippetText = doc.content || "Citation Details...";
                if (snippetText.length > 60) snippetText = snippetText.substring(0, 60) + "...";
                const citationPage = Number(doc.page) >= 1 ? Number(doc.page) : 1;
                
                // 尝试根据 file_name 找到对应的 fileId (用于 openPdf)
                let docId = null;
                let documentId = doc.document_id || null;
                if (documentId) {
                    const foundDoc = session.docs.find(d => d.documentId === documentId);
                    if (foundDoc) docId = foundDoc.id;
                }
                if (doc.file_name) {
                    const foundDoc = session.docs.find(d => d.name === doc.file_name);
                    if (foundDoc) docId = foundDoc.id;
                }
                // Fallback
                if (!docId && session.docs.length > 0) docId = session.docs[0].id;

                return {
                    fileId: documentId || docId || doc.file_name || activeFile,
                    fileName: doc.file_name || activeFile,
                    documentId: documentId,
                    page: citationPage,
                    snippet: snippetText,
                    bboxes: Array.isArray(doc.bboxes)
                        ? doc.bboxes.map((bbox) => Array.isArray(bbox) ? { page: citationPage, range: bbox } : bbox)
                        : []
                };
            });

        } catch (error) {
            console.error("API Request Failed:", error);
            answer = `❌ Request Failed: ${error.message}`;
            if (error.message.includes("404")) {
                answer += "\n\n💡 Tip: Please check backend dataset path and file integrity.";
            }
            citations = [];
        } finally {
            state.isThinking = false;

            const newMsg = {
                role: "assistant",
                content: "",
                isTyping: true,
                citations: citations
            };

            session.messages.push(newMsg);

            const activeMsg = session.messages[session.messages.length - 1];

            let i = 0;
            const timer = setInterval(() => {
                activeMsg.content += answer.charAt(i);
                i++;
                if (i >= answer.length) {
                    clearInterval(timer);
                    activeMsg.isTyping = false;
                    persistSession(session);
                }
            }, 30);
        }
    };
    
    // 更新树节点
    const updateTreeNode = async (fileRef, nodePath, action, newData) => {
        const doc = getDocByReference(fileRef);
        try {
            const response = await apiFetch('/api/tree/node/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_name: doc ? doc.name : fileRef,
                    document_id: doc?.documentId,
                    action: action,
                    target_path: nodePath,
                    new_data: newData
                })
            });
            if (!response.ok) throw new Error("Update failed");
            return await response.json();
        } catch (e) {
            console.error("Update node error:", e);
            throw e;
        }
    };
    
    // 保存整个树结构
    const saveTreeStructure = async (fileRef, elements) => {
        const doc = getDocByReference(fileRef);
        try {
             const response = await apiFetch('/api/tree/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_name: doc ? doc.name : fileRef,
                    document_id: doc?.documentId,
                    elements: elements
                })
            });
            if (!response.ok) throw new Error("Save failed");
            return await response.json();
        } catch (e) {
             console.error("Save tree error:", e);
             throw e;
        }
    };

    // 动作：更新设置
    const updateSettings = async (newSettings) => {
        state.settings = normalizeSettings({ ...state.settings, ...newSettings });
        localStorage.setItem('modora_settings', JSON.stringify(state.settings));
        if (!state.currentUser) {
            return;
        }
        try {
            const res = await apiFetch('/api/settings/ui', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ settings: state.settings })
            });
            if (res.ok) {
                const data = await res.json();
                if (data && data.settings) {
                    state.settings = normalizeSettings(data.settings);
                    localStorage.setItem('modora_settings', JSON.stringify(state.settings));
                }
            }
        } catch (e) {
            console.error("Failed to save settings:", e);
        }
    };

    const loadSettings = async () => {
        if (!state.currentUser) {
            state.settings = normalizeSettings(JSON.parse(localStorage.getItem('modora_settings')) || DEFAULT_SETTINGS);
            return;
        }
        try {
            const res = await apiFetch('/api/settings/ui');
            if (res.ok) {
                const data = await res.json();
                if (data && data.settings) {
                    state.settings = normalizeSettings(data.settings);
                    localStorage.setItem('modora_settings', JSON.stringify(state.settings));
                }
            }
        } catch (e) {
            console.error("Failed to load settings:", e);
        }
    };

    const loadModelInstances = async () => {
        if (!state.currentUser) {
            state.modelInstances = [];
            return;
        }
        try {
            const res = await apiFetch('/api/models/instances');
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data.instances)) {
                    state.modelInstances = data.instances;
                } else {
                    state.modelInstances = [];
                }
            }
        } catch (e) {
            state.modelInstances = [];
            console.error("Failed to load model instances:", e);
        }
    };

    const createModelInstance = async ({ modelName, baseUrl, apiKey }) => {
        const res = await apiFetch('/api/models/instances', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model_name: modelName,
                base_url: baseUrl,
                api_key: apiKey || ''
            })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(data.detail || `HTTP ${res.status}`);
        }
        await loadModelInstances();
        return data.instance || null;
    };

    const deleteModelInstance = async (instanceId) => {
        const res = await apiFetch(`/api/models/instances/${encodeURIComponent(instanceId)}`, {
            method: 'DELETE'
        });
        if (res.status !== 204) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || `HTTP ${res.status}`);
        }
        await loadModelInstances();
    };

    const uploadFile = async (file) => {
        if (!file) return;
        state.isUploading = true;
        state.uploadProgress = 0;
        
        let progressTimer = null;
        let pollTimer = null;

        // 阶段 1: 模拟上传进度 (0-40%)
        progressTimer = setInterval(() => {
            if (state.uploadProgress < 40) {
                state.uploadProgress += 2;
            }
        }, 200);

        try {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("settings", JSON.stringify(state.settings));

            const data = await uploadViaDirectApi(formData, (ratio) => {
                const scaled = Math.min(40, Math.max(1, ratio * 40));
                state.uploadProgress = Math.max(state.uploadProgress, scaled);
            });

            clearInterval(progressTimer); 

            state.uploadProgress = 40;
            const filename = data.filename;
            const documentId = data.document_id || null;
            const jobId = data.job_id || null;
            const taskStatusKey = jobId || filename;

            // 阶段 2: 轮询后台状态 (40% -> 99%)
            progressTimer = setInterval(() => {
                if (state.uploadProgress < 95) {
                    const increment = state.uploadProgress > 80 ? 0.2 : 0.5;
                    state.uploadProgress = Math.min(state.uploadProgress + increment, 95);
                }
            }, 500);

            // 开始轮询
            await new Promise((resolve, reject) => {
                pollTimer = setInterval(async () => {
                    try {
                        const statusRes = await apiFetch(`/api/task/status/${encodeURIComponent(taskStatusKey)}`);
                        if (!statusRes.ok) return; 
                        
                        const statusData = await statusRes.json();
                        const status = statusData.status;

                        if (status === 'completed') {
                            clearInterval(pollTimer);
                            clearInterval(progressTimer);
                            state.uploadProgress = 100;
                            resolve();
                        } else if (status === 'failed') {
                            clearInterval(pollTimer);
                            clearInterval(progressTimer);
                            reject(new Error("Background processing failed"));
                        }
                    } catch (e) {
                        console.error("Polling error:", e);
                    }
                }, 2000); 
            });

            await new Promise(resolve => setTimeout(resolve, 500));
            
            // 上传成功后添加到当前会话
            const ext = filename.split('.').pop().toLowerCase();
            const newDoc = {
                id: documentId || ('doc_' + Math.random().toString(36).substr(2, 9)),
                name: filename,
                type: ext,
                documentId: documentId,
                jobId: jobId,
                storageKey: documentId ? `${documentId}_${filename}` : filename,
                kbKey: documentId ? `${documentId}_${filename}` : filename,
                status: 'completed'
            };
            
            const session = getActiveSession();
            session.docs.push(newDoc);
            await loadUserDocuments();
            
            // 刷新知识库数据
            await fetchKbDocs();
            await fetchGlobalTags();
            
            // 如果是第一个文档，自动改会话名（可选）
            if (session.name === "New Chat") {
                session.name = filename;
            }
            await persistSession(session);
            
        } catch (e) {
            console.error("Upload Error:", e);
            alert("上传失败: " + e.message);
        } finally {
            state.isUploading = false;
            state.uploadProgress = 0;
            if (progressTimer) clearInterval(progressTimer);
            if (pollTimer) clearInterval(pollTimer);
        }
    };

    // 动作：获取知识库所有文档
    const fetchKbDocs = async () => {
        if (!state.currentUser) {
            state.kbDocs = {};
            return;
        }
        try {
            const res = await apiFetch('/api/kb/docs');
            if (res.ok) {
                state.kbDocs = await res.json();
            }
        } catch (e) {
            console.error("Failed to fetch KB docs:", e);
        }
    };

    // 动作：获取全局标签库
    const fetchGlobalTags = async () => {
        if (!state.currentUser) {
            state.globalTags = [];
            return;
        }
        try {
            const res = await apiFetch('/api/kb/tags');
            if (res.ok) {
                state.globalTags = await res.json();
            }
        } catch (e) {
            console.error("Failed to fetch global tags:", e);
        }
    };

    // 动作：更新文档标签
    const updateDocTags = async (fileRef, tags) => {
        const doc = getDocByReference(fileRef);
        const kbKey = doc?.documentId || doc?.name || fileRef;
        try {
            const res = await apiFetch('/api/kb/doc/tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_name: doc?.name || fileRef,
                    document_id: doc?.documentId,
                    tags
                })
            });
            if (res.ok) {
                // 更新本地缓存
                if (state.kbDocs[kbKey]) {
                    state.kbDocs[kbKey].tags = tags;
                }
                // 重新获取全局标签库，因为可能新增了标签
                await fetchGlobalTags();
                
                // 如果当前正在看这个文档的统计，也更新一下
                if (state.docStats && (state.docStats.document_id === doc?.documentId || state.docStats.file_name === doc?.name || state.docStats.file_name === fileRef)) {
                    state.docStats.tags = tags;
                }
            }
        } catch (e) {
            console.error("Failed to update doc tags:", e);
        }
    };

    // 动作：从知识库添加文档到当前会话
    const addDocFromKb = async (fileName) => {
        const doc = getDocByReference(fileName);
        const session = getActiveSession();
        const candidate = doc || state.documentLibrary.find(d => d.storageKey === fileName) || state.documentLibrary.find(d => d.name === fileName);
        if (!candidate) {
            return;
        }
        if (session.docs.find(d => d.documentId === candidate.documentId || d.storageKey === candidate.storageKey || d.name === candidate.name)) {
            return;
        }
        const newDoc = {
            ...candidate,
            id: candidate.id || ('doc_' + Math.random().toString(36).substr(2, 9))
        };
        session.docs.push(newDoc);
        
        if (session.name === "New Chat") {
            session.name = candidate.name;
        }
        await persistSession(session);
    };

    // 动作：从当前会话移除文档
    const removeDocFromSession = async (docId) => {
        const session = getActiveSession();
        const docIndex = session.docs.findIndex(d => d.id === docId);
        if (docIndex === -1) return;

        const doc = session.docs[docIndex];
        session.docs.splice(docIndex, 1);
        
        // 如果删除的是当前正在查看的文档，需要清除 viewingDocTree 等状态
        if (state.viewingDocTree && state.viewingDocTree.id === docId) {
            state.viewingDocTree = null;
        }
        // viewingPdf
        if (state.viewingPdf && state.viewingPdf.name === doc.name) {
             state.viewingPdf = null;
        }
        // docStats
        if (state.docStats && state.docStats.file_name === doc.name) {
             state.docStats = null;
        }
        await persistSession(session);
    };

    // 动作：从全局库中删除标签
    const deleteGlobalTag = async (tag) => {
        try {
            const res = await apiFetch(`/api/kb/tag/${encodeURIComponent(tag)}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                // 更新本地缓存
                state.globalTags = state.globalTags.filter(t => t !== tag);
                // 同时更新所有文档的标签显示（如果已加载）
                for (const name in state.kbDocs) {
                    state.kbDocs[name].tags = state.kbDocs[name].tags.filter(t => t !== tag);
                    state.kbDocs[name].semantic_tags = state.kbDocs[name].semantic_tags.filter(t => t !== tag);
                }
            }
        } catch (e) {
            console.error("Failed to delete global tag:", e);
        }
    };

    // 动作：从知识库彻底删除文档
    const deleteKbDoc = async (fileRef) => {
        const doc = getDocByReference(fileRef);
        const displayName = doc?.name || fileRef;
        if (!confirm(`Are you sure you want to permanently delete "${displayName}"? This cannot be undone.`)) {
            return;
        }
        try {
            const endpoint = doc?.documentId
                ? `/api/kb/doc/${encodeURIComponent(doc.documentId)}`
                : `/api/kb/delete/${encodeURIComponent(displayName)}`;
            const res = await apiFetch(endpoint, { method: 'DELETE' });
            // Treat 404 (Not Found) as success, assuming file is already deleted
            if (res.ok || res.status === 404) {
                // 从本地缓存移除
                const kbKey = doc?.storageKey || displayName;
                if (state.kbDocs[kbKey]) {
                    delete state.kbDocs[kbKey];
                }
                state.documentLibrary = state.documentLibrary.filter(item => item.documentId !== doc?.documentId && item.name !== displayName);
                // 从所有会话移除引用
                state.sessions.forEach(sess => {
                    const idx = sess.docs.findIndex(d => d.name === displayName || d.documentId === doc?.documentId);
                    if (idx !== -1) {
                         sess.docs.splice(idx, 1);
                         persistSession(sess);
                    }
                });
                
                // 如果当前正在查看此文档，关闭它
                if (state.viewingPdf && state.viewingPdf.name === displayName) closePdf();
                if (state.viewingDocTree && state.viewingDocTree.name === displayName) closeSidePanel();
            } else {
                const err = await res.json().catch(() => ({}));
                alert("Delete failed: " + (err.detail || `Status ${res.status}`));
            }
        } catch (e) {
            console.error("Failed to delete kb doc:", e);
            alert("Delete failed: " + e.message);
        }
    };

    // 动作：获取单文档统计
    const fetchDocStats = async (fileRef) => {
        const doc = getDocByReference(fileRef);
        try {
            const endpoint = doc?.documentId
                ? `/api/documents/${encodeURIComponent(doc.documentId)}/stats`
                : `/api/docs/stats/${encodeURIComponent(doc?.name || fileRef)}`;
            const res = await apiFetch(endpoint);
            if (res.ok) {
                state.docStats = await res.json();
                state.docStats.file_name = doc?.name || fileRef;
                state.docStats.document_id = doc?.documentId || null;
            }
        } catch (e) {
            console.error("Failed to fetch doc stats:", e);
        }
    };

    // 动作：获取当前 Session 所有文档统计
    const fetchSessionStats = async () => {
        const session = getActiveSession();
        const fileNames = session.docs.map(d => d.name);
        const documentIds = session.docs.map(d => d.documentId).filter(Boolean);
        if (fileNames.length === 0) {
            state.sessionStats = null;
            return;
        }

        try {
            const res = await apiFetch('/api/session/stats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_names: fileNames,
                    document_ids: documentIds.length > 0 ? documentIds : undefined
                })
            });
            if (res.ok) {
                state.sessionStats = await res.json();
            }
        } catch (e) {
            console.error("Failed to fetch session stats:", e);
        }
    };

    const loadUserDocuments = async () => {
        if (!state.currentUser) {
            state.documentLibrary = [];
            return;
        }
        try {
            const res = await apiFetch('/api/documents');
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            setDocumentLibrary(data.documents || []);
            state.sessions = state.sessions.map((session) => ({
                ...session,
                docs: session.docs.map((doc) => {
                    const latest = getDocByReference(doc.documentId || doc.storageKey || doc.name);
                    return latest ? { ...latest, id: doc.id || latest.id } : doc;
                })
            }));
            syncCurrentSessionDocs();
        } catch (e) {
            console.error("Failed to load user documents:", e);
        }
    };

    const fetchCurrentUser = async () => {
        try {
            const res = await apiFetch('/api/auth/me');
            if (!res.ok) {
                if (res.status === 401) {
                    state.currentUser = null;
                    return null;
                }
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            state.currentUser = data.user;
            return data.user;
        } catch (e) {
            console.error("Failed to fetch current user:", e);
            state.currentUser = null;
            return null;
        }
    };

    const authenticate = async (mode, payload) => {
        state.authError = '';
        const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
        const res = await apiFetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(data.detail || `HTTP ${res.status}`);
        }
        state.currentUser = data.user;
        await Promise.all([loadSettings(), loadModelInstances()]);
        await loadUserDocuments();
        await loadConversations();
        await Promise.all([fetchKbDocs(), fetchGlobalTags()]);
        return data.user;
    };

    const logout = async () => {
        try {
            await apiFetch('/api/auth/logout', { method: 'POST' });
        } catch (e) {
            console.error("Logout failed:", e);
        } finally {
            state.currentUser = null;
            state.documentLibrary = [];
            state.kbDocs = {};
            state.globalTags = [];
            resetSessionState();
        }
    };

    const initializeApp = async () => {
        state.isAuthLoading = true;
        await fetchCurrentUser();
        if (state.currentUser) {
            await Promise.all([loadSettings(), loadModelInstances()]);
            await loadUserDocuments();
            await loadConversations();
            await Promise.all([fetchKbDocs(), fetchGlobalTags()]);
        } else {
            state.documentLibrary = [];
            state.kbDocs = {};
            state.globalTags = [];
            state.modelInstances = [];
            state.settings = normalizeSettings(JSON.parse(localStorage.getItem('modora_settings')) || DEFAULT_SETTINGS);
        }
        state.isAuthLoading = false;
    };

    return {
        state,
        getActiveSession,
        setActiveSession,
        createNewSession,
        deleteSession,
        renameSession,
        openPdf,
        setViewingDoc,
        closeSidePanel,
        closePdf,
        sendMessage,
        uploadFile,
        saveTreeStructure,
        updateTreeNode,
        updateSettings,
        loadSettings,
        loadModelInstances,
        createModelInstance,
        deleteModelInstance,
        initializeApp,
        authenticate,
        logout,
        fetchCurrentUser,
        loadUserDocuments,
        fetchKbDocs,
        fetchGlobalTags,
        updateDocTags,
        fetchDocStats,
        fetchSessionStats,
        addDocFromKb,
        getKbInfoForDoc,
        getKbKeyForDoc,
        removeDocFromSession,
        deleteGlobalTag,
        deleteKbDoc
    };
}
