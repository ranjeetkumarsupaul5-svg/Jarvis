import threading
import time
from datetime import datetime

from backend.db import get_db_connection
#from backend.command import speak


class ReminderScheduler:
    """
    Background scheduler for JARVIS reminders.
    Checks SQLite every second and speaks due reminders.
    """

    def __init__(self):
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="JarvisReminderScheduler"
        )
        self.thread.start()

        print("Automation: Reminder scheduler started.")

    def stop(self):
        self.running = False

    def _run(self):
        while self.running:
            try:
                self._check_due_reminders()
            except Exception as e:
                print(f"Automation scheduler error: {e}")

            time.sleep(1)

    def _check_due_reminders(self):
        now = datetime.now()

        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM automations
                WHERE status = 'ACTIVE'
                  AND trigger_type = 'REMINDER'
                  AND last_run IS NULL
                ORDER BY id ASC
                """
            ).fetchall()

            for row in rows:
                automation_id = row["id"]
                name = row["name"]
                command = row["command"]

                # command stores ISO scheduled time:
                # __REMINDER_TIME__=2026-10-06T02:30:00
                if not command.startswith("__REMINDER_TIME__="):
                    continue

                try:
                    payload = command.split(
                        "__REMINDER_TIME__=",
                        1
                    )[1]

                    scheduled_time = datetime.fromisoformat(
                        payload
                    )

                except Exception:
                    continue

                if now >= scheduled_time:
                    self._fire_reminder(
                        automation_id,
                        name,
                        command,
                        conn
                    )

    def _fire_reminder(
        self,
        automation_id,
        name,
        command,
        conn
    ):
        try:
            from backend.command import speak
            reminder_text = name

            print(
                f"Automation: Reminder triggered -> "
                f"{reminder_text}"
            )

            # Mark first to prevent duplicate execution.
            conn.execute(
                """
                UPDATE automations
                SET last_run = CURRENT_TIMESTAMP,
                    status = 'DISABLED'
                WHERE id = ?
                """,
                (automation_id,)
            )

            conn.commit()

            # Voice notification
            speak(
                f"Reminder. {reminder_text}, sir."
            )

        except Exception as e:
            print(
                f"Automation reminder execution error: {e}"
            )


reminder_scheduler = ReminderScheduler()