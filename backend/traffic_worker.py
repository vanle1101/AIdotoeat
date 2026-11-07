"""Retired traffic worker.

This service remains as an inert compatibility entrypoint so an existing
systemd unit does not restart in a tight loop. It never opens pages, ad URLs,
or video URLs and never creates visitor or revenue events.
"""
from __future__ import annotations

from threading import Event
from typing import Optional


def run_traffic_cycle(stop_event: Optional[Event] = None) -> bool:
    print("[disabled] Automated traffic generation is retired.", flush=True)
    idle = stop_event or Event()
    while not idle.wait(3600):
        pass
    return False


if __name__ == "__main__":
    run_traffic_cycle()
