"""
``python -m je_mail_thunder.studio``: start MailThunder Studio and print the address to open.
"""
import argparse
import sys
import webbrowser
from typing import List, Optional

from je_mail_thunder.core.project import project_mail
from je_mail_thunder.studio.api import StudioApi
from je_mail_thunder.studio.server import DEFAULT_PORT, StudioServer


def create_server(arguments: Optional[List[str]] = None) -> StudioServer:
    """
    :param arguments: the command line, without the program name; ``sys.argv`` by default
    :return: the server, bound but not serving yet
    """
    parser = argparse.ArgumentParser(
        prog="python -m je_mail_thunder.studio",
        description="MailThunder Studio: a local page for the account, templates, triggers, policies and logs.")
    parser.add_argument("--host", default="localhost",
                        help="loopback address to bind: localhost (the default) or 127.x.x.x")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port to bind (default: {DEFAULT_PORT})")
    parser.add_argument("--project", help="use the mail layer of this project directory; this runs its "
                                          "mail/config.py and mail/triggers.py")
    parser.add_argument("--no-browser", action="store_true", help="do not open the page in a browser")
    options = parser.parse_args(arguments)
    mail = project_mail(options.project) if options.project else None
    server = StudioServer(StudioApi(mail, options.project), options.host, options.port)
    server.open_browser = not options.no_browser
    return server


def main(arguments: Optional[List[str]] = None) -> int:
    """
    Serve MailThunder Studio until interrupted.

    :param arguments: the command line, without the program name
    :return: the exit status
    """
    server = create_server(arguments)
    print(f"MailThunder Studio: {server.url}", flush=True)
    print("Anyone with this address can use the mailbox while Studio runs. Ctrl+C stops it.", flush=True)
    if server.open_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("MailThunder Studio stopped.", flush=True)
    finally:
        server.server_close()
        server.api.mail.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
