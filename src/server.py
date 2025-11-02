import os
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime

import psutil
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import bark
import maa
import scheduler
from settings import settings


def get_current_memory_usage():
    """
    获取当前进程的内存占用（单位：MB）
    """
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    # 返回驻留集大小（实际占用的物理内存）
    return memory_info.rss / 1024 / 1024  # 转换为MB


scheduler_instance = scheduler.Scheduler()
reports = deque(maxlen=16)


def run_maa():
    runner = maa.Runner()
    runner.run()

    report = runner.report()
    reports.append(report)
    bark.notify(settings().bark_key, "MAA 任务执行报告", report)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_instance.add_task(
        ["04:05", "12:05", "16:05", "22:05"],
        run_maa,
    )
    scheduler_instance.start()
    yield
    scheduler_instance.stop()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


@app.post("/api/pause")
def pause(seconds: int):
    print(f"Pause scheduler for {seconds} seconds")
    scheduler_instance.pause(seconds)
    return {"code": 0}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "memory_usage": f"{get_current_memory_usage():.3f} MB",
            "next_run_datetime": datetime.fromtimestamp(
                scheduler_instance.next_run_timestamp()
            ),
            "reports": [r for r in reports][::-1],
        },
    )
