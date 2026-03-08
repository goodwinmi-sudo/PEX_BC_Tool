import pty
import os
import sys

def read(fd):
    try:
        data = os.read(fd, 1024)
        print(data.decode("utf-8", errors="replace"), end="")
        return data
    except OSError:
        return b""

pty.spawn(["/google/bin/releases/corprun-cli/corprun", "init"], read)
