from setuptools import setup, find_packages

setup(
    name="autoglm-scheduler",
    version="0.1.0",
    description="多设备定时任务调度器，基于 Open-AutoGLM",
    author="Your Name",
    author_email="your@email.com",
    url="https://github.com/你的用户名/AutoGLM-Scheduler",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "apscheduler>=3.10.0",
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
        "rich>=13.0.0",
        "click>=8.1.0",
    ],
    extras_require={
        "web": [
            "fastapi>=0.104.0",
            "uvicorn>=0.24.0",
            "jinja2>=3.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "autoglm-scheduler=autoglm_scheduler.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
