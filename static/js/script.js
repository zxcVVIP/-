// 全局变量
let currentSessionId = null;
let apiKey = '';
let apiSecret = '';

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化会话
    newSession();

    // 加载示例问题
    loadExampleQuestions();

    // 设置API密钥
    apiKey = document.getElementById('apiKey').value;
    apiSecret = document.getElementById('apiSecret').value;

    // 绑定回车键发送
    document.getElementById('questionInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            askQuestion();
        }
    });
});

// 测试API连接
async function testConnection() {
    apiKey = document.getElementById('apiKey').value;
    apiSecret = document.getElementById('apiSecret').value;

    if (!apiKey || !apiSecret) {
        showMessage('错误', '请填写API Key和Secret');
        return;
    }

    const button = document.querySelector('button[onclick="testConnection()"]');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="bi bi-hourglass-split"></i> 测试中...';
    button.disabled = true;

    try {
        const response = await fetch('/api/test_connection', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({api_key: apiKey, api_secret: apiSecret})
        });

        const data = await response.json();

        if (data.success) {
            showMessage('成功', 'API连接测试成功！');
        } else {
            showMessage('错误', '连接失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        showMessage('错误', '请求失败: ' + error.message);
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// 创建新会话
async function newSession() {
    try {
        const response = await fetch('/api/new_session');
        const data = await response.json();

        if (data.success) {
            currentSessionId = data.session_id;
            document.getElementById('sessionId').value = currentSessionId;
            clearAllDisplays();
            showMessage('成功', '已创建新会话');
        }
    } catch (error) {
        showMessage('错误', '创建会话失败: ' + error.message);
    }
}

// 提问
async function askQuestion() {
    const question = document.getElementById('questionInput').value.trim();
    if (!question) {
        showMessage('提示', '请输入问题');
        return;
    }

    if (!currentSessionId) {
        await newSession();
    }

    const visualize = document.getElementById('visualizeGraph').checked;
    const askButton = document.getElementById('askButton');
    const originalText = askButton.innerHTML;

    askButton.innerHTML = '<i class="bi bi-hourglass-split"></i> 处理中...';
    askButton.disabled = true;

    // 显示加载中
    document.getElementById('loadingSpinner').classList.remove('d-none');
    document.getElementById('knowledgeGraph').style.display = 'none';
    document.getElementById('noGraph').style.display = 'none';

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                question: question,
                session_id: currentSessionId,
                visualize: visualize
            })
        });

        const data = await response.json();

        if (data.success) {
            // 更新界面
            updateDisplay(data);
            // 清空输入框
            document.getElementById('questionInput').value = '';
        } else {
            showMessage('错误', data.error || '请求失败');
        }
    } catch (error) {
        showMessage('错误', '请求失败: ' + error.message);
    } finally {
        askButton.innerHTML = originalText;
        askButton.disabled = false;
        document.getElementById('loadingSpinner').classList.add('d-none');
    }
}

// 更新显示
function updateDisplay(data) {
    // 显示知识图谱
    if (data.graph_image) {
        const graphImg = document.getElementById('knowledgeGraph');
        graphImg.src = data.graph_image;
        graphImg.style.display = 'block';
        document.getElementById('noGraph').style.display = 'none';
    }

    // 添加对话历史
    addToChatHistory(data.question, data.answer);

    // 显示实体
    displayEntities(data.extraction?.entities || []);

    // 显示三元组
    displayTriples(data.new_triples || []);

    // 更新统计信息
    updateStats(data.graph_stats || {total_entities: 0, total_triples: 0});

    // 显示使用统计
    if (data.usage) {
        showUsageStats(data.usage);
    }
}

// 添加对话历史
function addToChatHistory(question, answer) {
    const chatHistory = document.getElementById('chatHistory');

    // 如果显示"暂无对话历史"，先清除
    if (chatHistory.children.length === 1 && chatHistory.children[0].classList.contains('text-muted')) {
        chatHistory.innerHTML = '';
    }

    // 添加用户消息
    const userMessage = document.createElement('div');
    userMessage.className = 'message user-message';
    userMessage.innerHTML = `
        <strong><i class="bi bi-person-circle"></i> 您:</strong>
        <p class="mb-0">${escapeHtml(question)}</p>
        <small class="text-muted">${new Date().toLocaleTimeString()}</small>
    `;
    chatHistory.appendChild(userMessage);

    // 添加AI消息
    const aiMessage = document.createElement('div');
    aiMessage.className = 'message ai-message';
    aiMessage.innerHTML = `
        <strong><i class="bi bi-robot"></i> AI:</strong>
        <p class="mb-0">${escapeHtml(answer)}</p>
        <small class="text-muted">${new Date().toLocaleTimeString()}</small>
    `;
    chatHistory.appendChild(aiMessage);

    // 滚动到底部
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// 显示实体
function displayEntities(entities) {
    const container = document.getElementById('entitiesList');

    if (entities.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无实体</p>';
        return;
    }

    let html = '';
    entities.forEach(entity => {
        html += `<span class="entity-badge">${escapeHtml(entity)}</span> `;
    });
    container.innerHTML = html;
}

// 显示三元组
function displayTriples(triples) {
    const container = document.getElementById('triplesList');

    if (triples.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无关系</p>';
        return;
    }

    let html = '';
    triples.forEach((triple, index) => {
        html += `
            <div class="triple-item">
                <strong>${index + 1}.</strong>
                <span class="badge bg-primary">${escapeHtml(triple.subject)}</span>
                <span class="badge bg-success">${escapeHtml(triple.predicate)}</span>
                <span class="badge bg-warning text-dark">${escapeHtml(triple.object)}</span>
            </div>
        `;
    });
    container.innerHTML = html;
}

// 更新统计信息
function updateStats(stats) {
    const container = document.getElementById('statsContent');
    container.innerHTML = `
        <div class="stats-item">
            <i class="bi bi-tags"></i> 实体总数: <strong>${stats.total_entities || 0}</strong>
        </div>
        <div class="stats-item">
            <i class="bi bi-link"></i> 关系总数: <strong>${stats.total_triples || 0}</strong>
        </div>
    `;
}

// 显示使用统计
function showUsageStats(usage) {
    console.log('Token使用情况:', usage);
    // 可以在界面上添加更多详细信息显示
}

// 清空会话
async function clearSession() {
    if (!currentSessionId) {
        showMessage('提示', '没有活动的会话');
        return;
    }

    if (!confirm('确定要清空当前会话的所有数据吗？')) {
        return;
    }

    try {
        const response = await fetch('/api/clear', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({session_id: currentSessionId})
        });

        const data = await response.json();

        if (data.success) {
            clearAllDisplays();
            showMessage('成功', '会话已清空');
        }
    } catch (error) {
        showMessage('错误', '清空会话失败: ' + error.message);
    }
}

// 清空所有显示
function clearAllDisplays() {
    document.getElementById('knowledgeGraph').style.display = 'none';
    document.getElementById('noGraph').style.display = 'block';
    document.getElementById('chatHistory').innerHTML =
        '<div class="text-muted text-center p-3">暂无对话历史</div>';
    document.getElementById('entitiesList').innerHTML =
        '<p class="text-muted">暂无实体</p>';
    document.getElementById('triplesList').innerHTML =
        '<p class="text-muted">暂无关系</p>';
    document.getElementById('statsContent').innerHTML =
        '<p class="text-muted">暂无数据</p>';
}

// 导出数据
async function exportData(format) {
    if (!currentSessionId) {
        showMessage('提示', '没有要导出的数据');
        return;
    }

    try {
        const response = await fetch(`/api/export?session_id=${currentSessionId}&format=${format}`);
        const data = await response.json();

        if (data.success) {
            if (format === 'json') {
                downloadJson(data.data, `knowledge_graph_${currentSessionId}.json`);
            } else if (format === 'csv') {
                downloadCsv(data.data, `knowledge_graph_${currentSessionId}.csv`);
            }
            showMessage('成功', '数据导出成功');
        } else {
            showMessage('错误', data.error || '导出失败');
        }
    } catch (error) {
        showMessage('错误', '导出失败: ' + error.message);
    }
}

// 下载JSON文件
function downloadJson(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// 下载CSV文件
function downloadCsv(data, filename) {
    const blob = new Blob([data], {type: 'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// 复制会话ID
function copySessionId() {
    const sessionIdInput = document.getElementById('sessionId');
    sessionIdInput.select();
    document.execCommand('copy');
    showMessage('提示', '会话ID已复制到剪贴板');
}

// 加载示例问题
async function loadExampleQuestions() {
    try {
        const response = await fetch('/api/example_questions');
        const data = await response.json();

        if (data.success) {
            const container = document.getElementById('exampleQuestions');
            container.innerHTML = '';

            data.examples.forEach(question => {
                const div = document.createElement('div');
                div.className = 'list-group-item example-question';
                div.textContent = question;
                div.onclick = () => {
                    document.getElementById('questionInput').value = question;
                };
                container.appendChild(div);
            });
        }
    } catch (error) {
        console.error('加载示例问题失败:', error);
    }
}

// 显示消息模态框
function showMessage(title, message) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalMessage').textContent = message;
    const modal = new bootstrap.Modal(document.getElementById('messageModal'));
    modal.show();
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}