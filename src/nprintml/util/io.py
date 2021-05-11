import io


class _NamedIO:

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.name}>'


class NamedStringIO(_NamedIO, io.StringIO):
    """StringIO featuring a `name` attribute to reflect the path
    represented by its contents.

    """
    def __init__(self, initial_value='', newline='\n', name=None):
        super().__init__(initial_value, newline)
        self.name = name


class NamedBytesIO(_NamedIO, io.BytesIO):
    """BytesIO featuring a `name` attribute to reflect the path
    represented by its contents.

    """
    def __init__(self, initial_bytes=b'', name=None):
        super().__init__(initial_bytes)
        self.name = name
