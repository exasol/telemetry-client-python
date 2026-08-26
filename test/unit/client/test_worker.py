import queue
import time
from unittest import mock

from exasol.telemetry.client import *
from exasol.telemetry.client.setup import setup
from exasol.telemetry.client import (
    config,
    protocol,
    worker,
)


def test_stop_worker_doing_nothing_without_worker():
    worker.stop_worker(False)


def test_track_not_init(telemetry_reset):
    worker.track("test-product", "0.1", "feature")

    assert not setup(disable=True)
    worker.track("test-product", "0.1", "feature")


def test_clear_expired_features():
    ts = protocol.get_current_ts()
    data = {
        # last value should be cleared away
        "f1": [ts - 10, ts, ts - worker.MAX_DATA_KEEP_SECONDS - 1],
        # this feature's data is fresh enough, should be kept
        "f2": [ts - 5, ts],
        # this feature should be cleared entirely
        "f3": [
            ts - worker.MAX_DATA_KEEP_SECONDS - 1,
            ts - worker.MAX_DATA_KEEP_SECONDS - 2,
        ],
    }
    worker.clear_expired_features(data, ts)
    assert data["f1"] == [ts - 10, ts]
    assert data["f2"] == [ts - 5, ts]
    assert "f3" not in data


@mock.patch("requests.post")
def test_track(post_mock: mock.MagicMock, telemetry_reset, telemetry_unset_ci, telemetry_unset_disable):
    post_mock.return_value = mock.MagicMock(status_code=200)

    worker.track("test", "0.1", "feature1")
    worker.track("test", "0.1", "feature2")
    shutdown(flush_buffers=True)
    post_mock.assert_called_once()


def test_deadline_queue_deadline():
    q = worker.WorkerDeadlineQueue(queue.Queue())
    assert q.deadline_expired()
    q.set_deadline(0.2)
    assert not q.deadline_expired()
    assert q.seconds_to_deadline() > 0.0
    time.sleep(1)
    assert q.deadline_expired()


def test_send_features_not_conf():
    assert config.get() is None
    assert worker.send_features("prod", "ver", {})
    assert worker.send_features("prod", "ver", {"f": [1]})


def test_send_features_wrong_endpoint(telemetry_reset, caplog):
    caplog.set_level("DEBUG")
    assert setup(endpoint="http://non-existent-domain.weird", disable=False)
    assert not worker.send_features("prod", "ver", {"f": [1]})
    assert "Features send error" in caplog.text
    assert "Name or service not known" in caplog.text


# Make sure that first buffer is sent quickly after the initialization
@mock.patch("requests.post", return_value=mock.MagicMock(status_code=200))
def test_worker_proc_sent_quick(
    mock_post: mock.MagicMock, telemetry_reset, telemetry_unset_ci, telemetry_unset_disable
):
    track("product", "ver", "test")
    time.sleep(worker.DATA_SEND_FIRST_INTERVAL_SECONDS * 2)
    shutdown(flush_buffers=False)
    mock_post.assert_called_once()


# Make sure that features are not sent if not enabled
@mock.patch("requests.post")
def test_worker_proc_not_sent_when_disabled(
    mock_post: mock.MagicMock, telemetry_reset, telemetry_unset_ci, telemetry_unset_disable
):
    assert not setup(disable=True)
    assert config.was_setup()
    assert not config.was_enabled()
    track("test", "0.1", "test-feature")
    shutdown(flush_buffers=True)

    mock_post.assert_not_called()


@mock.patch("exasol.telemetry.client.worker.send_features")
def test_worker_proc_no_send(mock_send_features: mock.MagicMock):
    msg_queue = queue.Queue()
    msg_queue.put(worker.WorkerMessage.make_track("prod", "ver", "f1"))
    msg_queue.put(worker.WorkerMessage.make_terminate())

    worker.worker_proc(msg_queue)
    mock_send_features.assert_not_called()


@mock.patch("exasol.telemetry.client.worker.send_features", return_value=True)
def test_worker_proc_send_success(mock_send_features: mock.MagicMock):
    msg_queue = queue.Queue()
    msg_queue.put(worker.WorkerMessage.make_track("prod", "ver", "f1"))
    msg_queue.put(worker.WorkerMessage.make_send_buffers())
    msg_queue.put(worker.WorkerMessage.make_terminate())

    worker.worker_proc(msg_queue)
    mock_send_features.assert_called_once()


# imitate send error - send_features returns false, so clear_expired_features
# should be called
@mock.patch("exasol.telemetry.client.worker.clear_expired_features")
@mock.patch("exasol.telemetry.client.worker.send_features", return_value=False)
def test_worker_proc_send_fail(
    mock_send_features: mock.MagicMock, mock_clear_expired_features: mock.MagicMock
):
    msg_queue = queue.Queue()
    msg_queue.put(worker.WorkerMessage.make_track("prod", "ver", "f1"))
    msg_queue.put(None)
    msg_queue.put(worker.WorkerMessage.make_terminate())

    worker.worker_proc(msg_queue)
    mock_send_features.assert_called_once()
    mock_clear_expired_features.assert_called_once()
