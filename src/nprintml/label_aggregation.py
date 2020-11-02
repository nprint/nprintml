import pathlib
import sys

import numpy as np
import pandas as pd
from automl import AutoML

from abc import ABC, abstractmethod

class FeatureAggregator(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def generate_features():
        pass
    
    def load_npt(self, npt):
        npt = pd.read_csv(npt, index_col=0)

        return npt

    def load_labels(self, labels):
        labels = pd.read_csv(labels, index_col=0)
        print(labels)

        return labels
    
    def compress_npt(self, npt):
        nunique = npt.apply(pd.Series.nunique)
        cols_to_drop = nunique[nunique == 1].index
        npt = npt.drop(cols_to_drop, axis=1)

        return npt

    def attach_labels(self, df, labels):
        missing_labels = set(df.index) - set(labels.index)
        og_num_samples = df.shape[0]
        df = df.join(labels)
        df = df.dropna(subset=['label'])
        new_num_samples = df.shape[0]

        return df, missing_labels, og_num_samples, new_num_samples 
    
    def get_flattened_columns(self, npt, sample_size):
        og_columns = list(npt.columns)
        new_columns = []
        for i in range(sample_size):
            for c in og_columns:
                new_columns.append('pkt_{0}_{1}'.format(i, c))

        return new_columns

class IndexFeatureAggregator(FeatureAggregator):
    def __init__(self, npt_file, labels):
        self.npt_file = npt_file
        self.labels = labels

    def generate_features(self, sample_size=1, compress=False):
        print('Loading nprint')
        self.npt_df = self.load_npt(self.npt_file)
        print('  nPrint shape: {0}'.format(self.npt_df.shape))
        if compress:
            print('Compressing nPrint')
            self.npt_df = self.compress_npt(self.npt_df)
            print('  compressed nPrint shape: {0}'.format(self.npt_df.shape))
        
        print('Loading labels')
        self.labels = self.load_labels(self.label_file, self.label_type)
        print('  number of labels: {0}, type of labels: {1}'.format(self.labels.shape[0],
                                                                    self.label_type))
        if sample_size > 1: 
            print('Grouping by sample size')
            self.npt_df = self.group_by_sample_size(self.npt_df, sample_size)
        
        print('Attaching labels to nPrints')
        npt_df, ml, ogns, nns = self.attach_labels(self.npt_df, self.labels)
        print('  labels attached: missing labels for:')
        for missing_label in ml:
            print('    {0}'.format(missing_label))
        print('    missing labels caused {0} samples to be dropped'.format(ogns - nns))
        
    def group_by_sample_size(self, npt, sample_size):
        # If the sample size is 1, its just per packet, which we already have
        if sample_size <= 1:
            return

        new_data = []
        indexes = []
        new_columns = self.get_new_columns(npt, sample_size)
        groups = npt.groupby(npt.index)
        for lid, group in groups:
            # Pad rows to get an even division for sample size
            pad_rows = sample_size - group.shape[0] % sample_size
            fill_row = [-1 for i in range(group.shape[1])]
            for i in range(group.shape[0], group.shape[0] + pad_rows):
                group.loc[i] = fill_row
            
            # actually separate group into samples and flatten for 1d learning
            num_splits = group.shape[0] / sample_size
            for sample in np.split(group, num_splits):
                flattened_sample = sample.to_numpy().flatten()
                new_data.append(flattened_sample)
                indexes.append(lid)

        new_df = pd.DataFrame(new_data, index=indexes, columns=new_columns)

        return new_df

class PcapFeatureAggregator(FeatureAggregator):
    def __init__(self, npt_dir, labels):
        self.npt_dir = pathlib.Path(npt_dir)
        self.label_file = labels

    def generate_features(self, compress=False):
        files = [f for f in self.npt_dir.glob('**/*') if f.is_file()]

        print('Loading all {0} nPrints'.format(len(files)))
        npt_tups = []
        largest = None
        for i, f in enumerate(files):
            npt = self.load_npt(f)
            if largest is None or npt.shape[0] > largest.shape[0]:
                largest = npt
            npt_tups.append((npt, str(f)))
        
        print('Padding nPrints to maximum size: {0}'.format(largest.shape[0]))
        npts = self.pad_and_flatten_npts(npt_tups, largest)
        labels = self.load_labels(self.label_file)
    
        print('Attaching labels to nPrints')
        npt_df, ml, ogns, nns = self.attach_labels(npts, labels)
        print('  labels attached: missing labels for: {0}'.format(ml))
        print('    missing labels caused {0} samples to be dropped'.format(ogns - nns))

        return npt_df

    def pad_and_flatten_npts(self, npt_tups, largest):
        new_npts = []
        new_indexes = []
        new_columns = self.get_flattened_columns(largest, largest.shape[0])
        fill_row = [-1 for i in range(npt_tups[0][0].shape[1])]
        
        for (npt, index) in npt_tups:
            if npt.shape[0] < largest.shape[0]:
                for i in range(npt.shape[0], largest.shape[0]):
                    npt.loc[i] = fill_row
            flattened_npt = npt.to_numpy().flatten()
            new_npts.append(flattened_npt)
            new_indexes.append(index)

        new_npts = pd.DataFrame(new_npts, index=new_indexes, columns=new_columns)

        return new_npts

if __name__ == '__main__':
    fa = PcapFeatureAggregator(sys.argv[1], sys.argv[2])
    npt_df = fa.generate_features(compress=False)
    import pathlib
    a = AutoML(npt_df, pathlib.Path('tmp'))
    a.run()
