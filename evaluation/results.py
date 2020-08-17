import numpy as np


class TrajectoryResults(object):

    def __init__(self, name, pred_fcn, pred_kwargs, frame_skip=1):
        self.name = name
        self.xy_hat_list = []
        self.p_list = []
        self.dict_list = []
        self.pred_fcn = pred_fcn
        self.pred_kwargs = pred_kwargs
        self.frame_skip = frame_skip

    def predict(self, *args):
        xy_hat, p, dict_data = self.pred_fcn(*args, **self.pred_kwargs)
        self.xy_hat_list.append(xy_hat)
        self.p_list.append(p)
        self.dict_list.append(dict_data)

    def clear(self):
        self.xy_hat_list = []
        self.p_list = []
        self.dict_list = []

    def __len__(self):
        return len(self.xy_hat_list)

    def __getitem__(self, i):
        if i < 0:
            i = len(self) + i
        return self.xy_hat_list[i], self.p_list[i], self.dict_list[i]


def evaluate_metric_on_results(
        xy_true_list, results, init_fcn, accumulate_fcn, reduce_fcn):
    n_batches = 0
    accumulator = init_fcn()
    for i in range(len(results)):
        xy_true = xy_true_list[i]
        xy_hat, p, dict_data = results[i]
        n_batches += 1
        accumulate_fcn(accumulator, xy_hat, p, xy_true, **dict_data)
    metric_value = reduce_fcn(accumulator)
    return metric_value, n_batches


class RunningEvaluation(object):

    def __init__(self, metric_fcn_list, prediction_methods_list):
        """

        :param metric_fcn_list:
        :param prediction_methods_list:
        """
        self.metric_names = [metric_info[0] for metric_info in metric_fcn_list]
        # : (init_fcn, accumulate_fcn, reduce_fcn)
        self.metric_name2fcns = {metric_info[0]: metric_info[1] for
                                 metric_info in metric_fcn_list}
        self.method_names = [method.name for method in prediction_methods_list]
        self.method_metric_names2accumulator = {}
        for method_name in self.method_names:
            for metric_name in self.metric_names:
                key = (method_name, metric_name)
                self.method_metric_names2accumulator[key] = \
                    self.metric_name2fcns[metric_name][0]()
        self.n_batches = 0

    def evaluate(self, prediction_methods_list, x_true):
        """
        Evaluate each prediction method's last result on true value
        :param prediction_methods_list: of TrajectoryResults
        :param x_true:
        :return:
        """
        for method in prediction_methods_list:
            for metric_name in self.metric_names:
                key = (method.name, metric_name)
                accumulator = self.method_metric_names2accumulator[key]
                accumulate_fcn = self.metric_name2fcns[metric_name][1]
                x_hat, p, dict_data = method[-1]
                accumulate_fcn(accumulator, x_hat, p, x_true, **dict_data)
                self.method_metric_names2accumulator[key] = accumulator
        self.n_batches += 1

    def reduce(self, decimals=2):
        for method_name in self.method_names:
            print('Results for {}'.format(method_name))
            for metric_name in self.metric_names:
                key = (method_name, metric_name)
                accumulator = self.method_metric_names2accumulator[key]
                reduce_fcn = self.metric_name2fcns[metric_name][2]
                metric_val = reduce_fcn(accumulator.copy())
                print('{}: {}'.format(
                    metric_name, np.round(metric_val, decimals=decimals)))
        print('  {} evaluated\n'.format(self.n_batches))
