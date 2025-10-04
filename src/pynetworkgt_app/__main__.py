"""Entry point for launching the PyNetworkGT standalone GUI."""

from __future__ import annotations

import sys

from pynetworkgt_app.gui import create_application


def main() -> int:
    app = create_application(sys.argv)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
