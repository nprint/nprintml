import tempfile


def mktestdir(prefix=f'nprintml.{__name__}.'):
    return tempfile.TemporaryDirectory(prefix=prefix)
