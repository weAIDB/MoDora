import { reactive } from 'vue';

// 1. 更新初始数据，匹配你后端已处理的文件名
const INITIAL_DOCS = [
    { id: 1, name: "1.pdf", type: "pdf" },
    { id: 2, name: "2.pdf", type: "pdf" },
    { id: 3, name: "3.pdf", type: "pdf" }
];

// 核心状态
const state = reactive({
    messages: [
        {
            role: "assistant",
            content: "你好！后端服务已连接。我现在默认基于 [1.pdf] 进行问答，请直接提问。",
            isTyping: false
        }
    ],
    knowledgeBase: [...INITIAL_DOCS],
    isThinking: false,
    isUploading: false,
    viewingDocTree: null,
    inputMessage: ''
});

// 辅助：生成 Mermaid 图表代码
const generateGraph = {
    tree(docName) {
        // 保持原来的文档结构树逻辑不变（仅做展示用）
        return `
        graph LR
            root["📄 ${docName}"]:::rootNode
            subgraph Chapters [章节概览]
                direction TB
                c1["1. 前言与背景"]
                c2["2. 核心内容"]
            end
            root --> c1
            root --> c2
            classDef rootNode fill:#4f46e5,stroke:#312e81,color:white;
        `;
    },
    // 2. 修改检索图生成逻辑，接收后端返回的 log
    retrieval(query, logContent) {
        const qShort = query.length > 6 ? query.substring(0, 6) + '...' : query;
        // 处理 log 文本，防止破坏 mermaid 语法 (简单的转义)
        const safeLog = logContent ? logContent.replace(/"/g, "'").substring(0, 50) + "..." : "后端未返回详细日志";

        return `
        graph TD
            Q(("🔍 提问:<br/>${qShort}")):::qNode
            API[("☁️ 后端 API")]:::apiNode
            Log["📄 检索日志:<br/>${safeLog}"]:::logNode
            Ans["📝 最终答案"]:::ansNode

            Q --> API
            API --> Log
            Log --> Ans

            classDef qNode fill:#eef2ff,stroke:#6366f1,color:#312e81;
            classDef apiNode fill:#f1f5f9,stroke:#64748b;
            classDef logNode fill:#fff7ed,stroke:#f97316,stroke-dasharray: 5 5;
            classDef ansNode fill:#f0fdf4,stroke:#22c55e,stroke-width:2px;
        `;
    }
};

export function useModoraStore() {

    // 动作：发送消息
    const sendMessage = async () => {
        const text = state.inputMessage.trim();
        if (!text) return;

        // 1. 用户消息上屏
        state.messages.push({ role: "user", content: text });
        const currentQuery = text;
        state.inputMessage = '';

        // 2. 进入思考状态
        state.isThinking = true;

        // 默认使用第一个文件作为上下文
        const activeFile = state.knowledgeBase[0].name;

        try {
            // 3. 发起真实 API 请求
            // 注意：如果你本地开发，前端在 localhost:5173，后端在 localhost:8000
            // 可能需要在 vite.config.js 配置 proxy 解决跨域，或者直接写完整 URL
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_name: activeFile,
                    query: currentQuery
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // 4. 获取结果
            const answer = data.answer || "后端未返回答案";
            const log = data.log || "";

            state.isThinking = false;

            // 5. 准备 AI 回复对象
            const newMsg = {
                role: "assistant",
                content: "",
                isTyping: true,
                graphData: null
            };
            state.messages.push(newMsg);

            // 获取响应式对象引用
            const activeMsg = state.messages[state.messages.length - 1];

            // 6. 模拟打字机效果显示真实答案
            let i = 0;
            const timer = setInterval(() => {
                activeMsg.content += answer.charAt(i);
                i++;
                if (i >= answer.length) {
                    clearInterval(timer);
                    activeMsg.isTyping = false;
                    // 生成包含后端 Log 的图表
                    activeMsg.graphData = generateGraph.retrieval(currentQuery, log);
                }
            }, 30); // 打字速度

        } catch (error) {
            console.error("API 请求失败:", error);
            state.isThinking = false;
            state.messages.push({
                role: "assistant",
                content: `❌ 请求失败: ${error.message}。请检查后端服务是否启动，以及跨域(CORS)配置。`,
                isTyping: false
            });
        }
    };

    // 动作：上传文件 (暂时保持模拟，或后续对接真实上传接口)
    const handleFileUpload = (file) => {
        if (!file) return;
        state.isUploading = true;
        setTimeout(() => {
            const ext = file.name.split('.').pop().toLowerCase();
            state.knowledgeBase.push({
                id: state.knowledgeBase.length + 1,
                name: file.name,
                type: ext
            });
            state.isUploading = false;
        }, 1000);
    };

    const setViewingDoc = (doc) => {
        state.viewingDocTree = doc;
    };

    return {
        state,
        sendMessage,
        handleFileUpload,
        setViewingDoc
    };
}
