import pathlib

import pandas as pd

from . import LabelAggregator


class PcapLabelAggregator(LabelAggregator):
    """A LabelAggregator that takes a directory of nPrint output files
    and considers each file a single sample, padding to the maximum
    size, to run autoML on the generated samples.

    """
    def generate_features(self, compress=False, sample_size=1):
        """Enumerates the directory of nPrints given, loading them,
        padding to their maximum size, and attaching labels.

        """
        npt_dir = pathlib.Path(self.npts)
        files = [npt_f for npt_f in npt_dir.glob('**/*') if npt_f.is_file()]

        print('Loading all {0} nPrints'.format(len(files)))
        npt_tups = []
        largest = None
        for npt_f in files:
            npt = self.load_npt(npt_f)
            if largest is None or npt.shape[0] > largest.shape[0]:
                largest = npt
            npt_tups.append((npt, str(npt_f)))

        print('Padding nPrints to maximum size: {0}'.format(largest.shape[0]))
        npts = self.pad_and_flatten_npts(npt_tups, largest)
        print('nPrint shape: {0}'.format(npts.shape))
        if compress:
            print('Compressing nPrint')
            npts = self.compress_npt(npts)
            print('  compressed nPrint shape: {0}'.format(npts.shape))
            npts = self.compress_npt(npts)
        labels = self.load_labels(self.label_file)

        print('Attaching labels to nPrints')
        npt_df, missing_labels, ogns, nns = self.attach_labels(npts, labels)
        print('  labels attached: missing labels for: {0}'.format(missing_labels))
        print('    missing labels caused {0} samples to be dropped'.format(ogns - nns))

        return npt_df

    def pad_and_flatten_npts(self, npt_tups, largest):
        """We need every sample size to be the same, so we find the
        largest nPrint in all of the files and pad each sample with
        empty nPrints.

        """
        new_npts = []
        new_indexes = []
        new_columns = self.get_flattened_columns(largest, largest.shape[0])
        row_len = npt_tups[0][0].shape[1]
        fill_row = [-1] * row_len

        for (npt, index) in npt_tups:
            if npt.shape[0] < largest.shape[0]:
                for i in range(npt.shape[0], largest.shape[0]):
                    npt.loc[i] = fill_row
            flattened_npt = npt.to_numpy().flatten()
            new_npts.append(flattened_npt)
            new_indexes.append(index)

        return pd.DataFrame(new_npts, index=new_indexes, columns=new_columns)
