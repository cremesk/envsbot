def command(*names, owner_only=False):
    """
    Decorator used to declare bot commands.

    Parameters
    ----------
    *names : str
        Command names (aliases) without prefix.
    owner_only : bool
        If True, the command is restricted to bot admins.

    Example
    -------
    @command("status", "showstatus")
    async def show_status(...):
        ...
    """

    def decorator(func):

        func._command_names = names
        func.primary_name = names[0]
        func.owner_only = owner_only

        return func

    return decorator
