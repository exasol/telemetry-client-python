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
    product_name: tt.Optional[protocol.ProductName] = None
    product_version: tt.Optional[protocol.ProductVersion] = None
    feature: tt.Optional[protocol.Feature] = None
    timestamp: tt.Optional[protocol.Timestamp] = None

    @classmethod
    def make_track(
        cls,
        product_name: protocol.ProductName,
        product_version: protocol.ProductVersion,
        feature: protocol.Feature,
    ) -> "WorkerMessage":
        return WorkerMessage(
            command=WorkerCommand.Track,
            product_name=product_name,
            product_version=product_version,
            feature=feature,
            timestamp=protocol.get_current_ts(),
        )

    @classmethod
    def make_send_buffers(cls) -> "WorkerMessage":
        return WorkerMessage(command=WorkerCommand.SendBuffers)

    @classmethod
    def make_terminate(cls) -> "WorkerMessage":
        return WorkerMessage(command=WorkerCommand.Terminate)


class WorkerDeadlineQueue:
    """
    Queue with deadline - moment in the future when we
    want to stop waiting for a message to arrive.
    """

    def __init__(self, msg_queue: queue.Queue):
        self._queue = msg_queue
        self._deadline_ts: tt.Optional[protocol.Timestamp] = None

    def set_deadline(self, seconds: float):
        self._deadline_ts = protocol.get_current_ts() + seconds

    def deadline_expired(self) -> bool:
        return (
            self._deadline_ts is None or protocol.get_current_ts() > self._deadline_ts
        )

    def seconds_to_deadline(self, now: tt.Optional[protocol.Timestamp] = None) -> float:
        """
        Get amount of seconds until deadline. If expired, return 0
        :param now: optional current time (used for testing)
        :return: count of seconds
        """
        if self._deadline_ts is None:
            return 0.0
        if now is None:
            now = protocol.get_current_ts()
        dt = self._deadline_ts - now
        return max(dt, 0.0)

    def get_msg(self) -> tt.Optional[WorkerMessage]:
        try:
            msg = self._queue.get(timeout=self.seconds_to_deadline())
            return msg if isinstance(msg, WorkerMessage) else None
        except queue.Empty:
            return None


DataPoolKey = tt.Tuple[protocol.ProductName, protocol.ProductVersion]


class DataPool:
    def __init__(self):
        self._pool: tt.Dict[DataPoolKey, protocol.Features] = {}

    def is_empty(self) -> bool:
        return not bool(self._pool)

    def send(self) -> bool:
        to_clear: tt.List[DataPoolKey] = []
        try:
            for key, features in self._pool.items():
                product, version = key
                if send_features(product, version, features):
                    to_clear.append(key)
                else:
                    # stop on first error
                    break
        finally:
            for key in to_clear:
                self._pool.pop(key)
        return self.is_empty()

    def clear_expired(self, now: protocol.Timestamp):
        to_clear: tt.List[DataPoolKey] = []
        for key, features in self._pool.items():
            clear_expired_features(features, now)
            if not features:
                to_clear.append(key)
        for key in to_clear:
            self._pool.pop(key)

    def append(
        self,
        product_name: tt.Optional[protocol.ProductName],
        product_version: tt.Optional[protocol.ProductVersion],
        feature: tt.Optional[protocol.Feature],
        timestamp: tt.Optional[protocol.Timestamp],
    ):
        # should never happen, but to make linter happy :shrug
        if (
            product_name is None
            or product_version is None
            or feature is None
            or timestamp is None
        ):
            return
        key = (product_name, product_version)
        features = self._pool.get(key)
        if features is None:
            features = collections.defaultdict(list)
            self._pool[key] = features
        features[feature].append(timestamp)


def send_features(
    product_name: protocol.ProductName,
    product_version: protocol.ProductVersion,
    features: protocol.Features,
) -> bool:
    """
    Internal method to send the accumulated data to endpoint.
    :param product_name: name of the product
    :param product_version: version of the product
    :param features: data to be sent
    :return: True if data was sent successfully,
    False if something happened, and we need to keep data for some time.
    """
    if not features:
        return True
    conf = config.get()
    if conf is None:
        return True
    message = protocol.Message.from_features(product_name, product_version, features)
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


def worker_proc(msg_queue: queue.Queue):
    """
    Worker procedure - consumes the queue, periodically sends the accumulated data.
    :param msg_queue: queue to consume
    """
    data_pool = DataPool()
    deadline_queue = WorkerDeadlineQueue(msg_queue)
    deadline_queue.set_deadline(DATA_SEND_FIRST_INTERVAL_SECONDS)

    while True:
        msg = deadline_queue.get_msg()
        if msg is None or msg.command == WorkerCommand.SendBuffers:
            # deadline has expired or we've asked to flush buffers
            if not data_pool.send():
                data_pool.clear_expired(protocol.get_current_ts())
        if deadline_queue.deadline_expired():
            deadline_queue.set_deadline(DATA_SEND_INTERVAL_SECONDS)
        if msg is None:
            continue
        if msg.command == WorkerCommand.Track:
            data_pool.append(
                msg.product_name, msg.product_version, msg.feature, msg.timestamp
            )
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


def _do_setup():
    from .setup import setup

    setup()


def track(
    product_name: protocol.ProductName,
    product_version: protocol.ProductVersion,
    feature: protocol.Feature,
):
    """
    Track feature usage.
    :param product_name: product name
    :param product_version: product version
    :param feature: string feature to track.
    """
    if not config.was_setup():
        _do_setup()
    if not config.was_enabled():
        return

    global _queue
    if _queue is not None:
        if _queue.not_full:
            _queue.put(WorkerMessage.make_track(product_name, product_version, feature))
