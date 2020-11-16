import pathlib

import pandas as pd

from . import LabelAggregator


class PcapLabelAggregator(LabelAggregator):
    """A LabelAggregator that takes a directory of nPrint output files
    and considers each file a single sample, padding to the maximum
    size, to run autoML on the generated samples.

    """
    def __call__(self, compress=False, sample_size=1):
        """Enumerate given directory of nPrint data, load, pad to their
        maximum size, and attach labels.

        """
        npts = self.merge_npt()

        if compress:
            print('Compressing nPrint')
            npts = self.compress_npt(npts)
            print('  compressed nPrint shape:', npts.shape)

        print('Attaching labels to nPrints')

        labels = self.load_label(self.label_csv)
        (npt_df, missing_labels, ogns, nns) = self.attach_label(npts, labels)

        print('  labels attached: missing labels for:', missing_labels)
        print('    missing labels caused samples to be dropped:', (ogns - nns))

        return npt_df

    def merge_npt(self):
        """Merge nPrint data from multiple output files."""
        # Load nPrint data sets and determine largest set
        print('Loading nprints')

        npt_dir = pathlib.Path(self.npt_csv)
        npt_files = (npt_file for npt_file in npt_dir.iterdir() if npt_file.is_file())

        npts0 = []
        npt_paths = []
        largest_npt = None
        file_count = 0

        for (file_count, npt_file) in enumerate(npt_files, 1):
            npt = self.load_npt(npt_file)

            if largest_npt is None or npt.shape[0] > largest_npt.shape[0]:
                largest_npt = npt

            npts0.append(npt)
            npt_paths.append(str(npt_file))

        print('Loaded', file_count, 'nprints')

        # We need every sample size to be the same, so we find the
        # largest nPrint in all of the files and pad each sample with
        # empty nPrints.

        row_len = npts0[0].shape[1]
        fill_row = [-1] * row_len

        npts1 = []

        for npt in npts0:
            for index in range(npt.shape[0], largest_npt.shape[0]):
                npt.loc[index] = fill_row
            npt_flat = npt.to_numpy().flatten()
            npts1.append(npt_flat)

        cols_flat = self.flatten_columns(largest_npt.columns, largest_npt.shape[0])

        npts = pd.DataFrame(npts1, index=npt_paths, columns=cols_flat)

        print('nPrints padded to maximum size:', largest_npt.shape[0])
        print('nPrint shape:', npts.shape)

        return npts
