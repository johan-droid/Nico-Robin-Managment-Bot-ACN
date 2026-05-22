from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from types import ModuleType

from telegram.ext import Application

logger = logging.getLogger(__name__)


class ModuleLoader:
    def __init__(self, application: Application, modules_path: str = "modules") -> None:
        self.application = application
        self.modules_path = Path(modules_path)

    def discover(self) -> list[str]:
        if not self.modules_path.exists():
            return []
        return sorted(
            module.name
            for module in pkgutil.iter_modules([str(self.modules_path)])
            if not module.ispkg and not module.name.startswith("_")
        )

    def _import_module(self, module_name: str) -> ModuleType:
        return importlib.import_module(f"modules.{module_name}")

    def load_all(self) -> list[str]:
        loaded: list[str] = []
        for module_name in self.discover():
            module = self._import_module(module_name)
            register = getattr(module, "register", None)
            module_label = getattr(module, "MODULE_NAME", module_name)
            if callable(register):
                register(self.application)
                loaded.append(module_label)
                logger.info("module_loaded", extra={"module": module_label})
        return loaded
