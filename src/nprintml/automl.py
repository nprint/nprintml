import pathlib
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import autogluon as ag
from autogluon import TabularPrediction as task
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelBinarizer
from sklearn.metrics import (
    roc_curve,
    auc,
    precision_recall_curve,
    average_precision_score,
    confusion_matrix,
    ConfusionMatrixDisplay,
)

import seaborn as sns
sns.set_style("ticks")
sns.set_context(rc={"lines.linewidth": 1.75})


class AutoML:
    def __init__(self, ml_data, outpath):
        self.data = ml_data
        self.outpath = outpath
        self.qd = {
          0: 'medium_quality_faster_train',
          1: 'good_quality_faster_inference_only_refit',
          2: 'high_quality_fast_inference_only_refit',
          3: 'best_quality',
          }

    def run(self, test_size=.30, eval_metric='accuracy', quality=0,
            time_limits=5*60, n_threads=1):
        train_data, test_data = train_test_split(self.data, test_size=test_size)
        predictor = self.train(train_data, eval_metric, quality, time_limits,
                               n_threads)
        self.test(predictor, test_data)
        self.generate_graphs(predictor, test_data)

    def train(self, train_data, eval_metric='accuracy', quality=0,
              time_limits=5*60, n_threads=1):
        return task.fit(train_data=train_data, label='label',
                        eval_metric=eval_metric,
                        output_directory=self.outpath.name,
                        time_limits=time_limits,
                        presets=self.qd[quality],
                        nthreads_per_trial=n_threads)

    def test(self, predictor, test_data):
        leaderboard = predictor.leaderboard(test_data, silent=True)
        leaderboard = leaderboard.set_index('model').sort_index()
        leaderboard.to_csv(self.outpath / 'leaderboard.scv')

    def generate_graphs(self, predictor, test_data):
        y_true = test_data['label']
        test_no_label = test_data.drop(labels=['label'], axis=1)
        binarizer = LabelBinarizer().fit(y_true)
        binarized_labels = binarizer.transform(y_true)

        y_pred = predictor.predict(test_no_label)
        y_proba = predictor.predict_proba(test_no_label)
        self.make_pr(binarizer.classes_, binarized_labels, y_proba)
        self.make_roc(binarizer.classes_, binarized_labels, y_proba)
        self.make_cfmx(binarizer.classes_, y_true, y_pred, normalize='all')

    def make_cfmx(self, classes, y_true, y_pred, normalize=None):
        cm = confusion_matrix(y_true, y_pred)
        c = ConfusionMatrixDisplay(cm, display_labels=classes)
        c.plot(include_values=False, cmap=plt.cm.Blues, xticks_rotation=45)

        self.finalize_graph(self.outpath / 'cfmx.pdf',
                            x_label='Predicted Label', y_label='True Label')

    def make_pr(self, classes, y_true_bin, y_proba):
        # Binary case does not enumerate
        if len(classes) == 2:
            ax = self._make_binary_pr(y_true_bin.ravel(), y_proba.ravel())
        else:
            for i, cl in enumerate(classes):
                ax = self._make_binary_pr(y_true_bin[:, i], y_proba[:, i], cl=cl)

        # Split up the line styles to make them unique
        linestyles = ('-', '--', '-.', ':')
        for (linestyle, line) in zip(itertools.cycle(linestyles),
                                     ax.lines):
            line.set_linestyle(linestyle)

        self.finalize_graph(self.outpath / 'pr.pdf', x_lim=[0.0, 1.0],
                            y_lim=[0.0, 1.05], legend_loc='lower left',
                            x_label='Recall', y_label='Precision')

    def _make_binary_pr(self, y_true, y_proba, cl=None):
        precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
        cl_ap = average_precision_score(y_true, y_proba)
        if cl:
            label = '{0} - AP: {1:.2f}'.format(cl, cl_ap)
        else:
            label = 'AP: {0:.2f}'.format(cl_ap)
        return sns.lineplot(x=recall, y=precision, label=label)

    def make_roc(self, classes, y_true_bin, y_proba):
        # Binary case does not enumerate
        if len(classes) == 2:
            ax = self._make_binary_roc(y_true_bin.ravel(), y_proba.ravel())
        else:
            for i, cl in enumerate(classes):
                ax = self._make_binary_roc(y_true_bin[:, i], y_proba[:, i], cl=cl)

        # Split up the line styles to make them unique
        linestyles = ('-', '--', '-.', ':')
        for (linestyle, line) in zip(itertools.cycle(linestyles),
                                     ax.lines):
            line.set_linestyle(linestyle)

        self.finalize_graph(self.outpath / 'roc.pdf', x_lim=[0.0, 1.0],
                            y_lim=[0.0, 1.05], x_label='False Positive Rate',
                            y_label='True Positive Rate',
                            legend_loc='lower right')

    def _make_binary_roc(self, y_true, y_proba, cl=None):
        fpr, tpr, thresholds = roc_curve(y_true, y_proba)
        cl_auc = auc(fpr, tpr)
        if cl:
            label = '{0} - AUC: {1:.2f}'.format(cl, cl_auc)
        else:
            label = 'AUC: {0:.2f}'.format(cl_auc)
        return sns.lineplot(x=fpr, y=tpr, label=label)

    def finalize_graph(self, ofn, x_lim=None, y_lim=None, legend_loc=None,
                       title=None, x_label=None, y_label=None):
        plt.xlim(x_lim)
        plt.ylim(y_lim)
        if legend_loc:
            plt.legend(loc=legend_loc)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.title(title)
        plt.tight_layout()
        plt.savefig(ofn)
        plt.clf()
