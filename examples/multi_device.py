#!/usr/bin/env python3
"""
多设备并发示例

演示如何使用多台设备同时执行任务。
"""

from autoglm_scheduler import Scheduler


def main():
    # 创建调度器
    scheduler = Scheduler(
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="your-api-key",
        model="autoglm-phone",
    )
    
    # ==================== 添加多个设备 ====================
    
    # 添加3台设备
    scheduler.add_device("emulator-5554")      # 模拟器1
    scheduler.add_device("emulator-5556")      # 模拟器2
    scheduler.add_device("192.168.1.100:5555") # WiFi手机
    
    print(f"已添加 {scheduler._device_pool.total_count} 台设备")
    
    # ==================== 方式1: 并发执行多个任务 ====================
    
    print("\n📱 并发执行签到任务...")
    
    results = scheduler.run_parallel([
        "打开微博完成签到",
        "打开京东完成签到",
        "打开淘宝完成签到",
    ])
    
    print("\n执行结果:")
    for i, result in enumerate(results):
        status = "✅ 成功" if result.success else "❌ 失败"
        print(f"  任务{i+1}: {status} ({result.duration:.1f}s)")
    
    # ==================== 方式2: 指定设备执行 ====================
    
    print("\n📱 指定设备执行任务...")
    
    # 指定任务在特定设备上执行
    scheduler.add_cron_job(
        name="设备1专属任务",
        task="打开微信查看消息",
        cron="0 10 * * *",
        device_id="emulator-5554",  # 只在这台设备执行
    )
    
    # ==================== 方式3: 自动负载均衡 ====================
    
    print("\n📱 添加多个任务（自动分配设备）...")
    
    # 添加很多任务，调度器会自动分配到空闲设备
    tasks = [
        "打开支付宝查看余额",
        "打开美团查看订单",
        "打开大众点评搜索附近美食",
        "打开高德地图查看路况",
        "打开网易云音乐播放每日推荐",
    ]
    
    for i, task in enumerate(tasks):
        scheduler.add_job(f"任务{i+1}", task)
    
    print(f"已添加 {len(tasks)} 个任务到队列")
    print(f"等待执行: {scheduler._task_queue.pending_count}")
    
    # 启动调度器
    scheduler.start(blocking=True)


if __name__ == "__main__":
    main()
