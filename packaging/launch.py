"""Entry point of the frozen executable.

With no arguments it opens the desktop window; with arguments it behaves as the command line:

    ADIT.exe                       desktop window
    ADIT.exe web                   local web server
    ADIT.exe gen spec.json out/    same as adit-gen
    ADIT.exe analyze out/run1      same as adit-analyze
    ADIT.exe report out/run1       same as adit-report
    ADIT.exe convert structure ... same as adit-convert
"""

import multiprocessing
import sys


def main() -> int:
    multiprocessing.freeze_support()
    commands = {"gen": "adit.cli", "analyze": "adit.analysis.cli", "web": "adit.web.server",
                "report": "adit.report", "convert": "adit.convert"}
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        import importlib

        module = importlib.import_module(commands[sys.argv[1]])
        sys.argv = [f"adit-{sys.argv[1]}"] + sys.argv[2:]
        return int(module.main() or 0)
    from adit.gui.app import main as gui_main

    return int(gui_main() or 0)


if __name__ == "__main__":
    sys.exit(main())
