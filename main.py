import configparser
import os

HERE = os.path.dirname(__file__)
config = configparser.ConfigParser()
config.read(os.path.join(HERE, 'config.ini'))

if __name__ == '__main__':
    pass
