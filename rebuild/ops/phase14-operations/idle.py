"""Bounded test/restore helper with a normal, capability-free SIGTERM exit."""
import signal
import sys
import time

signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
time.sleep(1800)
