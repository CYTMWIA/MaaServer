import ctypes
import datetime
import json
import os
import time
import weakref

from asst.asst import Asst
from asst.utils import Message

from settings import settings

# 关卡开放日，1 表示周一，2 表示周二，以此类推，周日为 7
stage_open_weekdays = {
    "LS-6": [1, 2, 3, 4, 5, 6, 7],
    "CE-6": [2, 4, 6],
    "AP-5": [1, 4, 6],
    "CA-5": [2, 3, 5],
    "SK-5": [1, 3, 5, 6],
    "PR-A-1": [1, 4, 5],
    "PR-A-2": [1, 4, 5],
    "PR-B-1": [1, 2, 5, 6],
    "PR-B-2": [1, 2, 5, 6],
    "PR-C-1": [3, 4, 6],
    "PR-C-2": [3, 4, 6],
    "PR-D-1": [2, 3, 6],
    "PR-D-2": [2, 3, 6],
}


def today_weekday():
    now = datetime.datetime.now()
    weekday = now.weekday() + 1
    if now.hour < 4:  # 四点更新
        weekday -= 1
    if weekday == 0:
        weekday = 7
    return weekday


class Runner:
    def __init__(self) -> None:
        self._depot = {}  # 仓库

        self.current_sanity = -1  # 当前理智
        self.max_sanity = -1  # 最大理智

        self.fight_product = None  # 刷理智 目标产物
        self.fight_stage = None  # 刷理智 关卡

        self.last_task_ok = True

        self.report_lines = []

        self.maacore_log = (
            f"maacore/{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        )

        weakref.finalize(self, lambda obj: print(f"GC: {obj}"), str(self))

    def __report_line(self, s: str):
        print(s)
        self.report_lines.append(s)

    def report(self):
        return "\n".join(self.report_lines)

    @Asst.CallBackType
    @staticmethod
    def __callback(_msg, _details, _arg):
        py_obj_ptr = ctypes.cast(_arg, ctypes.POINTER(ctypes.py_object))
        self: Runner = py_obj_ptr.contents.value
        msg = Message(_msg)
        data = json.loads(_details.decode("utf-8"))

        if msg == Message.SubTaskExtraInfo and data["what"] == "DepotInfo":
            self._depot.clear()
            arkplanner_data = json.loads(data["details"]["arkplanner"]["data"])
            for item in arkplanner_data["items"]:
                self._depot[item["name"]] = item["have"]
        elif msg == Message.SubTaskExtraInfo and data["what"] == "SanityBeforeStage":
            self.current_sanity = data["details"]["current_sanity"]
            self.max_sanity = data["details"]["max_sanity"]
        elif msg == Message.TaskChainCompleted:
            self.last_task_ok = True
        elif msg == Message.TaskChainError:
            self.last_task_ok = False

        os.makedirs(os.path.dirname(self.maacore_log), exist_ok=True)
        with open(self.maacore_log, "a", encoding="utf-8") as f:
            now = datetime.datetime.now()
            line = f"[{now.strftime('%Y/%m/%d %H:%M:%S')}] {msg} {data}\n"
            f.write(line)

    def __select_fight_stage(self):
        demands = [
            # 活动关卡
            ("糖组", -1, "OS-7"),
            # 芯片：三个六星干员升级到精一
            # 芯片组：两个六星干员升级到精二
            ("重装芯片", 5 * 3, "PR-A-1"),
            ("重装芯片组", 8 * 2, "PR-A-2"),
            ("医疗芯片", 5 * 3, "PR-A-1"),
            ("医疗芯片组", 8 * 2, "PR-A-2"),
            ("狙击芯片", 5 * 3, "PR-B-1"),
            ("狙击芯片组", 8 * 2, "PR-B-2"),
            ("术师芯片", 5 * 3, "PR-B-1"),
            ("术师芯片组", 8 * 2, "PR-B-2"),
            ("先锋芯片", 5 * 3, "PR-C-1"),
            ("先锋芯片组", 8 * 2, "PR-C-2"),
            ("辅助芯片", 5 * 3, "PR-C-1"),
            ("辅助芯片组", 8 * 2, "PR-C-2"),
            ("近卫芯片", 5 * 3, "PR-D-1"),
            ("近卫芯片组", 8 * 2, "PR-D-2"),
            ("特种芯片", 5 * 3, "PR-D-1"),
            ("特种芯片组", 8 * 2, "PR-D-2"),
            # 蓝书：两个六星技能升级到专三
            ("技巧概要·卷3", 43 * 2, "CA-5"),
            # 兜底，不要浪费理智
            ("红票", -1, "AP-5"),
            ("龙门币", -1, "CE-6"),
            ("经验书", -1, "LS-6"),
        ]
        today = today_weekday()
        for d in demands:
            product, min_amount, stage = d
            # 数量是否足够
            current_amount = self._depot.get(product, 0)
            if 0 <= min_amount and min_amount <= current_amount:
                continue
            # 关卡是否开放（若开放表中不存在关卡则默认开放）
            open_weekdays = stage_open_weekdays.get(stage, None)
            if (open_weekdays is None) or (today in open_weekdays):
                self.fight_product = product
                self.fight_stage = stage
                return

    def __run_task(self, name: str, params: dict = {}):
        self.maa.append_task(name, params)
        self.maa.start()
        while self.maa.running():
            time.sleep(1)
        # print(f"Task '{name}' Result: {'OK' if self.last_task_ok else 'FAILED'}")
        return self.last_task_ok

    def __run(self):
        self.__report_line(f"运行时间：{datetime.datetime.now()}")
        self.__report_line(f"MAA 版本：{self.maa.get_version()}")

        self.maa.connect(settings().adb_path, settings().adb_addr, "MuMuEmulator12")

        self.__run_task(
            "StartUp",
            {
                "client_type": "Official",
                "start_game_enabled": True,
            },
        )

        self.__run_task(
            "Recruit",
            {"times": 1, "refresh": True, "select": [3, 4], "confirm": [3, 4]},
        )

        drones = "PureGold" if today_weekday() <= 5 else "Money"
        self.__report_line(f"基建无人机用途：{drones}")
        self.__run_task(
            "Infrast",
            {
                "facility": [
                    "Mfg",
                    "Trade",
                    "Control",
                    "Power",
                    "Reception",
                    "Office",
                    "Dorm",
                    "Processing",
                    "Training",
                ],
                "drones": drones,
                "dorm_trust_enabled": True,
            },
        )

        # 不论剿灭成功失败，都要执行第二次刷理智
        ok = self.__run_task(
            "Fight",
            {
                "stage": "Annihilation",
                "series": 0,
                "expiring_medicine": 65535,
                "client_type": "Official",
            },
        )
        self.__report_line(f"刷剿灭: {'成功' if ok else '失败'}")

        self.__run_task("Depot")
        self.__select_fight_stage()
        self.__report_line(f"刷理智目标: {self.fight_product} {self.fight_stage}")

        ok = self.__run_task(
            "Fight",
            {
                "stage": self.fight_stage,
                "series": 0,
                "expiring_medicine": 65535,
                "client_type": "Official",
            },
        )
        self.__report_line(f"刷理智: {'成功' if ok else '失败'}")
        self.__report_line(f"剩余理智: {self.current_sanity}/{self.max_sanity}")

        self.__run_task(
            "Mall",
            {
                "buy_first": ["招聘许可"],
                "blacklist": ["加急许可", "家具零件"],
                "force_shopping_if_credit_full": True,
                "credit_fight": True,
                "formation_index": 4,
            },
        )
        self.__report_line("信用：TODO")

        self.__run_task("Award", {"award": True, "mail": True})

        self.__run_task("CloseDown", {"client_type": "Official"})

    def run(self):
        Asst.load(settings().maacore_path)

        py_obj_ref = ctypes.py_object(weakref.proxy(self))
        arg = ctypes.cast(ctypes.pointer(py_obj_ref), ctypes.c_void_p)
        self.maa = Asst(callback=self.__callback, arg=arg)

        res = self.__run()

        del self.maa  # 提前销毁 Asst 对象，避免其生命期长于 Runner
        return res
