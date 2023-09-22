import datetime
import threading
import time
from dataclasses import asdict, is_dataclass
from enum import Enum

import hivemind
import simplejson
from flask import Flask, render_template

import config
from health import fetch_health_state
from metrics import get_prometheus_metrics

logger = hivemind.get_logger(__name__)


class StateUpdaterThread(threading.Thread):
    def __init__(self, dht: hivemind.DHT, app: Flask, **kwargs):
        super().__init__(**kwargs)
        self.dht = dht
        self.app = app

        self.state_json = self.state_html = None
        self.ready = threading.Event()

    def run(self):
        while True:
            start_time = time.perf_counter()
            try:
                state_dict = fetch_health_state(self.dht)
                with self.app.app_context():
                    self.state_html = render_template("index.html", **state_dict)
                    self.prometheus_metrics = get_prometheus_metrics(state_dict)
                self.state_json = simplejson.dumps(state_dict, indent=2, ignore_nan=True, default=json_default)

                self.ready.set()
                logger.info(f"Fetched new state in {time.perf_counter() - start_time:.1f} sec")
            except Exception:
                logger.error("Failed to update state:", exc_info=True)

            delay = config.UPDATE_PERIOD - (time.perf_counter() - start_time)
            if delay < 0:
                logger.warning("Update took more than update_period, consider increasing it")
            time.sleep(max(delay, 0))


def json_default(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Enum):
        return value.name.lower()
    if isinstance(value, hivemind.PeerID):
        return value.to_base58()
    if isinstance(value, datetime.datetime):
        return value.timestamp()
    raise TypeError(f"Can't serialize {repr(value)}")
