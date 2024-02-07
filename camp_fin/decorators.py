def check_date_params(func):
    """
    Decorator to ensure that methods using the `since` parameter get passed
    year strings corresponding to a coherent input format.
    """

    def checked_func(*args, **kwargs):
        # Enforce argument format for years
        since = kwargs.get("since")
        if since:
            assert since is None or (isinstance(since, str) and len(since) == 4)
        return func(*args, **kwargs)

    return checked_func


def short_description(desc):
    """
    Decorator that assigns the `short_description` attribute of an admin form field.
    """

    def decorator(func):
        func.short_description = desc
        return func

    return decorator


def boolean(func):
    """
    Decorator that marks an admin form field as a Boolean type.
    """
    func.boolean = True
    return func
