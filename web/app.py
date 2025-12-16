"""Web 监控界面"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from autoglm_scheduler import Scheduler


app = FastAPI(title="AutoGLM-Scheduler", description="多设备定时任务调度器")

# 全局调度器实例
scheduler: Optional[Scheduler] = None


def init_scheduler(
    base_url: str = "http://localhost:8000/v1",
    api_key: str = "EMPTY",
    model: str = "autoglm-phone-9b",
) -> Scheduler:
    """初始化调度器"""
    global scheduler
    scheduler = Scheduler(
        base_url=base_url,
        api_key=api_key,
        model=model,
        verbose=True,
    )
    return scheduler


# ==================== API 路由 ====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return get_dashboard_html()


@app.get("/api/status")
async def get_status():
    """获取调度器状态"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    return scheduler.status


@app.get("/api/devices")
async def get_devices():
    """获取设备列表"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    devices = scheduler.list_devices()
    return [
        {
            "device_id": d.device_id,
            "status": d.status.value,
            "current_job_id": d.current_job_id,
            "total_jobs": d.total_jobs,
            "success_rate": f"{d.success_rate * 100:.1f}%",
        }
        for d in devices
    ]


@app.post("/api/devices/{device_id}")
async def add_device(device_id: str):
    """添加设备"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    success = scheduler.add_device(device_id)
    return {"success": success}


@app.delete("/api/devices/{device_id}")
async def remove_device(device_id: str):
    """移除设备"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    success = scheduler.remove_device(device_id)
    return {"success": success}


@app.get("/api/jobs/pending")
async def get_pending_jobs():
    """获取待执行任务"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    jobs = scheduler.list_pending_jobs()
    return [j.to_dict() for j in jobs]


@app.get("/api/jobs/running")
async def get_running_jobs():
    """获取运行中任务"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    jobs = scheduler.list_running_jobs()
    return [j.to_dict() for j in jobs]


@app.get("/api/jobs/history")
async def get_history(limit: int = 20):
    """获取历史任务"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    jobs = scheduler.list_history(limit)
    return [j.to_dict() for j in jobs]


@app.get("/api/jobs/cron")
async def get_cron_jobs():
    """获取定时任务"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    jobs = scheduler.list_cron_jobs()
    return [
        {
            "id": j.id,
            "name": j.name,
            "next_run": str(j.next_run_time) if j.next_run_time else None,
        }
        for j in jobs
    ]


@app.post("/api/jobs")
async def add_job(name: str, task: str, cron: Optional[str] = None, device_id: Optional[str] = None):
    """添加任务"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    if cron:
        job_id = scheduler.add_cron_job(name, task, cron, device_id)
    else:
        job_id = scheduler.add_job(name, task, device_id)
    
    return {"job_id": job_id}


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """取消任务"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    success = scheduler.cancel_job(job_id)
    return {"success": success}


@app.post("/api/start")
async def start_scheduler():
    """启动调度器"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    scheduler.start(blocking=False)
    return {"success": True}


@app.post("/api/stop")
async def stop_scheduler():
    """停止调度器"""
    if scheduler is None:
        return {"error": "调度器未初始化"}
    
    scheduler.stop()
    return {"success": True}


# ==================== HTML 模板 ====================

def get_dashboard_html() -> str:
    """返回仪表盘HTML"""
    return """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoGLM-Scheduler</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        .card { @apply bg-white rounded-lg shadow-md p-6; }
        .btn { @apply px-4 py-2 rounded-lg font-medium transition-colors; }
        .btn-primary { @apply bg-blue-600 text-white hover:bg-blue-700; }
        .btn-danger { @apply bg-red-600 text-white hover:bg-red-700; }
        .btn-success { @apply bg-green-600 text-white hover:bg-green-700; }
        .status-idle { @apply text-green-600; }
        .status-busy { @apply text-yellow-600; }
        .status-offline { @apply text-gray-400; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="flex items-center justify-between mb-8">
            <div>
                <h1 class="text-3xl font-bold text-gray-800">AutoGLM-Scheduler</h1>
                <p class="text-gray-600">多设备定时任务调度器</p>
            </div>
            <div class="flex gap-4">
                <button onclick="startScheduler()" class="btn btn-success flex items-center gap-2">
                    <i data-lucide="play" class="w-4 h-4"></i> 启动
                </button>
                <button onclick="stopScheduler()" class="btn btn-danger flex items-center gap-2">
                    <i data-lucide="square" class="w-4 h-4"></i> 停止
                </button>
            </div>
        </div>
        
        <!-- Status Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="card">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">设备总数</p>
                        <p id="total-devices" class="text-3xl font-bold text-gray-800">0</p>
                    </div>
                    <i data-lucide="smartphone" class="w-10 h-10 text-blue-600"></i>
                </div>
            </div>
            <div class="card">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">空闲设备</p>
                        <p id="idle-devices" class="text-3xl font-bold text-green-600">0</p>
                    </div>
                    <i data-lucide="check-circle" class="w-10 h-10 text-green-600"></i>
                </div>
            </div>
            <div class="card">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">等待任务</p>
                        <p id="pending-jobs" class="text-3xl font-bold text-yellow-600">0</p>
                    </div>
                    <i data-lucide="clock" class="w-10 h-10 text-yellow-600"></i>
                </div>
            </div>
            <div class="card">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">运行中</p>
                        <p id="running-jobs" class="text-3xl font-bold text-blue-600">0</p>
                    </div>
                    <i data-lucide="loader" class="w-10 h-10 text-blue-600 animate-spin"></i>
                </div>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Devices -->
            <div class="card">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-bold text-gray-800">设备列表</h2>
                    <button onclick="showAddDevice()" class="btn btn-primary text-sm">
                        <i data-lucide="plus" class="w-4 h-4 inline"></i> 添加设备
                    </button>
                </div>
                <div id="devices-list" class="space-y-3">
                    <!-- 动态填充 -->
                </div>
            </div>
            
            <!-- Cron Jobs -->
            <div class="card">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-bold text-gray-800">定时任务</h2>
                    <button onclick="showAddJob()" class="btn btn-primary text-sm">
                        <i data-lucide="plus" class="w-4 h-4 inline"></i> 添加任务
                    </button>
                </div>
                <div id="cron-jobs-list" class="space-y-3">
                    <!-- 动态填充 -->
                </div>
            </div>
            
            <!-- Running Jobs -->
            <div class="card">
                <h2 class="text-xl font-bold text-gray-800 mb-4">运行中的任务</h2>
                <div id="running-jobs-list" class="space-y-3">
                    <!-- 动态填充 -->
                </div>
            </div>
            
            <!-- History -->
            <div class="card">
                <h2 class="text-xl font-bold text-gray-800 mb-4">执行历史</h2>
                <div id="history-list" class="space-y-3 max-h-96 overflow-y-auto">
                    <!-- 动态填充 -->
                </div>
            </div>
        </div>
    </div>
    
    <!-- Add Device Modal -->
    <div id="add-device-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center">
        <div class="bg-white rounded-lg p-6 w-96">
            <h3 class="text-xl font-bold mb-4">添加设备</h3>
            <input id="device-id-input" type="text" placeholder="设备ID (如 emulator-5554)" 
                   class="w-full px-4 py-2 border rounded-lg mb-4">
            <div class="flex justify-end gap-2">
                <button onclick="hideAddDevice()" class="btn bg-gray-200 hover:bg-gray-300">取消</button>
                <button onclick="addDevice()" class="btn btn-primary">添加</button>
            </div>
        </div>
    </div>
    
    <!-- Add Job Modal -->
    <div id="add-job-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center">
        <div class="bg-white rounded-lg p-6 w-96">
            <h3 class="text-xl font-bold mb-4">添加任务</h3>
            <input id="job-name-input" type="text" placeholder="任务名称" 
                   class="w-full px-4 py-2 border rounded-lg mb-3">
            <textarea id="job-task-input" placeholder="任务描述（发给AI的指令）" 
                      class="w-full px-4 py-2 border rounded-lg mb-3" rows="3"></textarea>
            <input id="job-cron-input" type="text" placeholder="Cron表达式 (如 0 8 * * *，留空则立即执行)" 
                   class="w-full px-4 py-2 border rounded-lg mb-4">
            <div class="flex justify-end gap-2">
                <button onclick="hideAddJob()" class="btn bg-gray-200 hover:bg-gray-300">取消</button>
                <button onclick="addJob()" class="btn btn-primary">添加</button>
            </div>
        </div>
    </div>

    <script>
        // 初始化 Lucide 图标
        lucide.createIcons();
        
        // 刷新数据
        async function refresh() {
            try {
                // 状态
                const status = await fetch('/api/status').then(r => r.json());
                if (!status.error) {
                    document.getElementById('total-devices').textContent = status.devices?.total || 0;
                    document.getElementById('idle-devices').textContent = status.devices?.idle || 0;
                    document.getElementById('pending-jobs').textContent = status.jobs?.pending || 0;
                    document.getElementById('running-jobs').textContent = status.jobs?.running || 0;
                }
                
                // 设备列表
                const devices = await fetch('/api/devices').then(r => r.json());
                if (!devices.error) {
                    const html = devices.map(d => `
                        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div class="flex items-center gap-3">
                                <i data-lucide="smartphone" class="w-5 h-5 status-${d.status}"></i>
                                <div>
                                    <p class="font-medium">${d.device_id}</p>
                                    <p class="text-sm text-gray-500">成功率: ${d.success_rate}</p>
                                </div>
                            </div>
                            <span class="px-2 py-1 text-xs rounded-full ${
                                d.status === 'idle' ? 'bg-green-100 text-green-800' :
                                d.status === 'busy' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-gray-100 text-gray-800'
                            }">${d.status}</span>
                        </div>
                    `).join('') || '<p class="text-gray-500 text-center">暂无设备</p>';
                    document.getElementById('devices-list').innerHTML = html;
                }
                
                // 定时任务
                const cronJobs = await fetch('/api/jobs/cron').then(r => r.json());
                if (!cronJobs.error) {
                    const html = cronJobs.map(j => `
                        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div>
                                <p class="font-medium">${j.name}</p>
                                <p class="text-sm text-gray-500">下次: ${j.next_run || '-'}</p>
                            </div>
                            <button onclick="removeJob('${j.id}')" class="text-red-600 hover:text-red-800">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    `).join('') || '<p class="text-gray-500 text-center">暂无定时任务</p>';
                    document.getElementById('cron-jobs-list').innerHTML = html;
                }
                
                // 运行中任务
                const running = await fetch('/api/jobs/running').then(r => r.json());
                if (!running.error) {
                    const html = running.map(j => `
                        <div class="p-3 bg-blue-50 rounded-lg">
                            <div class="flex items-center gap-2">
                                <i data-lucide="loader" class="w-4 h-4 animate-spin text-blue-600"></i>
                                <span class="font-medium">${j.name}</span>
                            </div>
                            <p class="text-sm text-gray-600 mt-1">${j.task}</p>
                        </div>
                    `).join('') || '<p class="text-gray-500 text-center">暂无运行中任务</p>';
                    document.getElementById('running-jobs-list').innerHTML = html;
                }
                
                // 历史
                const history = await fetch('/api/jobs/history?limit=10').then(r => r.json());
                if (!history.error) {
                    const html = history.map(j => `
                        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div class="flex items-center gap-2">
                                <i data-lucide="${j.status === 'success' ? 'check-circle' : 'x-circle'}" 
                                   class="w-4 h-4 ${j.status === 'success' ? 'text-green-600' : 'text-red-600'}"></i>
                                <span>${j.name}</span>
                            </div>
                            <span class="text-sm text-gray-500">${j.status}</span>
                        </div>
                    `).join('') || '<p class="text-gray-500 text-center">暂无历史记录</p>';
                    document.getElementById('history-list').innerHTML = html;
                }
                
                lucide.createIcons();
            } catch (e) {
                console.error('刷新失败:', e);
            }
        }
        
        // 启动/停止
        async function startScheduler() {
            await fetch('/api/start', { method: 'POST' });
            refresh();
        }
        
        async function stopScheduler() {
            await fetch('/api/stop', { method: 'POST' });
            refresh();
        }
        
        // 设备
        function showAddDevice() {
            document.getElementById('add-device-modal').classList.remove('hidden');
            document.getElementById('add-device-modal').classList.add('flex');
        }
        
        function hideAddDevice() {
            document.getElementById('add-device-modal').classList.add('hidden');
            document.getElementById('add-device-modal').classList.remove('flex');
        }
        
        async function addDevice() {
            const deviceId = document.getElementById('device-id-input').value.trim();
            if (!deviceId) return;
            
            await fetch(`/api/devices/${encodeURIComponent(deviceId)}`, { method: 'POST' });
            document.getElementById('device-id-input').value = '';
            hideAddDevice();
            refresh();
        }
        
        // 任务
        function showAddJob() {
            document.getElementById('add-job-modal').classList.remove('hidden');
            document.getElementById('add-job-modal').classList.add('flex');
        }
        
        function hideAddJob() {
            document.getElementById('add-job-modal').classList.add('hidden');
            document.getElementById('add-job-modal').classList.remove('flex');
        }
        
        async function addJob() {
            const name = document.getElementById('job-name-input').value.trim();
            const task = document.getElementById('job-task-input').value.trim();
            const cron = document.getElementById('job-cron-input').value.trim();
            
            if (!name || !task) return;
            
            const params = new URLSearchParams({ name, task });
            if (cron) params.append('cron', cron);
            
            await fetch(`/api/jobs?${params}`, { method: 'POST' });
            
            document.getElementById('job-name-input').value = '';
            document.getElementById('job-task-input').value = '';
            document.getElementById('job-cron-input').value = '';
            hideAddJob();
            refresh();
        }
        
        async function removeJob(jobId) {
            await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
            refresh();
        }
        
        // 初始化
        refresh();
        setInterval(refresh, 3000);  // 每3秒刷新
    </script>
</body>
</html>
"""


def run_web(
    host: str = "0.0.0.0",
    port: int = 8080,
    base_url: str = "http://localhost:8000/v1",
    api_key: str = "EMPTY",
    model: str = "autoglm-phone-9b",
):
    """启动 Web 服务"""
    init_scheduler(base_url, api_key, model)
    print(f"🌐 Web 界面已启动: http://localhost:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_web()
