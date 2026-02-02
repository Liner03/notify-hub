import os

from notify import Notify


def main() -> None:
    cfg = os.path.join(os.path.dirname(__file__), "notify.yaml")
    notify = Notify.from_config(cfg)

    # Send plain text email
    notify.send("hello from notice (email)", notify_level="info", type="text")

    # Send HTML email
    html_content = """
    <html>
        <body>
            <h1>Notification</h1>
            <p>This is a <strong>HTML</strong> email from notice.</p>
        </body>
    </html>
    """
    notify.send(html_content, notify_level="info", type="html")


if __name__ == "__main__":
    main()
