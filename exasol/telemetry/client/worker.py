import collections
import dataclasses
import enum
import json
import logging
import queue
import threading
import typing as tt

import requests

from exasol.telemetry.client import (
    config,
    protocol,
)

MAX_QUEUE_CAPACITY = 10

# requests' timeout value
SEND_TIMEOUT_SECONDS = 30

# how long in seconds to wait before the first batch send
DATA_SEND_FIRST_INTERVAL_SECONDS = 0.5

# how often we try to send the accumulated buffers
DATA_SEND_INTERVAL_SECONDS = 5 * 60

# for how long we keep features in buffers before removing them
MAX_DATA_KEEP_SECONDS = 60 * 60

log = logging.getLogger("worker")
_worker: tt.Optional[threading.Thread] = None
_queue: tt.Optional[queue.Queue] = None


class WorkerCommand(enum.Enum):
    Track = 0
    SendBuffers = 1
    Terminate = 2


@dataclasses.dataclass(frozen=True)
class WorkerMessage:
    command: WorkerCommand
    feature: tt.Optional[protocol.Feature]
    timestamp: tt.Optional[protocol.Timestamp]

    @classmethod
    def make_track(cls, feature: protocol.Feature) -> "WorkerMessage":
        return WorkerMessage(
            command=WorkerCommand.Track,
            feature=feature,
            timestamp=protocol.get_current_ts(),
        )

    @classmethod
    def make_send_buffers(cls) -> "WorkerMessage":
        return WorkerMessage(
            command=WorkerCommand.SendBuffers, feature=None, timestamp=None
        )

    @classmethod
    def make_terminate(cls) -> "WorkerMessage":
        return WorkerMessage(
            command=WorkerCommand.Terminate, feature=None, timestamp=None
        )


def send_features(features: protocol.Features) -> bool:
    """
    Internal method to send the accumulated data to endpoint.
    :param features: data to be sent
    :return: True if data was sent successfully,
    False if something happened and we need to keep data for some time.
    """
    if not features:
        return True
    conf = config.get()
    if conf is None:
        return True
    message = protocol.Message.from_features(features)
    try:
        url = conf.endpoint
        data = json.dumps(message.to_json())
        res = requests.post(url, data, timeout=SEND_TIMEOUT_SECONDS)
        if res.status_code != 200:
            log.debug("Feature send error: %s", str(res))
            return False
        return True
    except requests.exceptions.RequestException as e:
        log.debug("Features send error: %s", str(e))
    return False


def clear_expired_features(features: protocol.Features, now: protocol.Timestamp):
    """
    Discard expired features from buffers.
    :param features: dict with features and timestamps.
    :param now: current timestamp
    """
    keys_to_clear = []
    for key in features.keys():
        new_data = [v for v in features[key] if now - v < MAX_DATA_KEEP_SECONDS]
        if not new_data:
            keys_to_clear.append(key)
        else:
            features[key] = new_data
    for key in keys_to_clear:
        features.pop(key)


def get_msg_timeout(
    next_sent_ts: protocol.Timestamp, now: tt.Optional[protocol.Timestamp] = None
) -> protocol.Timestamp:
    """
    Get amount of seconds to wait for new message.
    :param next_sent_ts: when next data push is planned
    :param now: optional argument to redefine the current timestamp. Used for testing
    :return: Amount of seconds to sleep before the next send attempt.
    """
    if now is None:
        now = protocol.get_current_ts()
    dt = next_sent_ts - now
    # if interval has expired, return 0
    return max(dt, 0)


def worker_proc(msg_queue: queue.Queue):
    """
    Worker procedure - consumes the queue, periodically sends the accumulated data.
    :param msg_queue: queue to consume
    """
    data: protocol.Features = collections.defaultdict(list)
    next_sent_ts = protocol.get_current_ts() + DATA_SEND_FIRST_INTERVAL_SECONDS

    while True:
        try:
            msg = msg_queue.get(timeout=get_msg_timeout(next_sent_ts))
        except queue.Empty:
            msg = None
        now = protocol.get_current_ts()

        # if interval has expired, or we have an explicit send request, send the data
        if now > next_sent_ts or (
            msg is not None and msg.command == WorkerCommand.SendBuffers
        ):
            if send_features(data):
                data.clear()
            else:
                clear_expired_features(data, now)
            next_sent_ts = now + DATA_SEND_INTERVAL_SECONDS

        if not isinstance(msg, WorkerMessage):
            continue
        if msg.command == WorkerCommand.Track:
            if msg.feature is not None and msg.timestamp is not None:
                data[msg.feature].append(msg.timestamp)
        elif msg.command == WorkerCommand.Terminate:
            return


def start_worker() -> bool:
    """
    Initializes the worker process if needed.
    In case of error, raises TelemetryError exception.
    :return: True if worker has started, False if already started.
    """
    global _worker, _queue

    if _worker is not None:
        return False
    if not config.was_enabled():
        return False
    _queue = queue.Queue(maxsize=MAX_QUEUE_CAPACITY)
    _worker = threading.Thread(target=worker_proc, args=(_queue,))
    _worker.start()
    return True


def stop_worker(flush_buffers: bool):
    """
    Gracefully stops the worker process.
    :param flush_buffers: if True, we'll try to send the buffers (if any),
    otherwise, we'll just shut down the worker process.
    """
    global _worker, _queue

    if _worker is None or _queue is None:
        return
    if flush_buffers:
        _queue.put(WorkerMessage.make_send_buffers())
    _queue.put(WorkerMessage.make_terminate())
    _worker.join()
    _worker = None
    _queue = None


def track(category: str, product_version: str, feature: protocol.Feature):
    """
    Track feature usage. Library has to be initialized with `setup()` call.
    :param category: product name
    :param product_version: product version
    :param feature: string feature to track.
    """
    if not config.was_enabled():
        return

    global _queue
    if _queue is not None:
        if _queue.not_full:
            _queue.put(WorkerMessage.make_track(feature))
