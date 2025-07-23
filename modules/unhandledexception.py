import sys
import traceback
import os
from modules.settings import instance as settings_manager
import logging
from modules.globalvars import RED, RESET
import modules.keys as k

settings = settings_manager.settings
logger = logging.getLogger("goober")


def handle_exception(exc_type, exc_value, exc_traceback, *, context=None):
    os.system("cls" if os.name == "nt" else "clear")

    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    with open(settings["splash_text_loc"], "r") as f:
        print("".join(f.readlines()))

    print(f"{RED}=====BEGINNING OF TRACEBACK====={RESET}")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print(f"{RED}========END OF TRACEBACK========{RESET}")
    print(f"{RED}{k.unhandled_exception()}{RESET}")

    if context:
        print(f"{RED}Context: {context}{RESET}")
