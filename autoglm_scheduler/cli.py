"""命令行接口"""

import os
import click
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

from autoglm_scheduler import Scheduler

# 加载环境变量
load_dotenv()

console = Console()


@click.group()
@click.option('--base-url', envvar='AUTOGLM_BASE_URL', default='http://localhost:8000/v1', help='模型API地址')
@click.option('--api-key', envvar='AUTOGLM_API_KEY', default='EMPTY', help='API密钥')
@click.option('--model', envvar='AUTOGLM_MODEL', default='autoglm-phone-9b', help='模型名称')
@click.pass_context
def main(ctx, base_url, api_key, model):
    """AutoGLM-Scheduler: 多设备定时任务调度器"""
    ctx.ensure_object(dict)
    ctx.obj['base_url'] = base_url
    ctx.obj['api_key'] = api_key
    ctx.obj['model'] = model


@main.command()
@click.argument('task')
@click.option('--device', '-d', help='指定设备ID')
@click.pass_context
def run(ctx, task, device):
    """立即执行一个任务"""
    scheduler = Scheduler(
        base_url=ctx.obj['base_url'],
        api_key=ctx.obj['api_key'],
        model=ctx.obj['model'],
    )
    
    # 自动检测设备
    if device:
        scheduler.add_device(device)
    else:
        # 尝试获取已连接设备
        import subprocess
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]
        for line in lines:
            if '\tdevice' in line:
                dev_id = line.split('\t')[0]
                scheduler.add_device(dev_id)
                break
    
    if scheduler._device_pool.total_count == 0:
        console.print("[red]错误: 没有可用的设备[/red]")
        return
    
    console.print(f"[blue]执行任务:[/blue] {task}")
    job_id = scheduler.add_job("cli_task", task)
    scheduler.start(blocking=True)


@main.command()
@click.argument('name')
@click.option('--task', '-t', required=True, help='任务描述')
@click.option('--cron', '-c', required=True, help='cron表达式')
@click.option('--device', '-d', help='指定设备ID')
def add(name, task, cron, device):
    """添加定时任务"""
    # 保存到配置文件
    import json
    config_file = os.path.expanduser('~/.autoglm_scheduler/jobs.json')
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    
    jobs = []
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
    
    jobs.append({
        'name': name,
        'task': task,
        'cron': cron,
        'device': device,
    })
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    console.print(f"[green]✅ 添加定时任务: {name}[/green]")
    console.print(f"   任务: {task}")
    console.print(f"   cron: {cron}")


@main.command()
def list():
    """列出所有定时任务"""
    import json
    config_file = os.path.expanduser('~/.autoglm_scheduler/jobs.json')
    
    if not os.path.exists(config_file):
        console.print("[yellow]暂无定时任务[/yellow]")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        jobs = json.load(f)
    
    if not jobs:
        console.print("[yellow]暂无定时任务[/yellow]")
        return
    
    table = Table(title="定时任务列表")
    table.add_column("名称", style="cyan")
    table.add_column("任务描述", style="white")
    table.add_column("Cron", style="green")
    table.add_column("设备", style="yellow")
    
    for job in jobs:
        table.add_row(
            job['name'],
            job['task'][:30] + '...' if len(job['task']) > 30 else job['task'],
            job['cron'],
            job.get('device', '自动')
        )
    
    console.print(table)


@main.command()
@click.option('--device', '-d', multiple=True, help='设备ID（可多次指定）')
@click.pass_context
def start(ctx, device):
    """启动调度服务"""
    import json
    
    scheduler = Scheduler(
        base_url=ctx.obj['base_url'],
        api_key=ctx.obj['api_key'],
        model=ctx.obj['model'],
    )
    
    # 添加设备
    if device:
        for d in device:
            scheduler.add_device(d)
    else:
        # 自动检测设备
        import subprocess
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]
        for line in lines:
            if '\tdevice' in line:
                dev_id = line.split('\t')[0]
                scheduler.add_device(dev_id)
    
    if scheduler._device_pool.total_count == 0:
        console.print("[red]错误: 没有可用的设备[/red]")
        return
    
    # 加载定时任务
    config_file = os.path.expanduser('~/.autoglm_scheduler/jobs.json')
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
        
        for job in jobs:
            scheduler.add_cron_job(
                name=job['name'],
                task=job['task'],
                cron=job['cron'],
                device_id=job.get('device'),
            )
    
    console.print("[green]🚀 调度服务已启动[/green]")
    console.print(f"   设备数量: {scheduler._device_pool.total_count}")
    console.print(f"   定时任务: {len(scheduler.list_cron_jobs())}")
    console.print("[dim]按 Ctrl+C 停止服务[/dim]")
    
    scheduler.start(blocking=True)


@main.command()
def devices():
    """列出已连接的设备"""
    import subprocess
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    
    table = Table(title="已连接设备")
    table.add_column("设备ID", style="cyan")
    table.add_column("状态", style="green")
    
    lines = result.stdout.strip().split('\n')[1:]
    for line in lines:
        if line.strip():
            parts = line.split('\t')
            if len(parts) >= 2:
                table.add_row(parts[0], parts[1])
    
    console.print(table)


@main.command()
@click.argument('name')
def remove(name):
    """移除定时任务"""
    import json
    config_file = os.path.expanduser('~/.autoglm_scheduler/jobs.json')
    
    if not os.path.exists(config_file):
        console.print("[red]任务不存在[/red]")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        jobs = json.load(f)
    
    new_jobs = [j for j in jobs if j['name'] != name]
    
    if len(new_jobs) == len(jobs):
        console.print(f"[red]任务 '{name}' 不存在[/red]")
        return
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(new_jobs, f, ensure_ascii=False, indent=2)
    
    console.print(f"[green]✅ 已移除任务: {name}[/green]")


if __name__ == '__main__':
    main()
