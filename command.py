def command(*names, admins_only=False):
    """
    Decorator used to declare bot commands.

    Parameters
    ----------
    *names : str
        Command names (aliases) without prefix.
    admins_only : bool
        If True, the command is restricted to bot admins.

    Example
    -------
    @command("status", "showstatus")
    async def show_status(...):
        ...
    """

    def decorator(func):
        func._command_names = names
        func._command = True
        func.primary_name = names[0]
        func.admins_only = admins_only
        return func
    return decorator
