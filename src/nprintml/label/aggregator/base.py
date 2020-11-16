import abc

import pandas as pd


class LabelAggregator(abc.ABC):
    """LabelAggregator provides general methods for working with nPrint
    data, such as attaching labels, compressing nPrint data, and
    generating new columns for flattened nPrint data.

    Inheritors of this class are expected to implement
    `generate_features()` as a custom method to provide their method of
    feature aggregation.

    """
    def __init__(self, npts, label_file):
        self.npts = npts
        self.label_file = label_file

    @abc.abstractmethod
    def generate_features(self, compress=True, sample_size=1):
        """Abstract method, expected to be implemented on a per-example
        label aggregation method.

        """

    def load_npt(self, npt_csv):
        """Load an nPrint, where the index column is *always* the 0th
        column.

        """
        return pd.read_csv(npt_csv, index_col=0)

    def load_labels(self, labels_csv):
        """Load labels, which are expected to be in item,label column
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

    def attach_labels(self, npt_df, labels):
        """Attach labels to a dataframe of nPrints, returning the labels
        that are missing, the new dataframe, and the number of samples
        that were lost.

        """
        missing_labels = set(npt_df.index) - set(labels.index)
        og_num_samples = npt_df.shape[0]
        npt_df = npt_df.join(labels)
        npt_df = npt_df.dropna(subset=['label'])
        new_num_samples = npt_df.shape[0]

        return npt_df, missing_labels, og_num_samples, new_num_samples

    def get_flattened_columns(self, npt, sample_size):
        """When we attach labels to more than one nPrint we need to
        create new columns that essentially are the original columns
        multiplied by the number of packets in each flattened sample.

        """
        og_columns = list(npt.columns)
        new_columns = []
        for i in range(sample_size):
            for column in og_columns:
                new_columns.append('pkt_{0}_{1}'.format(i, column))

        return new_columns
