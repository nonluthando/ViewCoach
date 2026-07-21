#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as error:
        raise ImportError(
            "Django could not be imported. Install the project dependencies and activate "
            "the virtual environment before running this command."
        ) from error

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
