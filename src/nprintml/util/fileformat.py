import abc
import pathlib

import pandas as pd


class FormatRegistry(dict):

    def register(self, handler, name, *aliases):
        for alias in (name,) + aliases:
            self[alias] = handler

    def get_writer(self, full_format):
        dot_count = full_format.count('.')

        if dot_count <= 1:
            (file_format, file_compression) = (full_format.split('.') if dot_count == 1
                                               else (full_format, None))

            try:
                handler = self[file_format]
            except KeyError:
                pass
            else:
                return handler(file_compression).write

        raise NotImplementedError(full_format)

    def get_reader(self, path):
        file_path = path if isinstance(path, pathlib.Path) else pathlib.Path(path)

        suffixes = (suffix.lower().lstrip('.') for suffix in reversed(file_path.suffixes))

        compression = None

        for suffix in suffixes:
            try:
                handler = self[suffix]
            except KeyError:
                if compression is None:
                    compression = suffix
                else:
                    break
            else:
                return handler(compression).read

        raise NotImplementedError(path)


format_handlers = FormatRegistry()


class FormatHandler(abc.ABC):

    __fileformats__ = format_handlers

    @classmethod
    def __init_subclass__(cls, *, names=(), **kwargs):
        """Register handler upon declaration."""
        super().__init_subclass__(**kwargs)

        if names:
            cls.__fileformats__.register(cls, *names)
        else:
            cls.__fileformats__.register(cls, cls.__name__.lower())

    def __init__(self, compression=None):
        self.compression = compression

    @abc.abstractmethod
    def read(self, path):
        pass

    @abc.abstractmethod
    def write(self, data, outdir):
        pass


class Csv(FormatHandler):

    def read(self, path):
        return pd.read_csv(path, index_col=0)

    def write(self, data, outdir):
        outname = 'features.csv'

        if self.compression:
            outname = f'{outname}.{self.compression}'

        outdir = outdir if isinstance(outdir, pathlib.Path) else pathlib.Path(outdir)
        outpath = outdir / outname

        # Unlike others to_csv infers compression from name
        data.to_csv(outpath)

        return outpath


class Parquet(FormatHandler, names=('parquet', 'parq')):

    def read(self, path):
        return pd.read_parquet(path)

    def write(self, data, outdir):
        outdir = outdir if isinstance(outdir, pathlib.Path) else pathlib.Path(outdir)
        outpath = outdir / 'features.parq'

        data.to_parquet(outpath, compression=self.compression)

        return outpath


class Feather(FormatHandler, names=('feather', 'fhr')):

    def read(self, path):
        data = pd.read_feather(path)

        if len(data.columns) > 0:
            column_name = data.columns[0]
            data.set_index(column_name, inplace=True)

        return data

    def write(self, data, outdir):
        outdir = outdir if isinstance(outdir, pathlib.Path) else pathlib.Path(outdir)
        outpath = outdir / 'features.fhr'

        # Like CSV, (unlike Parquet), Feather does not support custom indices.
        #
        # (And, unlike to_csv, to_feather raises an error if you mess this up.)
        #
        data.reset_index().to_feather(outpath, compression=self.compression)

        return outpath
