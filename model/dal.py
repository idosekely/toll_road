import os
import datetime
import pandas as pd
import csv


class Data(object):

    def __init__(self):
        self.timestamp = datetime.datetime.now()
        self.price = None
        self.traffic = None

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'price': self.price,
            'traffic': self.traffic,
        }

    @staticmethod
    def headers():
        return ['timestamp', 'price', 'traffic']

    def to_data_frame(self):
        index = pd.DatetimeIndex([self.timestamp])
        df = pd.DataFrame(self.to_dict(), index=index, columns=self.headers())
        df.index = df['timestamp']
        df.drop('timestamp', 1, inplace=True)
        return df


class Dal(object):
    data_file = None

    def __init__(self, data_file=None):
        self.data_file = data_file

    def save_data(self, data, **kwargs):
        self._writer(data, **kwargs)

    def read_data(self, **kwargs):
        df = self._reader(**kwargs)
        df['traffic'] = df['traffic'].apply(lambda x: x / 60.)
        df = df.resample('T').mean()
        df.interpolate(inplace=True)
        return df

    def does_exist(self):
        if not self.data_file or not os.path.isfile(self.data_file):
            return False
        return True


class CsvHandler(Dal):
    def _writer(self, data):
        if not self.does_exist():
            mode = 'w'
            header = True
        else:
            mode = 'a'
            header = False
        data.to_data_frame().to_csv(self.data_file, mode=mode, header=header)

    def _reader(self):
        if not self.does_exist():
            return
        dateparse = lambda dates: pd.datetime.strptime(dates, '%Y-%m-%d %H:%M:%S.%f')
        df = pd.read_csv(self.data_file, parse_dates='timestamp', index_col='timestamp', date_parser=dateparse)
        return df


class HDF5Handler(Dal):
    def _writer(self, data):
        if not self.does_exist():
            mode = 'w'
            append = False
        else:
            mode = 'a'
            append = True
        data.to_data_frame().to_hdf(self.data_file, key='data', format='table', append=append, mode=mode)

    def _reader(self):
        if not self.does_exist():
            return
        return pd.read_hdf(self.data_file, 'data')
