项目简介

**机械臂智能问答系统**是一个基于科大讯飞Spark API的智能对话与知识图谱构建平台。系统结合了先进的大语言模型和知识图谱技术，提供智能问答、实体关系抽取、动态图谱构建与可视化等功能。
智能对话引擎
- 基于科大讯飞Spark API的多轮对话支持
- 上下文记忆和连续对话能力
- 多语言混合输入识别
- 智能意图识别和推理

知识图谱构建
- 实时实体关系抽取
- 动态知识图谱生成与更新
- 交互式可视化探索
- 多源数据融合能力

系统架构

前端技术栈
- **HTML5/CSS3** - 页面结构和样式
- **JavaScript (ES6+)** - 交互逻辑
- **Bootstrap 5** - UI框架
- **CSS Grid/Flexbox** - 布局系统
后端技术栈
- **Python Flask** - Web框架
- **NetworkX** - 图谱处理
- **Matplotlib** - 图表生成
- **jieba** - 中文分词
- **科大讯飞Spark API** - AI模型接口
项目结构
robotic-kg-system/
├── app.py                    # Flask后端主程序
├── static
│   └── css
│        └── style.css
│   └── js
│        └── script.js
├── requirements.txt         # Python依赖包
├── templates/
│   └── index.html          # 主页面模板
└── README.txt             # 项目文档

环境要求
- Python 3.8+
- Flask==2.3.3
- requests==2.31.0
- jieba==0.42.1
- networkx==3.1
- numpy==1.24.3  
- pyecharts==2.0.3
- flask-cors==4.0.0
- matplotlib==3.7.3
- 科大讯飞Spark API账户

安装步骤
1. **克隆或创建项目**
```bash
mkdir robotic-kg-system
cd robotic-kg-system
```
2. **安装依赖**
```bash
pip install -r requirements.txt
```
3. **配置科大讯飞API**
- 在`index.html`中配置API Key和Secret：
```html
<input type="password" class="form-control" id="apiKey"
       value="您的API_KEY">
<input type="password" class="form-control" id="apiSecret"
       value="您的API_SECRET">
```
4. **启动应用**
```bash
python app.py
```
5. **访问系统**
- 打开浏览器访问：`http://localhost:5000`

功能使用指南

#1. API配置
- 在左侧面板输入科大讯飞Spark API的Key和Secret
- 点击"测试连接"验证API可用性

#2. 会话管理
- **新建会话**：创建新的对话上下文
- **清空会话**：重置当前会话数据
- **会话ID**：自动生成，支持复制

#3. 智能对话
1. 在提问区域输入问题
2. 可选择是否生成知识图谱
3. 支持回车键快速发送
4. 可从示例问题中选择

#4. 知识图谱功能
- **实时构建**：对话中自动抽取实体关系
- **可视化**：动态生成并显示知识图谱
- **导出功能**：支持JSON/CSV格式导出
- **统计信息**：实时显示图谱规模

### 5. 功能菜单
- **智能助手**：查看对话AI功能特性
- **图谱生成**：了解知识图谱构建能力

 API接口说明

 后端API端点
```
GET    /api/new_session           # 创建新会话
POST   /api/test_connection       # 测试API连接
POST   /api/ask                   # 提问并获取回答
POST   /api/clear                 # 清空会话数据
GET    /api/export?format=json    # 导出数据
GET    /api/example_questions     # 获取示例问题
```
前端-后端数据流
1. 用户输入问题 → 前端JS处理
2. 发送POST请求到`/api/ask`
3. 后端调用科大讯飞API获取回答
4. 抽取实体关系并构建图谱
5. 生成可视化图表返回前端
6. 前端更新所有显示区域

 配置说明

 科大讯飞API配置
```python
API_KEY = "您的API_KEY"
API_SECRET = "您的API_SECRET"
BASE_URL = "https://spark-api-open.xf-yun.com/v2"
```

 系统配置
- 默认端口：5000
- 调试模式：启用
- CORS：允许所有来源
- 会话管理：内存存储

 日志查看
```bash
# 查看Flask服务器日志
python app.py
# 查看浏览器控制台（F12）
```

 相关技术
- **Flask官方文档**：https://flask.palletsprojects.com/
- **科大讯飞Spark API**：https://www.xfyun.cn/doc/spark
- **NetworkX教程**：https://networkx.org/documentation/
- **Bootstrap 5文档**：https://getbootstrap.com/docs/5.1/



**版本**: 1.0.0
**最后更新**: 2026年1月25日