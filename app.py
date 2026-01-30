import os
import json
import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_cors import CORS
import requests
import networkx as nx
import matplotlib

matplotlib.use('Agg')  # 使用非GUI后端
import matplotlib.pyplot as plt
import re
import jieba
import jieba.posseg as pseg
from io import BytesIO
import base64
import uuid
import threading
from typing import List, Dict, Any

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
app.secret_key = 'knowledge-graph-secret-key-2024'
CORS(app)

# 配置文件
UPLOAD_FOLDER = 'static/uploads'
GRAPH_FOLDER = 'static/graphs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GRAPH_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GRAPH_FOLDER'] = GRAPH_FOLDER


class SparkAPI:
    """Spark API封装类"""

    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://spark-api-open.xf-yun.com/v2"

    def set_credentials(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def test_connection(self):
        """测试API连接"""
        if not self.api_key or not self.api_secret:
            return {"error": "API密钥未设置"}

        result = self.chat("请回复'OK'表示连接正常")
        if "error" in result:
            return {"success": False, "error": result["error"]}
        elif "choices" in result and len(result["choices"]) > 0:
            return {"success": True, "response": result["choices"][0]["message"]["content"]}
        return {"success": False, "error": "未知错误"}

    def chat(self, message, model="spark-x", stream=False, max_retries=2):
        """发送聊天请求"""
        if not self.api_key or not self.api_secret:
            return {"error": "API密钥未设置"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}:{self.api_secret}"
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "stream": stream
        }

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}", "message": response.text}
            except requests.exceptions.Timeout:
                if attempt == max_retries:
                    return {"error": f"请求超时（尝试了{max_retries + 1}次）"}
                continue
            except Exception as e:
                return {"error": str(e)}

        return {"error": "请求失败"}


class EntityExtractor:
    """实体关系抽取器"""

    def __init__(self):
        self.relation_patterns = {
            '属于': ['是', '为', '属于', '作为', '叫做', '称为'],
            '包含': ['有', '包含', '包括', '拥有', '具备', '含有'],
            '位于': ['位于', '处在', '坐落在', '在', '地处', '坐落于'],
            '创造': ['创造', '发明', '提出', '创立', '建立', '开发'],
            '用于': ['用于', '用来', '适用于', '应用于', '作用于'],
            '相关': ['相关', '有关', '涉及', '关于', '关系到']
        }

    def extract_entities_relations(self, text: str) -> Dict[str, Any]:
        """从文本中抽取实体和关系"""
        entities = set()
        relations = []

        # 清理文本
        text = re.sub(r'\s+', ' ', text)

        # 使用jieba进行分词和词性标注
        words = pseg.cut(text)

        # 定义实体词性标签
        entity_pos_tags = ['nr', 'ns', 'nt', 'nz', 'n']

        # 提取命名实体
        for word, flag in words:
            if flag in entity_pos_tags and len(word) > 1:
                entities.add(word)

        # 如果命名实体太少，尝试提取名词短语
        if len(entities) < 3:
            words = pseg.cut(text)
            nouns = [word for word, flag in words if flag.startswith('n') and len(word) > 1]
            entities.update(nouns[:8])

        entities = list(entities)[:20]

        # 提取关系
        if len(entities) >= 2:
            sentences = re.split('[。！？；，]', text)
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    entity1 = entities[i]
                    entity2 = entities[j]

                    for sentence in sentences:
                        if entity1 in sentence and entity2 in sentence:
                            relation_type = self.detect_relation_type(sentence)
                            if relation_type:
                                relations.append({
                                    'subject': entity1,
                                    'predicate': relation_type,
                                    'object': entity2,
                                    'sentence': sentence.strip()[:100]
                                })
                                break

        # 去重
        unique_relations = []
        seen = set()
        for rel in relations:
            key = (rel['subject'], rel['predicate'], rel['object'])
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)

        return {
            'entities': entities[:15],
            'relations': unique_relations[:10]
        }

    def detect_relation_type(self, sentence: str) -> str:
        """检测关系类型"""
        sentence_lower = sentence

        for rel_type, keywords in self.relation_patterns.items():
            for keyword in keywords:
                if keyword in sentence_lower:
                    return rel_type

        if '是' in sentence or '为' in sentence or '叫做' in sentence:
            return '属于'
        elif '在' in sentence and ('位于' in sentence or '处在' in sentence):
            return '位于'
        elif '包括' in sentence or '包含' in sentence or '有' in sentence:
            return '包含'
        elif '用于' in sentence or '用来' in sentence:
            return '用于'

        return '相关'


class KnowledgeGraphManager:
    """知识图谱管理器"""

    def __init__(self):
        self.graphs = {}  # session_id -> graph_data
        self.spark_api = SparkAPI()
        self.extractor = EntityExtractor()

        # 设置matplotlib中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    def set_api_credentials(self, api_key: str, api_secret: str):
        """设置API凭证"""
        self.spark_api.set_credentials(api_key, api_secret)

    def process_question(self, question: str, session_id: str = None, visualize: bool = True) -> Dict[str, Any]:
        """处理问题并返回结果"""
        if not session_id:
            session_id = str(uuid.uuid4())

        # 调用大模型
        result = self.spark_api.chat(question)

        if "error" in result:
            return {
                "session_id": session_id,
                "error": result["error"],
                "success": False
            }

        if "choices" not in result or len(result["choices"]) == 0:
            return {
                "session_id": session_id,
                "error": "未收到有效响应",
                "success": False
            }

        response = result["choices"][0]["message"]["content"]

        # 抽取实体和关系
        extraction_result = self.extractor.extract_entities_relations(response)

        # 更新图谱
        if session_id not in self.graphs:
            self.graphs[session_id] = {
                "triples": [],
                "entities": set(),
                "history": []
            }

        graph_data = self.graphs[session_id]

        # 添加新的三元组
        new_triples = []
        for relation in extraction_result.get('relations', []):
            triple = {
                "subject": relation['subject'],
                "predicate": relation['predicate'],
                "object": relation['object'],
                "source": relation.get('sentence', '')
            }
            graph_data["triples"].append(triple)
            new_triples.append(triple)
            graph_data["entities"].add(relation['subject'])
            graph_data["entities"].add(relation['object'])

        # 添加对话历史
        graph_data["history"].append({
            "question": question,
            "answer": response,
            "timestamp": datetime.datetime.now().isoformat()
        })

        result_data = {
            "session_id": session_id,
            "success": True,
            "question": question,
            "answer": response,
            "extraction": extraction_result,
            "new_triples": new_triples,
            "graph_stats": {
                "total_entities": len(graph_data["entities"]),
                "total_triples": len(graph_data["triples"]),
                "total_history": len(graph_data["history"])
            }
        }

        # 添加使用统计
        if "usage" in result:
            result_data["usage"] = result["usage"]

        # 生成图谱图片
        if visualize and new_triples:
            graph_image = self.generate_graph_image(session_id)
            if graph_image:
                result_data["graph_image"] = graph_image

        return result_data

    def generate_graph_image(self, session_id: str) -> str:
        """生成知识图谱图片并返回base64编码"""
        if session_id not in self.graphs:
            return None

        graph_data = self.graphs[session_id]
        if not graph_data["triples"]:
            return None

        try:
            # 创建图
            G = nx.Graph()

            # 添加节点和边
            for triple in graph_data["triples"]:
                G.add_node(triple["subject"], type="entity")
                G.add_node(triple["object"], type="entity")
                G.add_edge(triple["subject"], triple["object"], relation=triple["predicate"])

            if len(G.nodes()) == 0:
                return None

            plt.figure(figsize=(12, 8))

            # 使用布局算法
            try:
                pos = nx.spring_layout(G, k=1.5, iterations=100, seed=42)
            except:
                pos = nx.circular_layout(G)

            # 绘制节点
            node_colors = []
            node_sizes = []

            for node in G.nodes():
                degree = G.degree(node)
                node_size = 800 + degree * 200
                node_sizes.append(min(node_size, 3000))
                node_colors.append('lightblue')

            nx.draw_networkx_nodes(
                G, pos,
                node_size=node_sizes,
                node_color=node_colors,
                alpha=0.8,
                edgecolors='black',
                linewidths=1
            )

            # 绘制边
            edges = G.edges()
            edge_labels = nx.get_edge_attributes(G, 'relation')

            nx.draw_networkx_edges(
                G, pos,
                edgelist=edges,
                width=2,
                alpha=0.6,
                edge_color='gray',
                style='solid'
            )

            # 添加标签
            nx.draw_networkx_labels(
                G, pos,
                font_size=10,
                font_weight='bold'
            )

            if edge_labels:
                nx.draw_networkx_edge_labels(
                    G, pos,
                    edge_labels=edge_labels,
                    font_color='red',
                    font_size=9
                )

            plt.title(f"知识图谱 (实体数: {len(G.nodes())}, 关系数: {len(G.edges())})",
                      fontsize=16, fontweight='bold', pad=20)
            plt.axis('off')
            plt.tight_layout()

            # 转换为base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()

            return f"data:image/png;base64,{image_base64}"

        except Exception as e:
            print(f"生成图谱图片失败: {e}")
            return None

    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """获取会话数据"""
        if session_id not in self.graphs:
            return None

        graph_data = self.graphs[session_id]
        return {
            "session_id": session_id,
            "triples": graph_data["triples"],
            "entities": list(graph_data["entities"]),
            "history": graph_data["history"],
            "stats": {
                "total_entities": len(graph_data["entities"]),
                "total_triples": len(graph_data["triples"]),
                "total_history": len(graph_data["history"])
            }
        }

    def clear_session(self, session_id: str):
        """清除会话数据"""
        if session_id in self.graphs:
            del self.graphs[session_id]

    def export_triples(self, session_id: str, format: str = "json") -> Dict[str, Any]:
        """导出三元组"""
        if session_id not in self.graphs:
            return None

        graph_data = self.graphs[session_id]

        if format == "json":
            return {
                "format": "json",
                "data": {
                    "triples": graph_data["triples"],
                    "metadata": {
                        "export_time": datetime.datetime.now().isoformat(),
                        "total_triples": len(graph_data["triples"]),
                        "total_entities": len(graph_data["entities"])
                    }
                }
            }
        elif format == "csv":
            csv_lines = ["subject,predicate,object,source"]
            for triple in graph_data["triples"]:
                csv_lines.append(
                    f'{triple["subject"]},{triple["predicate"]},{triple["object"]},"{triple.get("source", "")}"')

            return {
                "format": "csv",
                "data": "\n".join(csv_lines)
            }

        return None


# 全局知识图谱管理器
kg_manager = KnowledgeGraphManager()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/test_connection', methods=['POST'])
def test_connection():
    """测试API连接"""
    data = request.json
    api_key = data.get('api_key')
    api_secret = data.get('api_secret')

    if not api_key or not api_secret:
        return jsonify({"success": False, "error": "API密钥和密钥不能为空"})

    kg_manager.set_api_credentials(api_key, api_secret)
    result = kg_manager.spark_api.test_connection()

    if result.get("success"):
        session['api_key'] = api_key
        session['api_secret'] = api_secret

    return jsonify(result)


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """提问并构建知识图谱"""
    data = request.json
    question = data.get('question')
    session_id = data.get('session_id')
    visualize = data.get('visualize', True)

    if not question:
        return jsonify({"success": False, "error": "问题不能为空"})

    # 从session获取API密钥
    api_key = session.get('api_key')
    api_secret = session.get('api_secret')

    if not api_key or not api_secret:
        return jsonify({"success": False, "error": "请先配置API密钥"})

    kg_manager.set_api_credentials(api_key, api_secret)

    result = kg_manager.process_question(question, session_id, visualize)

    return jsonify(result)


@app.route('/api/get_graph', methods=['GET'])
def get_graph():
    """获取知识图谱"""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"success": False, "error": "缺少session_id"})

    data = kg_manager.get_session_data(session_id)
    if not data:
        return jsonify({"success": False, "error": "会话不存在"})

    return jsonify({"success": True, "data": data})


@app.route('/api/export', methods=['GET'])
def export_data():
    """导出数据"""
    session_id = request.args.get('session_id')
    format = request.args.get('format', 'json')

    if not session_id:
        return jsonify({"success": False, "error": "缺少session_id"})

    result = kg_manager.export_triples(session_id, format)
    if not result:
        return jsonify({"success": False, "error": "导出失败"})

    return jsonify({"success": True, **result})


@app.route('/api/clear', methods=['POST'])
def clear_session():
    """清除会话"""
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({"success": False, "error": "缺少session_id"})

    kg_manager.clear_session(session_id)
    return jsonify({"success": True, "message": "会话已清除"})


@app.route('/api/new_session', methods=['GET'])
def new_session():
    """创建新会话"""
    session_id = str(uuid.uuid4())
    return jsonify({"success": True, "session_id": session_id})


@app.route('/api/example_questions', methods=['GET'])
def get_example_questions():
    """获取示例问题"""
    examples = [
        "什么是人工智能？",
        "机器学习有哪些主要类型？",
        "北京有哪些著名景点？",
        "Python编程语言有什么特点？",
        "乔布斯创建了哪些公司？",
        "太阳系有哪些行星？",
        "深度学习和神经网络有什么关系？",
        "中国的四大发明是什么？",
        "什么是区块链技术？",
        "介绍一下量子计算的基本概念"
    ]
    return jsonify({"success": True, "examples": examples})


@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory('static', filename)


if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

    print("启动机械臂智能问答系统...")
    print("访问地址: http://localhost:5000")
    print("API文档:")
    print("  GET  /api/new_session          - 创建新会话")
    print("  POST /api/test_connection      - 测试API连接")
    print("  POST /api/ask                  - 提问")
    print("  POST /api/clear                - 清空会话")
    print("  GET  /api/export?format=json   - 导出数据")
    print("  GET  /api/example_questions    - 获取示例问题")

    app.run(debug=True, host='0.0.0.0', port=5000)