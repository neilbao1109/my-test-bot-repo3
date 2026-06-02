# mflux 本地生图 API 服务

基于 FastAPI + mflux 的本地 AI 图片生成服务（Flux 2），专为 Apple Silicon Mac 设计。

## 环境要求

- macOS（Apple Silicon：M1/M2/M3/M4）
- Python 3.10+
- [mflux](https://github.com/filipstrand/mflux)（通过 `uv tool install mflux` 安装）

## 安装

```bash
# 1. 安装 mflux（系统级工具）
uv tool install --upgrade mflux

# 2. 安装 Python 依赖
cd my-test-bot-repo3
pip install -r requirements.txt
```

## 启动

```bash
python server.py
```

服务默认运行在 `http://localhost:8100`。

## API 文档

### 1. 提交生图任务

```
POST /generate
```

**请求体：**
```json
{
  "prompt": "a cute cat sitting on a rainbow",
  "width": 1024,
  "height": 1024,
  "steps": 4,
  "seed": 42,
  "model": "flux2-klein-4b",
  "quantize": 8,
  "response_format": "url"
}
```

除 `prompt` 外均为可选参数。`response_format` 可选 `"url"`（默认）或 `"b64_json"`。`quantize` 支持 `4` 或 `8`。

**响应：**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

### 2. 查询任务状态

```
GET /task/{task_id}
```

**响应（生成中）：**
```json
{
  "task_id": "550e8400-...",
  "status": "generating"
}
```

**响应（完成）：**
```json
{
  "task_id": "550e8400-...",
  "status": "completed",
  "image_url": "/images/1717300000_550e8400.png"
}
```

如果请求时指定了 `response_format: "b64_json"`，响应中还会包含 `b64_json` 字段。

**响应（失败）：**
```json
{
  "task_id": "550e8400-...",
  "status": "failed",
  "error": "错误信息"
}
```

### 3. 服务状态

```
GET /status
```

**响应：**
```json
{
  "status": "idle",
  "queued": 0
}
```

或：
```json
{
  "status": "generating",
  "current_task": {
    "task_id": "550e8400-...",
    "prompt": "a cute cat..."
  },
  "queued": 2
}
```

### 4. 获取图片

```
GET /images/{filename}
```

直接返回 PNG 图片文件。

### 5. 生成历史

```
GET /history
```

返回最近 20 条生成记录（按时间倒序）：
```json
[
  {
    "task_id": "550e8400-...",
    "prompt": "a cute cat...",
    "params": { "width": 1024, "height": 1024, "steps": 20, "seed": 42, "model": "..." },
    "filename": "1717300000_550e8400.png",
    "created_at": "2026-06-02T06:45:00"
  }
]
```

## 配置

通过环境变量覆盖默认配置：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `MFLUX_PORT` | `8100` | 服务端口 |
| `MFLUX_MODEL` | `flux2-klein-4b` | 默认模型 |
| `MFLUX_WIDTH` | `1024` | 默认宽度 |
| `MFLUX_HEIGHT` | `1024` | 默认高度 |
| `MFLUX_STEPS` | `4` | 默认步数 |
| `MFLUX_QUANTIZE` | `8` | 量化级别（4 或 8） |
| `MFLUX_OUTPUT_DIR` | `./outputs` | 图片输出目录 |

## 注意事项

1. **串行生图**：由于硬件限制，任务按队列顺序串行执行，同一时间只有一个生图任务在运行
2. **mflux 安装**：mflux 是系统级工具，需通过 `uv tool install --upgrade mflux` 单独安装，不包含在 `requirements.txt` 中
3. **CLI 命令**：服务使用 `mflux-generate-flux2` 命令（Flux 2 专用），请确保 mflux 版本支持此命令
3. **仅限 Apple Silicon**：mflux 基于 MLX 框架，仅支持 Apple Silicon Mac
4. **历史记录**：生成历史存储在内存中，服务重启后会清空（图片文件仍保留在 outputs 目录）
5. **首次运行**：首次使用某个模型时，mflux 会自动下载模型权重，可能需要较长时间
