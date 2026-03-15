"""Allow the package to be run as a module: python -m pali_translator <args>"""

import sys

from .cli import main

sys.exit(main())
