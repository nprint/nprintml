"""
/*
  * Copyright 2020 nPrint
  * Licensed under the Apache License, Version 2.0 (the "License"); you may not
  * use this file except in compliance with the License. You may obtain a copy
  * of the License at https://www.apache.org/licenses/LICENSE-2.0
*/

This module contains code for training, evaluating, and representing the results
of AutoML training on nPrints. In general, it takes a dataframe generated from the
label aggregation step of the nprintML pipeline. It can be used on its own
as long as it receives a dataframe where each row of the dataframe contains
a single sample and the labels for the samples are contained in a 'label' column
in the dataframe

"""

import pathlib
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class LabelAggregator(ABC):
    '''
    Label Aggregator provides general methods for working with nPrints,
    including attaching labels, compressing nPrints, and generating new
    columns for flattened nPrints.

    Inheritors of this class are expected to implement generate_features() as
    a custom method to provide different methods for aggregating features
    '''
    def __init__(self, npts, label_file):
        self.npts = npts
        self.label_file = label_file

    @abstractmethod
    def generate_features(self, compress=True, sample_size=1):
        '''
        Abstract method, expected to be implemented on a per-example label
        aggregation method.
        '''

    def load_npt(self, npt_csv):
        '''
        Load an nPrint, where the index column is *always* the 0th column.
        '''
        return pd.read_csv(npt_csv, index_col=0)

    def load_labels(self, labels):
        '''
        Load labels, which are expected to be in item,label column format where
        item is the index.
        '''
        labels = pd.read_csv(labels, index_col=0)

        return labels

    def compress_npt(self, npt):
        '''
        Compress columns out of an nPrint that provide no predictive signal.
        More specifically, this method drops *all* columns in a given nPrint
        dataframe where each bit is the same value.
        '''
        nunique = npt.apply(pd.Series.nunique)
        cols_to_drop = nunique[nunique == 1].index
        npt = npt.drop(cols_to_drop, axis=1)

        return npt

    def attach_labels(self, npt_df, labels):
        '''
        Attach labels to a dataframe of nPrints, returning the labels that are
        missing, the new dataframe, and the number of samples that were lost
        '''
        missing_labels = set(npt_df.index) - set(labels.index)
        og_num_samples = npt_df.shape[0]
        npt_df = npt_df.join(labels)
        npt_df = npt_df.dropna(subset=['label'])
        new_num_samples = npt_df.shape[0]

        return npt_df, missing_labels, og_num_samples, new_num_samples

    def get_flattened_columns(self, npt, sample_size):
        '''
        When we attach labels to more than one nPrint we need to create new
        columns that essentially are the original columns multiplied by
        the number of packets in each flattened sample.
        '''
        og_columns = list(npt.columns)
        new_columns = []
        for i in range(sample_size):
            for column in og_columns:
                new_columns.append('pkt_{0}_{1}'.format(i, column))

        return new_columns


class IndexLabelAggregator(LabelAggregator):
    '''
    An implementation of the FeatureAggregator base class that aggregates labels
    according to the *index* of the nPrint output. This can be the src / dst ip,
    the src / dst port, or an entire flow label.
    '''

    def generate_features(self, compress=False, sample_size=1):
        '''
        Generates index driven features by loading nPrints and attaching labels,
        grouping by a given sample size if desired
        '''

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
        '''
        Takes a large nPrint dataframe, groups it by the index, then splits
        each separated sample into n sample_sized samples
        '''
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


class PcapLabelAggregator(LabelAggregator):
    '''
    PcapFeatureAggregtor is meant to take a directory of nPrint files and consider
    each file as a single sample, padding to the maximum size and running autoML
    on the generated samples
    '''
    def generate_features(self, compress=False, sample_size=1):
        '''
        Enumerates the directory of nPrints given, loading them, padding to
        their maximum size, and attaching labels
        '''
        npt_dir = pathlib.Path(self.npts)
        files = [npt_f for npt_f in npt_dir.glob('**/*') if npt_f.is_file()]

        print('Loading all {0} nPrints'.format(len(files)))
        npt_tups = []
        largest = None
        for npt_f in files[:100]:
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
        '''
        We need every sample size to be the same, so we find the largest
        nPrint in all of the files and pad each sample with empty nPrints
        '''
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
