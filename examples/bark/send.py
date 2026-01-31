import os

from notify import Notify


def main() -> None:
    cfg = os.path.join(os.path.dirname(__file__), "notify.yaml")
    notify = Notify.from_config(cfg)
    notify.send("hello from notice (bark)", notify_level="info", type="text")


if __name__ == "__main__":
    main()
