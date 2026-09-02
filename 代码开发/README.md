# 智能车间产品外观缺陷检测与报告系统

基于 **YOLOv8 深度学习 + FastAPI + Vue 3** 的工业产品外观图像自动缺陷检测与报告生成系统。
上传一张产品外观图像，系统自动完成：**图像预处理 → AI 缺陷检测 → 统计分析 → 标注图绘制 → 结构化报告生成 → 数据库存储**，并通过可视化看板展示检测结果与历史统计。

## ✨ 功能特性

- **自动缺陷检测**：YOLOv8 模型识别 6 类钢表面缺陷（裂纹、夹杂、斑块、麻点、氧化皮、划痕），GPU/CPU 自动切换
- **图像预处理**：等比缩放 640×640、CLAHE 自适应直方图增强、归一化
- **可视化标注**：检测框按缺陷类型着色，中文标签 + 置信度标注
- **结构化报告**：报告编号、缺陷明细表、统计汇总、检测结论、检测员信息（JSON 格式）
- **历史记录**：分页查询，支持按缺陷类型、日期范围筛选，完整报告抽屉查看
- **统计看板**：总检测数、合格率、今日检测数指标卡片；缺陷分布饼图、合格率仪表盘、近七天趋势折线图
- **前端交互**：拖拽上传、原图/结果图对比、悬停缺陷列表高亮对应检测框、点击图片放大
- **演示模式兜底**：未训练模型时自动切换模拟检测，系统始终可完整演示

## 🛠 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| 深度学习 | YOLOv8（ultralytics）+ PyTorch |
| 图像处理 | OpenCV + Pillow |
| 数据库 | SQLite + SQLAlchemy ORM |
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Axios |
| 测试 | pytest（内存 SQLite 隔离） |

## 📁 目录结构

```
代码开发/
├── backend/                        # 后端
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口（CORS/静态挂载/异常处理/健康检查）
│   │   ├── config.py               # Pydantic Settings 配置管理
│   │   ├── database.py             # 数据库引擎/会话/初始化
│   │   ├── models/                 # SQLAlchemy 模型（DetectionRecord）
│   │   ├── schemas/                # Pydantic 请求响应模型
│   │   ├── dao/                    # 数据访问层
│   │   ├── services/               # 业务逻辑层
│   │   ├── routers/                # API 路由（上传/记录/统计）
│   │   ├── algorithms/             # 核心算法（detector/preprocess/defect_mapping）
│   │   └── utils/                  # 文件处理与日志工具
│   ├── train/                      # 数据集转换 + 训练脚本
│   ├── tests/                      # pytest 自动化测试
│   ├── models/best.pt              # 训练好的模型（训练后生成）
│   ├── requirements.txt
│   └── run.py                      # 启动脚本
├── defect-detection-frontend/      # 前端（Vue 3 + Vite）
│   └── src/
│       ├── api/                    # axios 封装 + 接口定义
│       ├── views/                  # Dashboard 检测台 / History 历史记录
│       ├── components/             # UploadArea/ResultDisplay/StatisticsChart/RecordTable
│       └── router/                 # 路由配置
└── README.md
```

## 🌍 环境要求

- Python 3.10+（本项目在 3.13 验证通过）
- Node.js 18+（本项目在 24 验证通过）
- 可选：NVIDIA GPU（无 GPU 自动回退 CPU 推理；训练推荐 GPU）

## 📦 安装步骤

### 1. 后端

```bash
cd backend
python -m venv .venv                          # 创建虚拟环境
.venv\Scripts\python -m pip install -r requirements.txt
```

> GPU 用户注意：`pip install torch` 在 Windows 上默认装 CPU 版。
> 如需 GPU 加速，安装后执行：
> `.venv\Scripts\python -m pip install "torch==2.13.0+cu126" "torchvision==0.28.0+cu126" --index-url https://download.pytorch.org/whl/cu126`

### 2. 前端

```bash
cd defect-detection-frontend
npm install
```

## 🚀 启动步骤

### 方式一：一键启动（推荐）

双击项目根目录的 **`启动系统.bat`**，自动完成后端、前端启动并打开浏览器。
关闭弹出的两个黑色窗口即可停止系统。

### 方式二：手动两条命令

**第一步：启动后端**（终端 1）

```bash
cd backend
.venv\Scripts\python run.py
# 后端运行于 http://localhost:8000，接口文档 http://localhost:8000/docs
```

**第二步：启动前端**（终端 2）

```bash
cd defect-detection-frontend
npm run dev
# 前端运行于 http://localhost:5173，浏览器打开即可使用
```

> 前端通过 Vite 代理把 `/api`、`/uploads`、`/results` 转发到后端 8000 端口，无需额外配置。
> 注意：通过 Claude Code 等工具启动的服务会随会话结束而关闭；用一键启动脚本或手动开终端启动则不受影响。

## 🔬 模型训练（可选，训练前系统自动处于演示模式）

数据集：NEU-DET 钢表面缺陷数据集（1800 张，6 类），位于 `C:\Users\asus\Desktop\data\NEU\NEU-DET`。

```bash
cd backend
.venv\Scripts\python train\convert_neu.py     # 1. 数据转换（VOC XML -> YOLO 格式）
.venv\Scripts\python train\train.py           # 2. 训练（RTX 4050 约 20-40 分钟）
```

训练完成后 `best.pt` 自动复制到 `backend/models/best.pt`，重启后端即切换为真实模型推理。

**本项目当前模型指标**（NEU-DET 验证集 360 张，yolov8n 训练 60+80 轮）：

| 指标 | 数值 |
|---|---|
| 总体 mAP50 | **77.7%** |
| 划痕 / 斑块 / 夹杂 | 95% / 93% / 77% |
| 氧化皮 / 麻点 | 约 75% / 70% |
| 裂纹（线状细纹，最难类） | 45%（偶尔与麻点混淆） |

> 提示：训练时若卡住不出结果，请确认 `train.py` 中 `workers=0`（Windows 上多进程数据加载会卡死）。
> 想继续提升精度可运行 `.venv\Scripts\python train\train.py --epochs 80`（自动从 best.pt 断点续训）。

## 📡 API 接口列表

统一返回格式：`{code, msg, data}`，`code=0` 表示成功。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查（服务与模型状态） |
| POST | `/api/upload` | 上传图像并检测（multipart，file 字段，≤10MB，jpg/jpeg/png/bmp） |
| GET | `/api/records` | 分页查询记录（page/size/defect_type/start_date/end_date） |
| GET | `/api/records/{id}` | 单条记录详情（含完整报告） |
| GET | `/api/statistics/overview` | 统计总览（总数/合格率/缺陷分布/近7天趋势） |
| GET | `/api/statistics/report/{id}` | 单次检测的完整结构化报告 |

### 使用示例（curl）

```bash
# 健康检查
curl http://localhost:8000/api/health

# 上传检测（用数据集里的缺陷图试效果最佳）
curl -X POST http://localhost:8000/api/upload -F "file=@C:/Users/asus/Desktop/data/NEU/NEU-DET/IMAGES/crazing_1.jpg"

# 查询最近 10 条记录
curl "http://localhost:8000/api/records?page=1&size=10"

# 按缺陷类型筛选
curl "http://localhost:8000/api/records?defect_type=%E8%A3%82%E7%BA%B9"

# 统计总览
curl http://localhost:8000/api/statistics/overview
```

## 🧪 运行测试

```bash
cd backend
.venv\Scripts\python -m pytest tests -v
```

测试使用内存 SQLite + 假检测器，不依赖训练好的模型，秒级完成。
覆盖：健康检查、上传检测全流程、分页/筛选查询、统计接口、报告接口、
检测器返回格式（含真实模型测试，有 best.pt 时自动启用）、DAO 增删查统计、预处理与报告生成。

## 📝 检测结论规则

- 未检出任何缺陷 → **合格**（绿色）
- 检出 ≥1 处缺陷 → **不合格**（红色），并在报告中列出缺陷明细与严重程度分布

## ❓ 常见问题

1. **上传后提示"演示模式"？** 未找到 `backend/models/best.pt`，系统用模拟检测结果演示。运行训练脚本生成模型后重启后端即可。
2. **首次上传很慢？** 首次调用会加载模型并预热（GPU 约几秒），之后每次检测都在 1 秒内。
3. **提示文件格式错误？** 仅支持 jpg/jpeg/png/bmp，大小不超过 10MB。
4. **GPU 不可用？** 确认已安装 CUDA 版 PyTorch（见安装步骤），且 NVIDIA 驱动已装好。
