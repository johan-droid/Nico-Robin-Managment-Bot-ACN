from src.bot.bot.handlers_list import COMMAND_BINDINGS
from src.bot.services.feature_service import FeatureService

for binding in COMMAND_BINDINGS:
    if binding.feature_gate and binding.feature_gate not in FeatureService.AVAILABLE_FEATURES:
        print(f"Unknown feature_gate '{binding.feature_gate}' for command '{binding.command}'")

print("Done checking feature gates.")
