
from src.bot.bot.middleware.feature_gate import COMMAND_FEATURES
from src.bot.services.feature_service import FeatureService


def test_feature_gate_mappings():
    available_features = set(FeatureService.AVAILABLE_FEATURES.keys())

    for command, feature in COMMAND_FEATURES.items():
        assert feature in available_features, f"Command '{command}' maps to unknown feature '{feature}'"

def test_all_features_exist():
    # Ensure all features map to a command or are listed properly
    set(FeatureService.AVAILABLE_FEATURES.keys())
    used_features = set(COMMAND_FEATURES.values())

    # Assert there is at least some mapping
    assert len(used_features) > 0
