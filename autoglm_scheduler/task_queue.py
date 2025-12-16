"""任务队列模块"""

import threading
from collections import deque
from typing import Optional, List, Callable
from datetime import datetime

from autoglm_scheduler.job import Job, JobStatus


class TaskQueue:
    """任务队列：管理待执行的任务"""
    
    def __init__(self):
        self._queue: deque[Job] = deque()
        self._running: dict[str, Job] = {}  # job_id -> Job
        self._history: List[Job] = []
        self._lock = threading.Lock()
        self._max_history = 100  # 最大历史记录数
    
    def enqueue(self, job: Job) -> None:
        """
        将任务加入队列
        
        Args:
            job: 任务对象
        """
        with self._lock:
            job.status = JobStatus.PENDING
            self._queue.append(job)
    
    def dequeue(self) -> Optional[Job]:
        """
        从队列取出一个任务
        
        Returns:
            任务对象，如果队列为空则返回None
        """
        with self._lock:
            if not self._queue:
                return None
            
            job = self._queue.popleft()
            job.status = JobStatus.RUNNING
            self._running[job.id] = job
            return job
    
    def peek(self) -> Optional[Job]:
        """查看队首任务（不取出）"""
        with self._lock:
            if not self._queue:
                return None
            return self._queue[0]
    
    def complete(self, job_id: str, success: bool, message: str = "") -> bool:
        """
        标记任务完成
        
        Args:
            job_id: 任务ID
            success: 是否成功
            message: 结果消息
            
        Returns:
            是否成功标记
        """
        with self._lock:
            if job_id not in self._running:
                return False
            
            job = self._running.pop(job_id)
            job.status = JobStatus.SUCCESS if success else JobStatus.FAILED
            
            # 添加到历史记录
            self._history.append(job)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            
            return True
    
    def retry(self, job_id: str) -> bool:
        """
        重试失败的任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            是否成功加入重试队列
        """
        with self._lock:
            if job_id not in self._running:
                return False
            
            job = self._running.pop(job_id)
            
            if job.retry_count >= job.max_retries:
                job.status = JobStatus.FAILED
                self._history.append(job)
                return False
            
            job.retry_count += 1
            job.status = JobStatus.PENDING
            self._queue.appendleft(job)  # 优先重试
            return True
    
    def cancel(self, job_id: str) -> bool:
        """
        取消任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            是否成功取消
        """
        with self._lock:
            # 从等待队列中取消
            for i, job in enumerate(self._queue):
                if job.id == job_id:
                    job.status = JobStatus.CANCELLED
                    del self._queue[i]
                    self._history.append(job)
                    return True
            
            # 运行中的任务不能直接取消
            return False
    
    def list_pending(self) -> List[Job]:
        """列出等待中的任务"""
        with self._lock:
            return list(self._queue)
    
    def list_running(self) -> List[Job]:
        """列出运行中的任务"""
        with self._lock:
            return list(self._running.values())
    
    def list_history(self, limit: int = 20) -> List[Job]:
        """列出历史任务"""
        with self._lock:
            return self._history[-limit:]
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务信息"""
        with self._lock:
            # 先找运行中的
            if job_id in self._running:
                return self._running[job_id]
            
            # 再找等待中的
            for job in self._queue:
                if job.id == job_id:
                    return job
            
            # 最后找历史
            for job in self._history:
                if job.id == job_id:
                    return job
            
            return None
    
    @property
    def pending_count(self) -> int:
        """等待中的任务数量"""
        with self._lock:
            return len(self._queue)
    
    @property
    def running_count(self) -> int:
        """运行中的任务数量"""
        with self._lock:
            return len(self._running)
    
    def clear(self) -> int:
        """
        清空等待队列
        
        Returns:
            清空的任务数量
        """
        with self._lock:
            count = len(self._queue)
            for job in self._queue:
                job.status = JobStatus.CANCELLED
                self._history.append(job)
            self._queue.clear()
            return count
