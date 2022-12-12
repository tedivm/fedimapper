import asyncio
import inspect
import logging
import multiprocessing as mp
import signal
import time
from queue import Empty, Full
from typing import Any, Callable, Dict

import psutil
from pydantic import BaseSettings


class Settings(BaseSettings):
    num_processes: int = 2
    max_queue_size: int = 300
    prevent_requeuing_time: float = 300
    empty_queue_sleep_time: float = 1.00
    full_queue_sleep_time: float = 5.00
    queue_interaction_timeout: float = 0.01
    graceful_shutdown_timeout: float = 0.5
    lookup_block_size: int = 10


def get_named_settings(name):
    class QueueSettings(Settings):
        class Config:
            env_prefix = f"QUEUE_{name.upper()}_"

    return QueueSettings()


class QueueBuilder:
    def __init__(self, queue, settings, writer):
        self.i = 0
        self.queue = queue
        self.settings = settings
        self.last_queued = {}
        self.writer = writer

    async def populate(self, max=50):
        self.clean_history()
        successful_adds = 0
        count = min(int(self.settings.max_queue_size * 0.8) - self.queue.qsize(), max)
        blocksize = min(self.settings.lookup_block_size, count)
        if count <= 0:
            logging.debug("Skipping queue population due to max queue size.")
            return False
        try:
            async for id in self.writer(desired=blocksize):
                if id is None or id is False:
                    logging.debug(f"Returning False {id}")
                    return False
                if self.add_to_queue(id):
                    logging.debug(f"Added {id} to queue.")
                    successful_adds += 1
                    if successful_adds >= max:
                        return True
        except Full:
            logging.debug("Queue has reached max size.")
            return False

    def add_to_queue(self, id):
        if id in self.last_queued:

            logging.debug(f"ID {id} is in last_queued")
            logging.debug(time.time())
            logging.debug(self.last_queued[id] + self.settings.prevent_requeuing_time)

            if self.last_queued[id] + self.settings.prevent_requeuing_time > time.time():
                logging.debug(f"Skipping {id}: added too recently.")
                return False
        logging.debug(f"Adding {id} to queue.")
        self.last_queued[id] = time.time()
        self.queue.put(id, True, self.settings.queue_interaction_timeout)
        return True

    def clean_history(self):
        self.last_queued = {
            k: v for k, v in self.last_queued.items() if v + self.settings.prevent_requeuing_time > time.time()
        }

    def close(self):
        pass


class QueueRunner(object):
    def __init__(self, name: str, reader: Callable, writer: Callable, settings: Dict[str, Any] | None = None, **kwargs):
        self.name = name
        self.settings = settings if settings else get_named_settings(name)
        self.reader = reader
        self.writer = writer
        self.worker_launches = 0

    async def main(self):
        with mp.Manager() as manager:
            import_queue = manager.Queue(self.settings.max_queue_size)
            shutdown_event = manager.Event()
            queue_builder = QueueBuilder(import_queue, self.settings, self.writer)
            processes = []

            # Inline function to implicitly pass through shutdown_event.
            def shutdown(a=None, b=None):
                if a != None:
                    logging.debug(f"Signal {a} caught.")

                # Send shutdown signal to all processes.
                shutdown_event.set()

                # Graceful shutdown- wait for children to shut down.
                if a == 15 or a == None:
                    logging.debug("Gracefully shutting down child processes.")
                    shutdown_start = time.time()
                    while len(psutil.Process().children()) > 0:
                        if time.time() > (shutdown_start + self.settings.graceful_shutdown_timeout):
                            break
                        time.sleep(0.05)

                # Kill any remaining processes directly, not counting on variables.
                remaining_processes = psutil.Process().children()
                if len(remaining_processes) > 0:
                    logging.debug("Terminating remaining child processes.")
                    for process in remaining_processes:
                        process.terminate()

            # Set shutdown function as signal handler for SIGINT and SIGTERM.
            signal.signal(signal.SIGINT, shutdown)
            signal.signal(signal.SIGTERM, shutdown)

            # Now start actual script.
            try:
                while not shutdown_event.is_set():

                    # Prune dead processes
                    processes = [x for x in processes if x.is_alive()]

                    # Bring process list up to size
                    while len(processes) < self.settings.num_processes:
                        process = self.launch_process(import_queue, shutdown_event)
                        processes.append(process)
                        process.start()

                    # Populate Queue
                    if not await queue_builder.populate():
                        logging.debug("Queue unable to populate: sleeping scheduler.")
                        time.sleep(self.settings.full_queue_sleep_time)
                    else:
                        # SMall sleep between populate attempts to prevent CPU/database pegging.
                        time.sleep(0.05)
            finally:
                shutdown()

    def launch_process(self, import_queue, shutdown_event):
        process = mp.Process(
            target=reader_process,
            args=(
                import_queue,
                shutdown_event,
                self.reader,
                self.settings.dict(),
            ),
        )
        process.name = f"worker_{self.worker_launches:03d}"
        self.worker_launches += 1
        logging.debug(f"Launching worker {process.name}")
        process.daemon = True
        return process


def reader_process(queue, shutdown_event, reader: Callable, settings: dict):
    PROCESS_NAME = mp.current_process().name
    while not shutdown_event.is_set() and mp.parent_process().is_alive():
        try:
            id = queue.get(True, settings["queue_interaction_timeout"])
            if id == "close":
                break
            if inspect.iscoroutinefunction(reader):
                asyncio.run(reader(id))
            else:
                reader(id)

        except Empty:
            logging.debug(f"{PROCESS_NAME} has no jobs to process, sleeping.")
            time.sleep(settings["empty_queue_sleep_time"])
            continue


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
    runner = QueueRunner("main", reader=reader_test, writer=writer_test)
    runner.main()
