import autogluon as ag
from autogluon import TabularPrediction as task
from sklearn.model_selection import train_test_split

class AutoML:
    def __init__(ml_data, outdir):
        self.data = ml_data
        self.outdir = outdir
        self.qd = { 
          0 : 'medium_quality_faster_train'
          1 : 'good_quality_faster_inference_only_refit',
          2 : 'high_quality_fast_inference_only_refit',
          3 : 'best_quality',
          }

    def run(train_size=.70, test_size=.30, quality=0, time_limit=5*60, n_threads=1):
        train, test = train_test_split(self.data, train_size=train_size, test_size=test_size)
        predictor = train(train, train_size, test_size, quality, time_limit, n_threads)
        test(test, predictor)

    def train(train, quality=0, time_limit=5*60, n_threads=1):
        train, test = train_test_split(self.data, train_size=train_size,
                                       test_size=test_size)
        
        predictor = task.fit(train_data=train, label='label', eval_metric=metric,
                             output_directory=self.outdir, time_limit=time_limit,
                             presets=self.qd[quality], nthreads_per_trial=n_threads)

        return predictor

    def test(predictor, test):
        y_test = test['label']
        test_no_label = test.drop(labels=['label'], axis=1)
        
        # This actually gets us a leaderboard dataframe with stats, if we want graphs we'll have to do more
        leaderboard = predictor.leaderboard(test, silent=True)
        leaderboard = leaderboard.set_index('model').sort_index()
