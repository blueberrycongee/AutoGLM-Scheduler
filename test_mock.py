#!/usr/bin/env python3
"""Mock 模式测试脚本"""

from autoglm_scheduler import Scheduler

def main():
    print("=" * 50)
    print("🧪 AutoGLM-Scheduler Mock 模式测试")
    print("=" * 50)
    
    # 创建调度器（Mock 模式）
    scheduler = Scheduler(mock_mode=True)
    
    # 添加虚拟设备
    scheduler.add_device("mock-device-001")
    scheduler.add_device("mock-device-002")
    
    # 设置任务完成回调
    def on_complete(job):
        print(f"\n📋 任务回调: {job.name}")
        print(f"   状态: {job.status.value}")
        if job.result:
            print(f"   结果: {job.result.message}")
            print(f"   耗时: {job.result.duration:.1f}s")
            print(f"   步数: {job.result.steps}")
    
    scheduler.on_job_complete(on_complete)
    
    # 添加立即执行的任务
    print("\n📥 添加测试任务...")
    scheduler.add_job("微博签到", "打开微博完成每日签到")
    scheduler.add_job("京东签到", "打开京东APP领取京豆")
    scheduler.add_job("淘宝签到", "打开淘宝签到领金币")
    
    # 启动调度器（非阻塞）
    print("\n🚀 启动调度器...")
    scheduler.start(blocking=False)
    
    # 等待任务完成
    import time
    print("\n⏳ 等待任务执行...")
    time.sleep(15)
    
    # 查看执行历史
    print("\n" + "=" * 50)
    print("📊 执行历史")
    print("=" * 50)
    for job in scheduler.list_history():
        status_icon = "✅" if job.status.value == "success" else "❌"
        print(f"{status_icon} {job.name}: {job.status.value}")
    
    # 停止调度器
    scheduler.stop()
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    main()
