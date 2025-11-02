import enum
import threading
import time
from datetime import datetime
from typing import Callable


def str2seconds(s: str):
    parts = [float(p) for p in s.split(":")]
    if len(parts) > 3:
        raise Exception("time format: XX:XX[:XX]")
    parts += [0, 0, 0]  # placeholder
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


class TaskState(enum.Enum):
    IDLE = enum.auto()
    RUNNING = enum.auto()


class Task:
    def __init__(self, schedule: list[str], func: Callable) -> None:
        self.schedule = sorted(map(str2seconds, schedule))
        self.schedule_delta = [
            self.schedule[i + 1] - self.schedule[i]
            for i in range(len(self.schedule) - 1)
        ]
        # 首尾时间距离：第二天的第一时间点 减去 今天的最后时间点
        self.schedule_delta.append(24 * 3600 + self.schedule[0] - self.schedule[-1])

        # 计算下次运行时间
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        self.next_run_timestamp = today.timestamp() + self.schedule[0]
        self.schedule_idx = 0
        while self.check(now.timestamp()):
            pass

        self.func = func

        self.state = TaskState.IDLE

    def check(self, now: float | None = None):
        if now is None:
            now = time.time()

        if self.next_run_timestamp <= now:
            self.next_run_timestamp += self.schedule_delta[self.schedule_idx]
            self.schedule_idx = (self.schedule_idx + 1) % len(self.schedule)
            return True
        else:
            return False

    def run(self):
        self.state = TaskState.RUNNING
        res = self.func()
        self.state = TaskState.IDLE
        return res


class Scheduler:
    def __init__(self) -> None:
        self.tasks: list[Task] = []

        self.pause_until = time.time()  # 暂停结束时间

        self.exit = False  # 线程退出标志位
        self.thread = threading.Thread(target=self.__thread)

    def start(self):
        self.thread.start()

    def stop(self):
        self.exit = True
        if self.thread.is_alive():
            self.thread.join(timeout=5)

    def __del__(self):
        self.stop()

    def add_task(self, schedule: list[str], func: Callable):
        self.tasks.append(Task(schedule, func))

    def pause(self, seconds: int):
        self.pause_until = time.time() + seconds

    def next_run_timestamp(self):
        task = min(self.tasks, key=lambda t: t.next_run_timestamp)
        return max(task.next_run_timestamp, self.pause_until)

    def __thread(self) -> None:
        while not self.exit:
            time.sleep(1)
            now = time.time()
            if now < self.pause_until:
                continue

            for task in self.tasks:
                if task.check(now):
                    task.run()  # TODO 在新线程运行
        print("exit scheduler thread")
