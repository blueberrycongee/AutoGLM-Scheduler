"""任务定义模块"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class JobStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    SUCCESS = "success"      # 执行成功
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class JobResult:
    """任务执行结果"""
    success: bool
    message: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    device_id: Optional[str] = None
    steps: int = 0
    error: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """执行耗时（秒）"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


@dataclass
class Job:
    """任务定义"""
    name: str                          # 任务名称
    task: str                          # 任务描述（发给AutoGLM的指令）
    cron: Optional[str] = None         # cron表达式（定时任务）
    device_id: Optional[str] = None    # 指定设备（None则自动分配）
    retry_count: int = 0               # 重试次数
    max_retries: int = 3               # 最大重试次数
    timeout: int = 300                 # 超时时间（秒）
    
    # 内部字段
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: JobStatus = JobStatus.PENDING
    result: Optional[JobResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "task": self.task,
            "cron": self.cron,
            "device_id": self.device_id,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
        }
    
    def __repr__(self) -> str:
        return f"Job(id={self.id}, name={self.name}, status={self.status.value})"
