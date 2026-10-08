"""Permite ejecutar el CLI con `python -m outreach_agent generar ...`, sin el ejecutable del
entorno virtual."""

import sys

from outreach_agent.cli import main

sys.exit(main())
