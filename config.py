import os


class BaseConfig(object):
    UPLOAD_FOLDER = '~/dev'
    DEFAULT_CSV = 'toll_road.csv'
    API_KEY = None


class Production(BaseConfig):
    UPLOAD_FOLDER = os.path.expanduser(BaseConfig.UPLOAD_FOLDER)
    try:
        os.makedirs(UPLOAD_FOLDER)
    except OSError:
        if not os.path.isdir(UPLOAD_FOLDER):
            raise
    CSV_PATH = os.path.join(UPLOAD_FOLDER, BaseConfig.DEFAULT_CSV)
