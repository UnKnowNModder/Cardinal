"""core command package."""

# thanks to snoweee for enlightening me with decorators <3
from __future__ import annotations

import importlib
import inspect
import traceback
from pathlib import Path

from server.clients import Client, Players, fetch_client, fetch_player
from server.enums import Authority

_commands = {}


def _get_arguments_mapper(parameters: list[str]) -> callable:
    """returns a callable with the parameters requested."""
    if len(parameters) == 1:
        return lambda client, args: (client,)

    if "message" in parameters and "target" in parameters:
        return lambda client, args: (client, fetch_client(args[0]), " ".join(args[1:]))

    mappers: dict[callable] = {
        "args": lambda client, args: (client, args),
        "players": lambda client, args: (client, Players()),
        "account_id": lambda client, args: (client, args[0]),
        "target": lambda client, args: (client, fetch_client(args[0])),
        "player": lambda client, args: (client, fetch_player(args[0])),
    }

    return mappers.get(parameters[1], lambda client, args: (client,))


def on_command(
    name: str,
    aliases: list[str] = [],
    authority: Authority = Authority.USER,
    usage: str = "",
):
    """decorator to register a command."""

    def decorator(function):
        parameters = list(inspect.signature(function).parameters.keys())
        cmd = {
            "function": function,
            "authority": authority,
            "usage": usage,
            "mapper": _get_arguments_mapper(parameters=parameters),
        }
        _commands[name] = cmd
        if aliases:
            for aliase in aliases:
                _commands[aliase] = cmd
        return function

    return decorator


def command_line(msg: str, client: Client) -> str | None:
    """processes a chat message as a command.
    command line as the name says."""
    if not msg.startswith("/"):
        return msg
    command = msg.split()[0].lower()
    args = msg.split()[1:]
    if command in _commands:
        cmd = _commands[command]
        if client.authority >= cmd["authority"]:
            function = cmd["function"]
            try:
                mapper = cmd["mapper"]
                function_arguments = mapper(client, args)
                function(*function_arguments)
            except:
                # print(traceback.format_exc())
                client.error(f"Usage: {cmd['usage']}")
            return
    # wasn't any known command.
    return msg


def control_message(msg: str, client_id: int) -> str | None:
    """controls the message for filters/commands."""
    client = Client(client_id) if client_id == -1 else fetch_client(client_id)
    if client and msg:
        if not client.authenticity:
            auth_code = client.get_auth_code()
            if not client.verify_auth_code(msg.split()[0]):
                client.error(
                    f"Your auth code is: {auth_code}\nPlease enter in chat to verify."
                )
            return
        if client.is_mute:
            print(f"{client.name} (muted): {msg}")
            return
        return command_line(msg, client)
    return


def load():
    """automatically imports command files in the directory."""
    package_dir = Path(__file__).parent
    for file in package_dir.glob("*.py"):
        if file.stem == "__init__":
            continue
        module_name = f"{__package__}.{file.stem}"
        try:
            importlib.import_module(module_name)
        except ImportError:
            print(f"⚠️ Failed to load command file {file.stem}")
