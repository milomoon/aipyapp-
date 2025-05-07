<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>任务展示</title>
    <style>
      :root {
            --primary-color: #3b82f6;
            --secondary-color: #10b981;
            --background-color: #f5f7fa;
            --card-bg: #ffffff;
            --code-bg: #1e293b;
            --code-color: #e2e8f0;
            --text-color: #334155;
            --border-radius: 8px;
            --shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--background-color);
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 1000px;
            margin: 30px auto;
            padding: 20px;
        }

        header {
            text-align: center;
            margin-bottom: 30px;
        }

        h1 {
            color: var(--primary-color);
            font-weight: 600;
            margin-bottom: 10px;
        }

        .task-card {
            background-color: var(--card-bg);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            padding: 25px;
            margin-bottom: 25px;
            animation: fadeIn 0.5s ease-in-out;
        }

        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(10px); }
            100% { opacity: 1; transform: translateY(0); }
        }

        .instruction-section {
            margin-bottom: 30px;
        }

        .instruction-section h2 {
            color: var(--secondary-color);
            font-weight: 500;
            margin-bottom: 15px;
            border-bottom: 2px solid var(--secondary-color);
            padding-bottom: 8px;
        }

        .instruction-content {
            font-size: 18px;
            padding: 15px;
            background-color: rgba(16, 185, 129, 0.1);
            border-left: 4px solid var(--secondary-color);
            border-radius: var(--border-radius);
        }

        .message-section h2 {
            color: var(--primary-color);
            font-weight: 500;
            margin-bottom: 15px;
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 8px;
        }

        .message-list {
            margin-top: 20px;
        }

        .message-item {
            margin-bottom: 20px;
            padding: 15px;
            background-color: rgba(59, 130, 246, 0.05);
            border-radius: var(--border-radius);
            border-left: 4px solid var(--primary-color);
        }

        .user-message {
            border-left-color: #8b5cf6;
            background-color: rgba(139, 92, 246, 0.05);
        }

        .assistant-message {
            border-left-color: #10b981;
            background-color: rgba(16, 185, 129, 0.05);
        }

        .message-role {
            font-weight: 500;
            margin-bottom: 10px;
        }

        .user-role {
            color: #8b5cf6;
        }

        .assistant-role {
            color: #10b981;
        }

        .message-content {
            white-space: pre-wrap;
        }

        pre {
            margin: 15px 0;
            border-radius: var(--border-radius);
            background-color: var(--code-bg);
            color: var(--code-color);
            padding: 12px;
            overflow: auto;
        }

        code {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 14px;
        }

        .loading {
            text-align: center;
            padding: 50px;
            font-size: 18px;
            color: #777;
        }

        .error {
            background-color: #fee2e2;
            color: #ef4444;
            padding: 15px;
            border-radius: var(--border-radius);
            margin: 20px 0;
            border-left: 4px solid #ef4444;
        }

        .python-keyword { color: #ff79c6; }
        .python-string { color: #f1fa8c; }
        .python-comment { color: #6272a4; }
        .python-number { color: #bd93f9; }
        .python-function { color: #50fa7b; }
        .python-builtin { color: #8be9fd; }
    </style>
  </head>
  <body>
    <div class="container">
      <header>
        <h1>任务展示</h1>
      </header>
      <div id="content">
        <div class="loading">加载中，请稍候...</div>
      </div>
    </div>
    <script>
      const taskData = {{code}};
      document.addEventListener('DOMContentLoaded', async () => {
            const contentElement = document.getElementById('content');
            
            try {
                // 加载 task.json 文件
				/*
                const response = await fetch('task.json');
                
                if (!response.ok) {
                    throw new Error('无法加载 task.json 文件');
                }
                
                const taskData = await response.json();
                */
				
                // 过滤掉 role=system 的消息
                const filteredMessages = taskData.llm.filter(message => message.role !== 'system');
                
                // 渲染内容
                contentElement.innerHTML = `
                    <div class="task-card">
                        <div class="instruction-section">
                            <h2>任务指令</h2>
                            <div class="instruction-content">${taskData.instruction}</div>
                        </div>
                        
                        <div class="message-section">
                            <h2>对话内容</h2>
                            <div class="message-list">
                                ${filteredMessages.map(message => `
                                    <div class="message-item ${message.role === 'user' ? 'user-message' : 'assistant-message'}">
                                        <div class="message-role ${message.role === 'user' ? 'user-role' : 'assistant-role'}">
                                            ${message.role === 'user' ? '用户' : '助手'}
                                        </div>
                                        <div class="message-content">${formatContent(message.content)}</div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                `;
                
            } catch (error) {
                contentElement.innerHTML = `
                    <div class="error">
                        <strong>加载错误:</strong> ${error.message}
                    </div>
                    <div class="task-card">
                        <p>请确保:</p>
                        <ul>
                            <li>文件格式正确</li>
                        </ul>
                    </div>
                `;
            }
        });
        
		// 格式化内容，处理代码块
		function formatContent(content) {
			const codePattern = /```(python|json)?([^```]+)```/g;
		
			return content.replace(codePattern, (match, language, code) => {
			const lang = language ? language.toLowerCase() : '';
			const highlightedCode = lang === 'python' ? highlightPython(code) : code;
			const escapedCode = highlightedCode;
			return `
				<details>
				<summary style="cursor: pointer; color: var(--primary-color); font-weight: bold;">点击查看代码</summary>
				<pre style="margin-top: 0px;"><code class="${lang}">${escapedCode}</code></pre>
				</details>
			`;
			});
		}
        
        // 简单的 Python 代码高亮函数（无第三方库）
        function highlightPython(code) {
			/*
            // 安全处理 HTML 字符
            code = code.replace(/</g, '&lt;').replace(/>/g, '&gt;');
            
            // 高亮 Python 关键词
            const keywords = ['def', 'if', 'else', 'elif', 'for', 'while', 'in', 'try', 'except', 'finally', 
                             'class', 'return', 'import', 'from', 'as', 'with', 'True', 'False', 'None', 'and', 'or', 'not'];
            
            // 内置函数
            const builtins = ['print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 'range', 'input', 'sum', 'min', 'max'];
            
            // 应用高亮
            keywords.forEach(keyword => {
                const regex = new RegExp(`\\b${keyword}\\b`, 'g');
                code = code.replace(regex, `<span class="python-keyword">${keyword}</span>`);
            });
            
            builtins.forEach(builtin => {
                const regex = new RegExp(`\\b${builtin}\\b(?=\\s*\\()`, 'g');
                code = code.replace(regex, `<span class="python-builtin">${builtin}</span>`);
            });
            
            // 高亮字符串 (简单处理)
            code = code.replace(/'([^'\\]*(\\.[^'\\]*)*)'|"([^"\\]*(\\.[^"\\]*)*)"/g, 
                match => `<span class="python-string">${match}</span>`);
            
            // 高亮数字
            code = code.replace(/\b(\d+(\.\d+)?)\b/g, 
                match => `<span class="python-number">${match}</span>`);
            
            // 高亮注释
            code = code.replace(/(#.*$)/gm, 
                match => `<span class="python-comment">${match}</span>`);
            */
            return code;
        }
    </script>
  </body>
</html>