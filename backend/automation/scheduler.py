import threading
import time
import uuid
from datetime import datetime
from typing import Optional


class Scheduler:
    def __init__(self):
        self.tasks = {}
        self.lock = threading.Lock()
        self.running = True

        self.worker = threading.Thread(
            target=self._worker,
            daemon=True
        )
        self.worker.start()

    def add_reminder(
        self,
        message: str,
        run_at: str
    ):
        """
        run_at format:
        YYYY-MM-DD HH:MM:SS
        """

        try:
            scheduled_time = datetime.strptime(
                run_at,
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            return {
                "success": False,
                "message": "Invalid date format. Use YYYY-MM-DD HH:MM:SS.",
                "error": "InvalidDateFormat"
            }

        if scheduled_time <= datetime.now():
            return {
                "success": False,
                "message": "Reminder time must be in the future.",
                "error": "PastTime"
            }

        task_id = str(uuid.uuid4())[:8]

        task = {
            "id": task_id,
            "type": "reminder",
            "message": message,
            "run_at": scheduled_time,
            "status": "scheduled"
        }

        with self.lock:
            self.tasks[task_id] = task

        return {
            "success": True,
            "message": f"Reminder scheduled for {run_at}.",
            "data": {
                "task_id": task_id,
                "message": message,
                "run_at": run_at,
                "status": "scheduled"
            }
        }

    def list_tasks(self):
        with self.lock:
            tasks = []

            for task in self.tasks.values():
                item = task.copy()
                item["run_at"] = item["run_at"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                tasks.append(item)

            return {
                "success": True,
                "message": f"Found {len(tasks)} scheduled tasks.",
                "data": tasks
            }

    def cancel_task(self, task_id: str):
        with self.lock:
            task = self.tasks.get(task_id)

            if not task:
                return {
                    "success": False,
                    "message": f"Task {task_id} was not found.",
                    "error": "TaskNotFound"
                }

            task["status"] = "cancelled"

        return {
            "success": True,
            "message": f"Task {task_id} cancelled.",
            "data": {
                "task_id": task_id,
                "status": "cancelled"
            }
        }

    def _worker(self):
        while self.running:
            now = datetime.now()

            with self.lock:
                for task in list(self.tasks.values()):

                    if task["status"] != "scheduled":
                        continue

                    if now >= task["run_at"]:
                        print(
                            f"\n🔔 JARVIS REMINDER: "
                            f"{task['message']}\n"
                        )

                        task["status"] = "completed"

            time.sleep(1)

    def stop(self):
        self.running = False


scheduler = Scheduler()