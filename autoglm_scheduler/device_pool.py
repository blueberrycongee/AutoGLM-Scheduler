"""设备池管理模块"""

import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, Future


class DeviceStatus(Enum):
    """设备状态"""
    IDLE = "idle"          # 空闲
    BUSY = "busy"          # 忙碌
    OFFLINE = "offline"    # 离线
    ERROR = "error"        # 错误


@dataclass
class Device:
    """设备信息"""
    device_id: str
    status: DeviceStatus = DeviceStatus.IDLE
    current_job_id: Optional[str] = None
    last_used: Optional[datetime] = None
    total_jobs: int = 0
    success_jobs: int = 0
    failed_jobs: int = 0

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_jobs == 0:
            return 0.0
        return self.success_jobs / self.total_jobs


class DevicePool:
    """设备池：管理多个设备的并发执行"""
    
    def __init__(self, max_workers: int = 5):
        self._devices: Dict[str, Device] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def add_device(self, device_id: str) -> bool:
        """
        添加设备到池中
        
        Args:
            device_id: 设备ID（如 emulator-5554 或 192.168.1.100:5555）
            
        Returns:
            是否添加成功
        """
        with self._lock:
            if device_id in self._devices:
                return False
            
            # 检查设备是否在线
            if not self._check_device_online(device_id):
                print(f"警告: 设备 {device_id} 当前不在线，已添加但标记为离线")
                status = DeviceStatus.OFFLINE
            else:
                status = DeviceStatus.IDLE
            
            self._devices[device_id] = Device(device_id=device_id, status=status)
            return True
    
    def remove_device(self, device_id: str) -> bool:
        """移除设备"""
        with self._lock:
            if device_id not in self._devices:
                return False
            
            device = self._devices[device_id]
            if device.status == DeviceStatus.BUSY:
                return False  # 不能移除正在工作的设备
            
            del self._devices[device_id]
            return True
    
    def get_idle_device(self) -> Optional[str]:
        """
        获取一个空闲设备
        
        Returns:
            空闲设备的ID，如果没有则返回None
        """
        with self._lock:
            for device_id, device in self._devices.items():
                if device.status == DeviceStatus.IDLE:
                    return device_id
            return None
    
    def acquire_device(self, device_id: str, job_id: str) -> bool:
        """
        占用设备
        
        Args:
            device_id: 设备ID
            job_id: 任务ID
            
        Returns:
            是否成功占用
        """
        with self._lock:
            if device_id not in self._devices:
                return False
            
            device = self._devices[device_id]
            if device.status != DeviceStatus.IDLE:
                return False
            
            device.status = DeviceStatus.BUSY
            device.current_job_id = job_id
            device.last_used = datetime.now()
            return True
    
    def release_device(self, device_id: str, success: bool = True) -> bool:
        """
        释放设备
        
        Args:
            device_id: 设备ID
            success: 任务是否成功完成
            
        Returns:
            是否成功释放
        """
        with self._lock:
            if device_id not in self._devices:
                return False
            
            device = self._devices[device_id]
            device.status = DeviceStatus.IDLE
            device.current_job_id = None
            device.total_jobs += 1
            
            if success:
                device.success_jobs += 1
            else:
                device.failed_jobs += 1
            
            return True
    
    def list_devices(self) -> List[Device]:
        """列出所有设备"""
        with self._lock:
            return list(self._devices.values())
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """获取设备信息"""
        with self._lock:
            return self._devices.get(device_id)
    
    def refresh_status(self) -> None:
        """刷新所有设备状态"""
        with self._lock:
            for device_id, device in self._devices.items():
                if device.status != DeviceStatus.BUSY:
                    if self._check_device_online(device_id):
                        device.status = DeviceStatus.IDLE
                    else:
                        device.status = DeviceStatus.OFFLINE
    
    def _check_device_online(self, device_id: str) -> bool:
        """检查设备是否在线"""
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "get-state"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() == "device"
        except Exception:
            return False
    
    @property
    def idle_count(self) -> int:
        """空闲设备数量"""
        with self._lock:
            return sum(1 for d in self._devices.values() if d.status == DeviceStatus.IDLE)
    
    @property
    def busy_count(self) -> int:
        """忙碌设备数量"""
        with self._lock:
            return sum(1 for d in self._devices.values() if d.status == DeviceStatus.BUSY)
    
    @property
    def total_count(self) -> int:
        """总设备数量"""
        with self._lock:
            return len(self._devices)
    
    def shutdown(self) -> None:
        """关闭设备池"""
        self._executor.shutdown(wait=True)
