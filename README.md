# AutoGLM-Scheduler

> 基于 Open-AutoGLM 的多设备定时任务调度器

## 项目背景

参加智谱「AutoGLM实战派」活动（2024.12.15 - 12.31），赛道一：灵感二创开发。

**现有问题**：Open-AutoGLM 官方只支持单次任务执行，缺少：
- ❌ 定时任务调度
- ❌ 多设备并发管理
- ❌ 任务队列和状态监控

**我们的方案**：封装一个易用的调度器，支持定时执行 + 多设备并发。

---

## 核心功能

### 1. 定时任务调度
```
每天早上 8:00 → 自动打开微博签到
每周五 14:00 → 自动抢购茅台
每月 1 号 → 自动领取会员权益
```

### 2. 多设备并发
```
手机1 → 执行任务A（微博签到）
手机2 → 执行任务B（京东签到）  ← 同时进行
手机3 → 执行任务C（淘宝签到）
```

### 3. 任务队列管理
```
任务多于设备时 → 自动排队
设备空闲时 → 自动分配下一个任务
任务失败时 → 可配置重试策略
```

### 4. 状态监控（可选）
```
Web 界面查看：
- 当前运行的任务
- 等待中的任务
- 历史执行记录
- 成功/失败统计
```

---

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/你的用户名/AutoGLM-Scheduler.git
cd AutoGLM-Scheduler

# 安装依赖
pip install -r requirements.txt

# 安装 Open-AutoGLM（如果还没装）
pip install git+https://github.com/zai-org/Open-AutoGLM.git
```

### 基础用法

```python
from autoglm_scheduler import Scheduler

# 创建调度器
scheduler = Scheduler(
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key="your-api-key",
    model="autoglm-phone"
)

# 添加设备
scheduler.add_device("emulator-5554")
scheduler.add_device("192.168.1.100:5555")

# 添加定时任务
scheduler.add_cron_job(
    name="微博签到",
    task="打开微博，完成每日签到任务",
    cron="0 8 * * *"  # 每天8点
)

scheduler.add_cron_job(
    name="京东签到", 
    task="打开京东，完成签到领京豆",
    cron="0 9 * * *"  # 每天9点
)

# 启动调度器
scheduler.start()
```

### 立即并发执行

```python
# 多个任务同时执行（自动分配到空闲设备）
results = scheduler.run_parallel([
    "打开微博签到",
    "打开京东签到",
    "打开淘宝领金币"
])

for result in results:
    print(f"{result.task}: {result.status}")
```

### 命令行用法

```bash
# 添加定时任务
python -m autoglm_scheduler add "微博签到" --task "打开微博签到" --cron "0 8 * * *"

# 查看任务列表
python -m autoglm_scheduler list

# 立即执行任务
python -m autoglm_scheduler run "打开微博签到"

# 启动调度服务
python -m autoglm_scheduler start
```

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AutoGLM-Scheduler                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  定时器      │    │  任务队列    │    │  设备池     │     │
│  │ APScheduler │ -> │ Task Queue  │ -> │ Device Pool │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                               │             │
│                                               ▼             │
│                                    ┌─────────────────┐     │
│                                    │  PhoneAgent x N │     │
│                                    │  (原有代码复用)   │     │
│                                    └─────────────────┘     │
│                                               │             │
│                          ┌────────────────────┼────────┐   │
│                          ▼                    ▼        ▼   │
│                        📱                   📱       📱    │
│                      设备1                 设备2     设备3  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 项目结构

```
AutoGLM-Scheduler/
├── README.md                 # 项目说明
├── requirements.txt          # 依赖
├── setup.py                  # 安装配置
│
├── autoglm_scheduler/        # 核心代码
│   ├── __init__.py
│   ├── scheduler.py          # 调度器主类
│   ├── device_pool.py        # 设备池管理
│   ├── task_queue.py         # 任务队列
│   ├── job.py                # 任务定义
│   └── cli.py                # 命令行接口
│
├── web/                      # Web监控界面（可选）
│   ├── app.py                # FastAPI 后端
│   └── templates/            # 前端页面
│
└── examples/                 # 使用示例
    ├── daily_checkin.py      # 每日签到示例
    └── multi_device.py       # 多设备示例
```

---

## 应用场景

### 薅羊毛自动化
- 每日签到（微博、京东、淘宝、美团...）
- 定时抢购（茅台、优惠券、限时折扣）
- 自动领取（会员权益、积分、红包）

### 批量运营
- 多账号同时发布内容
- 批量点赞/评论/转发
- 定时发送消息

### 自动化测试
- 多设备并行测试
- 定时回归测试
- 兼容性测试

---

## 与其他项目对比

| 功能 | Open-AutoGLM | AutoGLM-GUI | **AutoGLM-Scheduler** |
|------|--------------|-------------|----------------------|
| 单次任务执行 | ✅ | ✅ | ✅ |
| Web界面 | ❌ | ✅ | ✅ (可选) |
| 实时投屏 | ❌ | ✅ | ❌ |
| **定时调度** | ❌ | ❌ | ✅ |
| **多设备自动并发** | ❌ | ❌ | ✅ |
| **任务队列** | ❌ | ❌ | ✅ |
| **失败重试** | ❌ | ❌ | ✅ |

---

## 参考资料

- [Open-AutoGLM 官方仓库](https://github.com/zai-org/Open-AutoGLM)
- [APScheduler 文档](https://apscheduler.readthedocs.io/)
- [智谱 BigModel API](https://docs.bigmodel.cn/)

---

## License

MIT License
