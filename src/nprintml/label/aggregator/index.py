import numpy as np
import pandas as pd

from . import LabelAggregator


class IndexLabelAggregator(LabelAggregator):
    """A LabelAggregator to aggregates labels according to the *index*
    of nPrint output.

    This can be the src / dst ip, the src / dst port, or an entire flow
    label.

    """
    def generate_features(self, compress=False, sample_size=1):
        """Generates index driven features by loading nPrints and
        attaching labels, grouping by a given sample size if desired.

        """
        print('Loading nprint')
        npt_df = self.load_npt(self.npts)
        print('  nPrint shape: {0}'.format(npt_df.shape))
        if compress:
            print('Compressing nPrint')
            npt_df = self.compress_npt(npt_df)
            print('  compressed nPrint shape: {0}'.format(npt_df.shape))

        print('Loading labels')
        labels = self.load_labels(self.label_file)
        print('  number of labels: {0}'.format(labels.shape[0]))

        if sample_size > 1:
            print('Grouping by sample size')
            npt_df = self.group_by_sample_size(npt_df, sample_size)
            print('  New shape of dataframe: {0}'.format(npt_df.shape))

        print('Attaching labels to nPrints')
        npt_df, missing_labels, ogns, nns = self.attach_labels(npt_df, labels)
        print('  labels attached: missing labels for:')
        for missing_label in missing_labels:
            print('    {0}'.format(missing_label))
        print('    missing labels caused {0} samples to be dropped'.format(ogns - nns))

        return npt_df

    def group_by_sample_size(self, npt, sample_size):
        """Take a large nPrint dataframe, groups it by the index, then
        split each separated sample into n sample_sized samples.

        """
        # If the sample size is 1, its just per packet, which we already have
        if sample_size <= 1:
            return npt

        new_data = []
        indexes = []
        new_columns = self.get_flattened_columns(npt, sample_size)
        groups = npt.groupby(npt.index)
        for lid, group in groups:
            # Pad rows to get an even division for sample size
            pad_rows = sample_size - group.shape[0] % sample_size
            fill_row = [-1] * group.shape[1]
            for i in range(group.shape[0], group.shape[0] + pad_rows):
                group.loc[i] = fill_row

            # actually separate group into samples and flatten for 1d learning
            num_splits = group.shape[0] / sample_size
            for sample in np.split(group, num_splits):
                flattened_sample = sample.to_numpy().flatten()
                new_data.append(flattened_sample)
                indexes.append(lid)

        return pd.DataFrame(new_data, index=indexes, columns=new_columns)
