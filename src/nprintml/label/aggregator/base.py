import abc

import pandas as pd


class LabelAggregator(abc.ABC):
    """LabelAggregator provides general methods for working with nPrint
    data, such as attaching labels, compressing nPrint data, and
    generating new columns for flattened nPrint data.

    Inheritors of this class are expected to implement the abstract
    method `__call__()` to provide their method of feature aggregation.

    """
    def __init__(self, npt_csv, label_csv):
        self.npt_csv = npt_csv
        self.label_csv = label_csv

    @abc.abstractmethod
    def __call__(self, compress=False, sample_size=1):
        """Abstract method, expected to be implemented on a per-example
        label aggregation method.

        """

    def load_npt(self, npt_csv):
        """Load nPrint data.

        The index column is expected to *always* be the 0th column.

        """
        return pd.read_csv(npt_csv, index_col=0)

    def load_label(self, labels_csv):
        """Load labels, which are expected to be in item, label column
        format where item is the index.

        """
        return pd.read_csv(labels_csv, index_col=0)

    def compress_npt(self, npt):
        """Compress columns out of an nPrint that provide no predictive
        signal.

        More specifically, this method drops *all* columns in a given nPrint
        dataframe where each bit is the same value.

        """
        nunique = npt.apply(pd.Series.nunique)
        cols_to_drop = nunique[nunique == 1].index
        return npt.drop(cols_to_drop, axis=1)

    def attach_label(self, npt, label):
        """Attach labels to a dataframe of nPrints, returning the labels
        that are missing, the new dataframe, and the number of samples
        that were lost.

        """
        missing_labels = set(npt.index) - set(label.index)
        og_num_samples = npt.shape[0]
        npt = npt.join(label).dropna(subset=['label'])
        new_num_samples = npt.shape[0]

        return (npt, missing_labels, og_num_samples, new_num_samples)

    def flatten_columns(self, columns, sample_size):
        """When we attach labels to more than one nPrint we need to
        create new columns that essentially are the original columns
        multiplied by the number of packets in each flattened sample.

        """
        return [
            f'pkt_{index}_{column}'
            for index in range(sample_size)
            for column in columns
        ]
