# PathRAG Standalone Pipeline

这个目录提供一个独立的文档解析、知识图谱生成/导入、知识图谱查询的工程代码，可直接用本地文件进行测试。

## 依赖与环境

- 该工程复用仓库中的 PathRAG 实现。
- 大模型服务支持本地 OpenAI 兼容接口，需设置以下环境变量：
  - `OPENAI_API_BASE=http://<your-openai-compatible-host>/v1`
  - `OPENAI_API_KEY=your_key`

## 使用方式

### 解析本地文件

```bash
python -m kg_pipeline parse /path/to/file.pdf
```

### 文档入库并触发知识图谱生成

```bash
python -m kg_pipeline ingest /path/to/file.pdf --working-dir ./data
```

### 导出知识图谱（JSON）

```bash
python -m kg_pipeline graph --working-dir ./data
```

按实体名称过滤：

```bash
python -m kg_pipeline graph --working-dir ./data --entity "EntityName"
```

### 导入知识图谱到 Neo4j

```bash
python -m kg_pipeline neo4j-import \
  --working-dir ./data \
  --uri bolt://localhost:7687 \
  --username neo4j \
  --password password
```
