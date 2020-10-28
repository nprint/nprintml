import pathlib
import autogluon as ag
from autogluon import TabularPrediction as task
from sklearn.model_selection import train_test_split
import pandas as pd

import seaborn as sns
sns.set_style("ticks")
sns.set_context(rc={"lines.linewidth": 1.75})
import matplotlib.pyplot as plt

from sklearn.metrics import roc_curve, auc
from sklearn.preprocessing import LabelBinarizer

class AutoML:
    def __init__(self, ml_data, outpath):
        self.data = ml_data
        self.outpath = outpath
        self.qd = { 
          0 : 'medium_quality_faster_train',
          1 : 'good_quality_faster_inference_only_refit',
          2 : 'high_quality_fast_inference_only_refit',
          3 : 'best_quality',
          }

    def run(self, test_size=.30, eval_metric='accuracy', quality=0, time_limits=5*60, n_threads=1):
        train_data, test_data = train_test_split(self.data, test_size=test_size)
        predictor = self.train(train_data, eval_metric, quality, time_limits, n_threads)
        self.test(predictor, test_data)
        self.generate_graphs(predictor, test_data)

    def train(self, train_data, eval_metric='accuracy', quality=0, time_limits=5*60, n_threads=1):
        predictor = task.fit(train_data=train_data, label='label', eval_metric=eval_metric,
                             output_directory=self.outpath.name, time_limits=time_limits,
                             presets=self.qd[quality], nthreads_per_trial=n_threads)

        return predictor

    def test(self, predictor, test_data):
        leaderboard = predictor.leaderboard(test_data, silent=True)
        leaderboard = leaderboard.set_index('model').sort_index()
        leaderboard.to_csv(self.outpath / 'leaderboard.scv')

    def generate_graphs(self, predictor, test_data):
        y_true = test_data['label']
        test_no_label = test_data.drop(labels=['label'], axis=1)
        binarizer = LabelBinarizer().fit(y_true)
        binarized_labels = binarizer.transform(y_true)
        print(binarized_labels)

        classes = sorted(list(set(y_true)))
        y_proba = predictor.predict_proba(test_no_label)
        self._make_binary_roc(binarized_labels, y_proba)
        #self.make_roc(classes, binarized_labels, y_proba)
    
    def make_roc(self, binarized_labels, y_proba):
        pass

    def _make_binary_roc(self, y_true, y_proba):
        fpr, tpr, thresholds = roc_curve(y_true, y_proba)
        sns.lineplot(fpr, tpr)
        plt.savefig(self.outpath / 'roc.pdf')

if __name__ == '__main__':
     import sys
     data = pd.read_csv(sys.argv[1], index_col=0, low_memory=False)
     p = pathlib.Path('tmp/')
     a = AutoML(data, p)
     a.run(time_limits=5, n_threads=6)
