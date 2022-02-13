"""
this script is used to run the `mkdocs build` command
automatically whenever the docs changes.
"""
import http.client as httplib
import logging
import os
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv
from pyrclone import Rclone
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger()

MONITOR_PATH = Path(os.environ.get("SYNC_PATH_LOCAL")).absolute()
logger.info("monitor directory: %s", MONITOR_PATH)

REMOVE_SYNC_PATH = os.environ.get("SYNC_PATH_REMOTE")
logger.info("remote sync path: %s", REMOVE_SYNC_PATH)

rclone = Rclone()
rclone.lsd(REMOVE_SYNC_PATH)


def internet_on():
    conn = httplib.HTTPSConnection("8.8.8.8", timeout=5)
    try:
        conn.request("HEAD", "/")
        return True
    except httplib.HTTPException:
        return False
    finally:
        conn.close()


class DocsWatchDog(FileSystemEventHandler):
    """put event Logs all the events captured."""

    def __init__(self):
        super().__init__()
        self.logger = logger
        self.last_modified = None

    def tick(self):
        """record current time"""
        self.last_modified = time.time()

    def on_moved(self, event):
        super().on_moved(event)

        what = "directory" if event.is_directory else "file"
        self.logger.info(
            "Moved %s: from %s to %s", what, event.src_path, event.dest_path
        )
        self.tick()

    def on_created(self, event):
        super().on_created(event)

        what = "directory" if event.is_directory else "file"
        self.logger.info("Created %s: %s", what, event.src_path)
        self.tick()

    def on_deleted(self, event):
        super().on_deleted(event)

        what = "directory" if event.is_directory else "file"
        self.logger.info("Deleted %s: %s", what, event.src_path)
        self.tick()

    def on_modified(self, event):
        super().on_modified(event)

        what = "directory" if event.is_directory else "file"
        self.logger.info("Modified %s: %s", what, event.src_path)
        self.tick()


if __name__ == "__main__":

    WAITING_TIME = 2 * 60  # wait for 2 minutes after last modified

    dir_e_handler = DocsWatchDog()
    observer = Observer()
    observer.schedule(dir_e_handler, MONITOR_PATH, recursive=True)
    observer.start()
    NO_CHANGE = True

    while not internet_on():
        logger.warning("internet is off, wait 10 seconds check again...")
        time.sleep(10)

    logger.warning("internet is on")

    try:
        while True:
            if (
                dir_e_handler.last_modified is not None
                and time.time() - dir_e_handler.last_modified >= WAITING_TIME
            ):
                NO_CHANGE = False

            if NO_CHANGE is False:
                try:
                    rclone.sync(source=MONITOR_PATH, dest=REMOVE_SYNC_PATH)
                    dir_e_handler.last_modified = None
                    NO_CHANGE = True
                except subprocess.CalledProcessError as e:
                    dir_e_handler.last_modified = time.time()
                    logger.error(e)
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt, waiting to exit...")

    except Exception as e:  # pylint: disable=broad-except
        logger.exception(e)
        logger.error("error occurred, waiting to exit...")
    finally:
        observer.stop()
        observer.join()
