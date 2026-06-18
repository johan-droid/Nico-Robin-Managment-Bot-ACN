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
