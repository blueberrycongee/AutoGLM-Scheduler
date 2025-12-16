"""调度器主模块"""

import threading
import time
from datetime import datetime
from typing import Optional, List, Callable
from concurrent.futures import ThreadPoolExecutor, Future

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from autoglm_scheduler.job import Job, JobStatus, JobResult
from autoglm_scheduler.device_pool import DevicePool, DeviceStatus
from autoglm_scheduler.task_queue import TaskQueue


class Scheduler:
    """
    AutoGLM 任务调度器
    
    支持定时任务调度和多设备并发执行。
    
    Example:
        >>> scheduler = Scheduler(
        ...     base_url="https://open.bigmodel.cn/api/paas/v4",
        ...     api_key="your-api-key"
        ... )
        >>> scheduler.add_device("emulator-5554")
        >>> scheduler.add_cron_job("签到", "打开微博签到", "0 8 * * *")
        >>> scheduler.start()
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "EMPTY",
        model: str = "autoglm-phone-9b",
        max_workers: int = 5,
        verbose: bool = True,
        mock_mode: bool = False,
    ):
        """
        初始化调度器
        
        Args:
            base_url: 模型API地址
            api_key: API密钥
            model: 模型名称
            max_workers: 最大并发数
            verbose: 是否打印详细日志
        """
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.verbose = verbose
        self.mock_mode = mock_mode
        
        if mock_mode and verbose:
            print("🧪 Mock 模式已启用 - 不会连接真实设备")
        
        # 核心组件
        self._device_pool = DevicePool(max_workers=max_workers)
        self._task_queue = TaskQueue()
        self._scheduler = BackgroundScheduler()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 状态
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 回调
        self._on_job_complete: Optional[Callable[[Job], None]] = None
    
    def add_device(self, device_id: str) -> bool:
        """
        添加设备
        
        Args:
            device_id: 设备ID（如 emulator-5554 或 192.168.1.100:5555）
            
        Returns:
            是否添加成功
        """
        # Mock 模式下强制设备在线
        success = self._device_pool.add_device(device_id, force_online=self.mock_mode)
        if success and self.verbose:
            print(f"✅ 添加设备: {device_id}")
        return success
    
    def remove_device(self, device_id: str) -> bool:
        """移除设备"""
        return self._device_pool.remove_device(device_id)
    
    def add_cron_job(
        self,
        name: str,
        task: str,
        cron: str,
        device_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> str:
        """
        添加定时任务
        
        Args:
            name: 任务名称
            task: 任务描述（发给AutoGLM的指令）
            cron: cron表达式（如 "0 8 * * *" 表示每天8点）
            device_id: 指定设备（None则自动分配）
            max_retries: 最大重试次数
            
        Returns:
            任务ID
        """
        job = Job(
            name=name,
            task=task,
            cron=cron,
            device_id=device_id,
            max_retries=max_retries,
        )
        
        # 添加到APScheduler
        self._scheduler.add_job(
            func=self._enqueue_job,
            trigger=CronTrigger.from_crontab(cron),
            args=[job],
            id=job.id,
            name=name,
        )
        
        if self.verbose:
            print(f"✅ 添加定时任务: {name} (cron: {cron})")
        
        return job.id
    
    def add_job(
        self,
        name: str,
        task: str,
        device_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> str:
        """
        添加立即执行的任务
        
        Args:
            name: 任务名称
            task: 任务描述
            device_id: 指定设备
            max_retries: 最大重试次数
            
        Returns:
            任务ID
        """
        job = Job(
            name=name,
            task=task,
            device_id=device_id,
            max_retries=max_retries,
        )
        
        self._enqueue_job(job, create_new=False)
        return job.id
    
    def run_parallel(self, tasks: List[str]) -> List[JobResult]:
        """
        并发执行多个任务
        
        Args:
            tasks: 任务描述列表
            
        Returns:
            执行结果列表
        """
        jobs = []
        for i, task in enumerate(tasks):
            job = Job(name=f"parallel_{i}", task=task)
            queued_job = self._enqueue_job(job, create_new=False)
            jobs.append(queued_job)
        
        # 等待所有任务完成
        while any(j.status in [JobStatus.PENDING, JobStatus.RUNNING] for j in jobs):
            time.sleep(0.5)
        
        return [j.result for j in jobs if j.result]
    
    def start(self, blocking: bool = True) -> None:
        """
        启动调度器
        
        Args:
            blocking: 是否阻塞主线程
        """
        if self._running:
            return
        
        self._running = True
        self._scheduler.start()
        
        # 启动工作线程
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        
        if self.verbose:
            print("🚀 调度器已启动")
            print(f"   设备数量: {self._device_pool.total_count}")
            print(f"   定时任务: {len(self._scheduler.get_jobs())}")
        
        if blocking:
            try:
                while self._running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
    
    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        self._scheduler.shutdown()
        self._executor.shutdown(wait=True)
        self._device_pool.shutdown()
        
        if self.verbose:
            print("🛑 调度器已停止")
    
    def _enqueue_job(self, job: Job, create_new: bool = True) -> Job:
        """将任务加入队列
        
        Args:
            job: 任务对象
            create_new: 是否创建新实例（定时任务需要，立即执行不需要）
            
        Returns:
            实际入队的 Job 对象
        """
        if create_new:
            # 定时任务每次触发需要新实例
            new_job = Job(
                name=job.name,
                task=job.task,
                cron=job.cron,
                device_id=job.device_id,
                max_retries=job.max_retries,
            )
        else:
            new_job = job
        
        self._task_queue.enqueue(new_job)
        if self.verbose:
            print(f"📥 任务入队: {new_job.name}")
        return new_job
    
    def _worker_loop(self) -> None:
        """工作循环：从队列取任务并分配给空闲设备"""
        while self._running:
            # 检查是否有空闲设备和待执行任务
            idle_device = self._device_pool.get_idle_device()
            if idle_device is None:
                time.sleep(0.1)
                continue
            
            job = self._task_queue.dequeue()
            if job is None:
                time.sleep(0.1)
                continue
            
            # 如果任务指定了设备，检查是否匹配
            target_device = job.device_id or idle_device
            
            # 尝试占用设备
            if not self._device_pool.acquire_device(target_device, job.id):
                # 设备被占用，放回队列
                self._task_queue.enqueue(job)
                continue
            
            # 提交任务执行
            if self.verbose:
                print(f"🏃 执行任务: {job.name} -> 设备: {target_device}")
            
            self._executor.submit(self._execute_job, job, target_device)
    
    def _execute_job(self, job: Job, device_id: str) -> None:
        """执行单个任务"""
        started_at = datetime.now()
        
        try:
            if self.mock_mode:
                # Mock 模式：模拟执行
                result_message, steps = self._mock_execute(job, device_id)
            else:
                # 真实模式：调用 PhoneAgent
                result_message, steps = self._real_execute(job, device_id)
            
            # 记录结果
            job.result = JobResult(
                success=True,
                message=result_message,
                started_at=started_at,
                finished_at=datetime.now(),
                device_id=device_id,
                steps=steps,
            )
            
            self._task_queue.complete(job.id, success=True)
            self._device_pool.release_device(device_id, success=True)
            
            if self.verbose:
                print(f"✅ 任务完成: {job.name} ({job.result.duration:.1f}s)")
            
        except Exception as e:
            # 执行失败
            job.result = JobResult(
                success=False,
                message=str(e),
                started_at=started_at,
                finished_at=datetime.now(),
                device_id=device_id,
                error=str(e),
            )
            
            # 尝试重试
            if job.retry_count < job.max_retries:
                self._task_queue.retry(job.id)
                self._device_pool.release_device(device_id, success=False)
                if self.verbose:
                    print(f"🔄 任务重试: {job.name} (第{job.retry_count}次)")
            else:
                self._task_queue.complete(job.id, success=False)
                self._device_pool.release_device(device_id, success=False)
                if self.verbose:
                    print(f"❌ 任务失败: {job.name} - {e}")
        
        # 触发回调
        if self._on_job_complete:
            self._on_job_complete(job)
    
    def _mock_execute(self, job: Job, device_id: str) -> tuple:
        """Mock 模式执行任务"""
        import random
        
        if self.verbose:
            print(f"🧪 [Mock] 模拟执行: {job.task[:30]}...")
        
        # 模拟执行时间 1-3 秒
        time.sleep(random.uniform(1, 3))
        
        # 模拟步数
        steps = random.randint(3, 10)
        
        if self.verbose:
            print(f"🧪 [Mock] 完成 {steps} 个步骤")
        
        return f"[Mock] 任务 '{job.name}' 模拟执行成功", steps
    
    def _real_execute(self, job: Job, device_id: str) -> tuple:
        """真实模式执行任务"""
        from phone_agent import PhoneAgent
        from phone_agent.agent import AgentConfig
        from phone_agent.model import ModelConfig
        
        model_config = ModelConfig(
            base_url=self.base_url,
            api_key=self.api_key,
            model_name=self.model,
        )
        
        agent_config = AgentConfig(
            device_id=device_id,
            verbose=self.verbose,
        )
        
        agent = PhoneAgent(
            model_config=model_config,
            agent_config=agent_config,
        )
        
        result_message = agent.run(job.task)
        return result_message, agent.step_count
    
    # ==================== 状态查询接口 ====================
    
    def list_devices(self) -> list:
        """列出所有设备"""
        return self._device_pool.list_devices()
    
    def list_pending_jobs(self) -> list:
        """列出等待中的任务"""
        return self._task_queue.list_pending()
    
    def list_running_jobs(self) -> list:
        """列出运行中的任务"""
        return self._task_queue.list_running()
    
    def list_history(self, limit: int = 20) -> list:
        """列出历史任务"""
        return self._task_queue.list_history(limit)
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务信息"""
        return self._task_queue.get_job(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """取消任务"""
        return self._task_queue.cancel(job_id)
    
    def list_cron_jobs(self) -> list:
        """列出所有定时任务"""
        return self._scheduler.get_jobs()
    
    def remove_cron_job(self, job_id: str) -> bool:
        """移除定时任务"""
        try:
            self._scheduler.remove_job(job_id)
            return True
        except Exception:
            return False
    
    def on_job_complete(self, callback: Callable[[Job], None]) -> None:
        """设置任务完成回调"""
        self._on_job_complete = callback
    
    @property
    def status(self) -> dict:
        """获取调度器状态"""
        return {
            "running": self._running,
            "devices": {
                "total": self._device_pool.total_count,
                "idle": self._device_pool.idle_count,
                "busy": self._device_pool.busy_count,
            },
            "jobs": {
                "pending": self._task_queue.pending_count,
                "running": self._task_queue.running_count,
            },
            "cron_jobs": len(self._scheduler.get_jobs()),
        }
