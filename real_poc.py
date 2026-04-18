#!/usr/bin/env python3
"""
Real Memvid POC for monday.com — Radar, April 15 2026
Tests: encode, search (keyword + NL), latency, incremental update, multi-source
"""

import time
import os
import tempfile
import json

# Suppress cv2 / Qt warnings
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["DISPLAY"] = ""

from memvid import MemvidEncoder, MemvidRetriever
