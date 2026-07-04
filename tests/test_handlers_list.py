from __future__ import annotations

from src.bot.bot.handlers_list import COMMAND_BINDINGS, command_handler_lines


def test_command_registry_is_unique() -> None:
    commands = [binding.command for binding in COMMAND_BINDINGS]

    assert len(commands) == len(set(commands))


def test_command_registry_includes_core_handlers() -> None:
    mapping = {
        binding.command: binding.callback.__name__ for binding in COMMAND_BINDINGS
    }

    assert mapping["start"] == "start"
    assert mapping["ping"] == "ping"
    assert mapping["filter"] == "add_filter"
    assert mapping["check_handlers"] == "check_handlers"


def test_command_handler_lines_are_human_readable() -> None:
    lines = command_handler_lines()

    assert any(line.startswith("/start -> ") for line in lines)
    assert any(line.startswith("/filter -> ") for line in lines)
    assert any(line.startswith("/save -> ") for line in lines)

def test_command_registry_no_help_cmd_placeholders() -> None:
    for binding in COMMAND_BINDINGS:
        if binding.command in ["management", "features", "ban", "unban", "kick", "mute", "warn"]:
            assert binding.callback.__name__ != "help_cmd", f"{binding.command} should not be mapped to help_cmd"

def test_no_duplicate_command_registrations() -> None:
    commands = [binding.command for binding in COMMAND_BINDINGS]
    assert len(commands) == len(set(commands))
