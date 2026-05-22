from __future__ import annotations

import importlib
import logging
from pathlib import Path
from types import ModuleType

from telegram.ext import Application

logger = logging.getLogger(__name__)


class ModuleLoader:
    """Auto-discovers and registers modules from the modules/ directory."""

    def __init__(self, modules_dir: str = "modules") -> None:
        self.modules_dir = Path(modules_dir)
        self.loaded_modules: dict[str, ModuleType] = {}

    def discover(self) -> list[str]:
        if not self.modules_dir.exists():
            return []
        module_names = []
        for file_path in sorted(self.modules_dir.glob("*.py")):
            if file_path.name.startswith("_") or file_path.stem == "__init__":
                continue
            module_names.append(file_path.stem)
        return module_names

    def load_and_register(self, application: Application) -> None:
        for module_name in self.discover():
            import_path = f"modules.{module_name}"
            module = importlib.import_module(import_path)
            if not hasattr(module, "MODULE_NAME") or not hasattr(module, "register"):
                logger.warning(
                    "module_missing_contract",
                    extra={"module": import_path},
                )
                continue
            module.register(application)
            self.loaded_modules[module.MODULE_NAME] = module
            logger.info("module_registered", extra={"module": module.MODULE_NAME})
