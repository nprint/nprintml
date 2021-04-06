import pathlib

import numpy as np
import pandas as pd

from . import LabelAggregator, AggregationLengthError, AggregationPathError


class IndexLabelAggregator(LabelAggregator):
    """A LabelAggregator to aggregates labels according to the *index*
    of nPrint output.

    This can be the src / dst ip, the src / dst port, or an entire flow
    label.

    """
    @classmethod
    def normalize_npt(cls, npt_csv):
        if isinstance(npt_csv, str):
            return cls.normalize_npt(pathlib.Path(npt_csv))

        if isinstance(npt_csv, pathlib.Path):
            if npt_csv.is_dir():
                try:
                    (npt_csv,) = npt_csv.iterdir()
                except ValueError:
                    raise AggregationPathError(
                        f"{cls.__name__} expects exactly one nPrint data file but "
                        f"specified directory contains none or more than one: '{npt_csv}'"
                    )

            return npt_csv

        # treat as stream
        try:
            (npt_csv,) = npt_csv
        except ValueError:
            raise AggregationLengthError(
                f"{cls.__name__} expects exactly one nPrint data result but "
                f"specified stream contains none or more than one: {npt_csv}"
            )
        else:
            return npt_csv

    def __call__(self, npt_csv, compress=False, sample_size=1, path_input_base=None):
        """Generate index driven features by loading an nPrint result
        and attaching labels, grouping by a given sample size if
        desired.

        `npt_csv` may specify either a path to an nPrint result (`str`
        or `pathlib.Path`) OR a stream containing an open file-like
        object (exposing both `read()` and `name`).

        (If a path, `npt_csv` may specify a directory, so long as the
        directory contains only one nPrint result file.)

        """
        npt_input = self.normalize_npt(npt_csv)

        print('Loading nPrint:', self.filerepr(npt_input))
        npt = self.load_npt(npt_input)

        print('Loaded 1 nprint')
        print('  nPrint shape:', npt.shape)

        if compress:
            print('Compressing nPrint')
            npt = self.compress_npt(npt)
            print('  compressed nPrint shape:', npt.shape)

        print('Loading labels:', self.filerepr(self.label_csv))
        self.labels = self.load_label(self.label_csv)
        print('  number of labels:', self.labels.shape[0])

        if sample_size > 1:
            print('Grouping by sample size')
            npt = self.regroup_npt(npt, sample_size)
            print('  New shape of dataframe:', npt.shape)

        print('Attaching labels to nPrints')
        (npt, missing_labels, ogns, nns) = self.attach_label(npt, self.labels)
        print('  labels attached: missing labels for:')
        for missing_label in missing_labels:
            print('    {0}'.format(missing_label))
        print('    missing labels caused samples to be dropped:', (ogns - nns))

        return npt

    def regroup_npt(self, npt, sample_size):
        """Take a large nPrint dataframe, groups it by the index, then
        split each separated sample into n sample_sized samples.

        """
        # If the sample size is 1, its just per packet, which we already have
        if sample_size <= 1:
            return npt

        grouped = []
        indexes = []

        for (lid, group) in npt.groupby(npt.index):
            # Pad rows to get an even division for sample size
            pad_rows = sample_size - group.shape[0] % sample_size
            fill_row = [-1] * group.shape[1]
            for index in range(group.shape[0], group.shape[0] + pad_rows):
                group.loc[index] = fill_row

            # actually separate group into samples and flatten for 1d learning
            num_splits = group.shape[0] / sample_size
            for sample in np.split(group, num_splits):
                flattened_sample = sample.to_numpy().flatten()
                grouped.append(flattened_sample)
                indexes.append(lid)

        cols_flat = self.flatten_columns(npt.columns, sample_size)
        return pd.DataFrame(grouped, index=indexes, columns=cols_flat)
