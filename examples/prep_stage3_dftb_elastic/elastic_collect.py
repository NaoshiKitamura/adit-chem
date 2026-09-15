#!/usr/bin/env python3
from pathlib import Path
from adit.elastic_setup import collect

print(collect(Path(__file__).resolve().parent)['summary'])
