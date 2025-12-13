import { reactive } from 'vue';

// 1. 初始文件列表
const INITIAL_DOCS = [
    { id: 1, name: "1.pdf", type: "pdf" },
    { id: 2, name: "2.pdf", type: "pdf" },
    { id: 3, name: "3.pdf", type: "pdf" }
];

// 辅助：创建初始欢迎消息
const createWelcomeMessage = (docName) => [
    {
        role: "assistant",
        content: docName 
            ? `你好！我是文档 **${docName}** 的助手。请问有什么可以帮你的？`
            : "你好！请在左侧点击选择一个文档，然后开始提问。",
        isTyping: false
    }
];

// 初始化每个文档的会话历史
const initialSessions = {};
INITIAL_DOCS.forEach(doc => {
    initialSessions[doc.id] = createWelcomeMessage(doc.name);
});

// 核心状态
const state = reactive({
    chatSessions: initialSessions, // 存储所有文档的会话历史 { docId: [messages] }
    messages: initialSessions[1],  // 当前显示的会话 (引用 chatSessions 中的某个数组)
    knowledgeBase: [...INITIAL_DOCS],
    activeDocId: 1, // 新增：当前被选中的文档 ID (默认选中第一个)
    isThinking: false,
    isUploading: false,
    uploadProgress: 0,
    viewingDocTree: null,
    viewingPdf: null,
    inputMessage: ''
});

// 辅助：生成 Mermaid 图表 (仅保留文档树)
const generateGraph = {
    tree(docName) {
        return `
        graph LR
            root["📄 ${docName}"]:::rootNode
            c1["章节解析中..."]
            root --> c1
            classDef rootNode fill:#4f46e5,stroke:#312e81,color:white;
        `;
    }
};

export function useModoraStore() {

    // 动作：切换当前提问的文档
    const setActiveDoc = (id) => {
        if (state.activeDocId === id) return; // 如果已经是当前文档，不做操作

        state.activeDocId = id;
        
        // 切换消息上下文
        // 确保该文档有会话历史
        if (!state.chatSessions[id]) {
            const doc = state.knowledgeBase.find(d => d.id === id);
            state.chatSessions[id] = createWelcomeMessage(doc ? doc.name : "");
        }
        
        // 将 state.messages 指向对应文档的数组引用
        state.messages = state.chatSessions[id];
    };

    // 打开 PDF 动作
    const openPdf = (fileId, page = 1, bboxes = []) => {
        const doc = state.knowledgeBase.find(d => d.id === fileId) || state.knowledgeBase[0];
        const fileUrl = `/api/files/${encodeURIComponent(doc.name)}`;

        state.viewingPdf = {
            url: fileUrl,
            page: page,
            name: doc.name,
            bboxes: bboxes || [] // 新增：传递高亮框，确保不为 null
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

        state.messages.push({ role: "user", content: text });
        const currentQuery = text;
        state.inputMessage = '';
        state.isThinking = true;

        // --- 核心修改：使用 activeDocId 获取当前文件名 ---
        const activeDocObj = state.knowledgeBase.find(d => d.id === state.activeDocId) || state.knowledgeBase[0];
        const activeFile = activeDocObj.name;
        const activeFileId = activeDocObj.id;

        let answer = "";
        let citations = [];

        try {
            // 发起真实 API 请求
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_name: activeFile, query: currentQuery })
            });

            if (!response.ok) {
                let errorMessage = `HTTP Error ${response.status}`;
                try {
                    const errData = await response.json();
                    if (errData.detail) errorMessage += `: ${errData.detail}`;
                } catch (e) {}
                throw new Error(errorMessage);
            }

            const data = await response.json();
            answer = data.answer || "后端未返回有效答案";

            const retrievedDocs = data.retrieved_documents || [];

            citations = retrievedDocs.map((doc) => {
                let snippetText = doc.content || "引用详情...";
                if (snippetText.length > 60) snippetText = snippetText.substring(0, 60) + "...";

                return {
                    fileId: activeFileId, // 绑定到当前选中的文件
                    fileName: activeFile,
                    page: doc.page,
                    snippet: snippetText,
                    bboxes: doc.bboxes
                };
            });

        } catch (error) {
            console.error("API 请求失败:", error);
            answer = `❌ 请求失败: ${error.message}`;
            if (error.message.includes("404")) {
                answer += "\n\n💡 提示: 请检查后端数据集路径及文件完整性。";
            }
            citations = [
                { fileId: activeFileId, fileName: activeFile, page: 1, snippet: "(模拟) API 出错时的 fallback 引用" }
            ];
        } finally {
            state.isThinking = false;

            const newMsg = {
                role: "assistant",
                content: "",
                isTyping: true,
                citations: citations
            };

            state.messages.push(newMsg);

            const activeMsg = state.messages[state.messages.length - 1];

            let i = 0;
            const timer = setInterval(() => {
                activeMsg.content += answer.charAt(i);
                i++;
                if (i >= answer.length) {
                    clearInterval(timer);
                    activeMsg.isTyping = false;
                }
            }, 30);
        }
    };

    const handleFileUpload = async (file) => {
        if (!file) return;
        state.isUploading = true;
        state.uploadProgress = 0;
        
        let progressTimer = null;
        let pollTimer = null;

        // 阶段 1: 模拟上传进度 (0-40%)
        // 假设上传和初步响应比较快
        progressTimer = setInterval(() => {
            if (state.uploadProgress < 40) {
                state.uploadProgress += 2;
            }
        }, 200);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            clearInterval(progressTimer); // 停止第一阶段模拟

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
            }

            // 上传成功，进入处理阶段，进度条跳到 40%
            state.uploadProgress = 40;
            const data = await response.json();
            const filename = data.filename;

            // 阶段 2: 轮询后台状态 (40% -> 99%)
            // 同时开启一个慢速的进度条模拟，让用户感觉还在动
            progressTimer = setInterval(() => {
                if (state.uploadProgress < 95) {
                    // 越往后越慢
                    const increment = state.uploadProgress > 80 ? 0.2 : 0.5;
                    state.uploadProgress = Math.min(state.uploadProgress + increment, 95);
                }
            }, 500);

            // 开始轮询
            await new Promise((resolve, reject) => {
                pollTimer = setInterval(async () => {
                    try {
                        const statusRes = await fetch(`/api/task/status/${encodeURIComponent(filename)}`);
                        if (!statusRes.ok) return; // 忽略网络错误，继续轮询
                        
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
                        // processing 或 pending 状态，继续等待
                    } catch (e) {
                        console.error("Polling error:", e);
                    }
                }, 2000); // 每 2 秒轮询一次
            });

            // 处理完成后的逻辑
            // 稍微停顿一下，让用户看到 100%
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // 上传成功后添加到列表
            const ext = filename.split('.').pop().toLowerCase();
            const newDoc = {
                id: state.knowledgeBase.length + 1, // 简单的 ID 生成策略
                name: filename,
                type: ext
            };
            
            state.knowledgeBase.push(newDoc);
            
            // 初始化新文档的会话历史
            state.chatSessions[newDoc.id] = createWelcomeMessage(newDoc.name);

            // 可选：自动选中新上传的文件
            setActiveDoc(newDoc.id);
            
            // 提示消息
            state.messages.push({
                role: "assistant",
                content: `✅ 文件 **${filename}** 处理完成！您现在可以开始提问了。`,
                isTyping: false
            });

        } catch (error) {
            clearInterval(progressTimer);
            if (pollTimer) clearInterval(pollTimer);
            console.error("Upload error:", error);
            state.messages.push({
                role: "assistant",
                content: `❌ 文件处理失败: ${error.message}`,
                isTyping: false
            });
        } finally {
            state.isUploading = false;
            state.uploadProgress = 0;
        }
    };

    // --- 树结构操作 ---
    const updateTreeNode = async (fileName, action, targetPath, newData = null) => {
        try {
            const response = await fetch('/api/tree/node/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_name: fileName,
                    action: action,
                    target_path: targetPath,
                    new_data: newData
                })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Update failed');
            }
            return true;
        } catch (error) {
            console.error('Failed to update tree node:', error);
            throw error;
        }
    };

    const saveTreeStructure = async (fileName, elements) => {
        try {
            const response = await fetch('/api/tree/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_name: fileName,
                    elements: elements
                })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Save failed');
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to save tree structure:', error);
            throw error;
        }
    };

    return {
        state,
        sendMessage,
        uploadFile: handleFileUpload, // Alias handleFileUpload to uploadFile
        handleFileUpload,
        setViewingDoc,
        openPdf,
        closePdf,
        closeSidePanel,
        setActiveDoc, // 导出新方法
        updateTreeNode,
        saveTreeStructure
    };
}
