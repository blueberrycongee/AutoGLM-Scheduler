#!/usr/bin/env python3
"""
每日签到示例

演示如何使用 AutoGLM-Scheduler 设置每日自动签到任务。
"""

from autoglm_scheduler import Scheduler


def main():
    # 创建调度器
    # 使用智谱BigModel API（推荐）
    scheduler = Scheduler(
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="your-api-key",  # 替换为你的API Key
        model="autoglm-phone",
    )
    
    # 或者使用本地部署的模型
    # scheduler = Scheduler(
    #     base_url="http://localhost:8000/v1",
    #     model="autoglm-phone-9b",
    # )
    
    # 添加设备（替换为你的设备ID）
    scheduler.add_device("emulator-5554")  # 模拟器
    # scheduler.add_device("192.168.1.100:5555")  # WiFi连接的手机
    
    # ==================== 添加定时签到任务 ====================
    
    # 微博签到 - 每天早上8点
    scheduler.add_cron_job(
        name="微博签到",
        task="打开微博，找到签到入口完成每日签到",
        cron="0 8 * * *",
    )
    
    # 京东签到领京豆 - 每天早上8:30
    scheduler.add_cron_job(
        name="京东签到",
        task="打开京东APP，完成签到任务领取京豆",
        cron="30 8 * * *",
    )
    
    # 淘宝签到领金币 - 每天早上9点
    scheduler.add_cron_job(
        name="淘宝签到",
        task="打开淘宝，进入领金币页面完成签到",
        cron="0 9 * * *",
    )
    
    # 美团签到 - 每天中午12点
    scheduler.add_cron_job(
        name="美团签到",
        task="打开美团APP，完成每日签到",
        cron="0 12 * * *",
    )
    
    # B站签到 - 每天下午6点
    scheduler.add_cron_job(
        name="B站签到",
        task="打开bilibili，完成每日签到任务",
        cron="0 18 * * *",
    )
    
    # ==================== 设置任务完成回调 ====================
    
    def on_complete(job):
        if job.result.success:
            print(f"🎉 {job.name} 签到成功！")
        else:
            print(f"😢 {job.name} 签到失败: {job.result.error}")
    
    scheduler.on_job_complete(on_complete)
    
    # ==================== 启动调度器 ====================
    
    print("=" * 50)
    print("🚀 每日签到助手已启动")
    print("=" * 50)
    print("\n已配置的签到任务:")
    for job in scheduler.list_cron_jobs():
        print(f"  - {job.name}")
    print("\n按 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 阻塞运行
    scheduler.start(blocking=True)


if __name__ == "__main__":
    main()
