"""Allow the package to be invoked directly: ``python -m pali_translator <args>``.

This thin shim imports the CLI entry-point and hands off control so that the
exit code returned by :func:`pali_translator.cli.main` is propagated correctly
to the shell.
"""

import sys

from .cli import main

sys.exit(main())
