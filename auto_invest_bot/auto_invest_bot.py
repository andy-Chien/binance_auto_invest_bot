import os
import time
import yaml
import zipfile
import getpass
import logging
import datetime
from binance.spot import Spot
from binance.error import ClientError

class AutoInvestBot:
    def __init__(self):
        self.logger = logging.getLogger("logger")
        c_handler = logging.StreamHandler()
        self.logger.addHandler(c_handler)
        self.logger.setLevel(logging.DEBUG)

        cfg_path = os.path.dirname(os.path.abspath(__file__)) + '/../config/cfg.yaml.zip'
        if not os.path.exists(cfg_path):
            cfg_path, _ = os.path.splitext(cfg_path)
            if not os.path.exists(cfg_path):
                raise ValueError(f"Config file not found: {cfg_path}")

        self.history_dir = os.path.dirname(os.path.abspath(__file__)) + '/../trading_history/'

        cfg_data = self.read_cfg(cfg_path)

        self.url_list = [
            'https://api.binance.com',
            'https://api1.binance.com',
            'https://api2.binance.com',
            'https://api3.binance.com'
        ]
        self.api_key = cfg_data['api_key']
        self.api_secret = cfg_data['api_secret']
        self.client = Spot(cfg_data['api_key'], cfg_data['api_secret'], 
                           base_url=self.url_list[0])
        self.url_list.append(self.url_list.pop(0))

        self.order_list = cfg_data['order_list']

        if self.check_setting(self.order_list):
            self.logger.info('Order list checked.')
        else:
            raise ValueError(f"Some thing wrong in order list")
        
    def change_base_url(self):
        self.client = Spot(self.api_key, self.api_secret, 
                           base_url=self.url_list[0])
        self.url_list.append(self.url_list.pop(0))
        try:
            self.client.time()
        except:
            self.logger.warn("Try connecting to a different server.")
            self.change_base_url()
        

    def read_cfg(self, cfg_path):
        root, extension = os.path.splitext(cfg_path)
        if extension == '.zip':
            with zipfile.ZipFile(cfg_path, 'r') as zipf:
                pwd = getpass.getpass(prompt='password:')
                with zipf.open(os.path.basename(root), pwd=pwd.encode('utf-8')) as file:
                    return yaml.safe_load(file)
                
        elif extension == '.yaml':
            with open(cfg_path, 'r') as file:
                return yaml.safe_load(file)
        else:
            raise ValueError(f"Invalid file extension: {extension}")

    def check_setting(self, order_list):
        passed = True
        for order in order_list:
            ot = order['time']
            if order['frequency'] == 'WEEKLY':
                if len(ot) != 3 or not (0 <= ot[0] < 7) or \
                        not (0 <= ot[1] < 24) or not (0 <= ot[2] < 60):
                    self.logger.error('[ERROR]: Wrong WEEKLY time setting!')
                    passed = False

            elif order['frequency'] == 'DAILY':
                if len(ot) != 2 or not (0 <= ot[0] < 24) or not (0 <= ot[1] < 60):
                    self.logger.error('[ERROR]: Wrong DAILY time setting!')
                    passed = False

            elif order['frequency'] == 'HOURLY':
                if len(ot) != 1 or not (0 <= ot[0] < 60):
                    self.logger.error('[ERROR]: Wrong HOURLY time setting!')
                    passed = False

            elif order['frequency'] == 'MINUTELY':
                if len(order['time']) != 0:
                    self.logger.error('[ERROR]: Wrong MINUTELY time setting!')
                    passed = False
            else:
                self.logger.error('[ERROR]: Wrong frequency type!')
                passed = False
        return passed

    def update_sys_time(self):
        for order in self.order_list:
            now = datetime.datetime.now()
            if order['frequency'] == 'WEEKLY':
                order['sys_time'] = datetime.datetime(
                    now.year, now.month, now.day, order['time'][1], order['time'][2])
                day_shift = order['time'][0] - now.weekday()
                if day_shift < 0:
                    day_shift += 7
                order['sys_time'] += datetime.timedelta(days=day_shift)
                if now > order['sys_time']:
                    order['sys_time'] += datetime.timedelta(days=7)

            elif order['frequency'] == 'DAILY':
                order['sys_time'] = datetime.datetime(
                    now.year, now.month, now.day, order['time'][0], order['time'][1])
                if now > order['sys_time']:
                    order['sys_time'] += datetime.timedelta(days=1)
                
            elif order['frequency'] == 'HOURLY':
                order['sys_time'] = datetime.datetime(
                    now.year, now.month, now.day, now.hour, order['time'][0])
                if now > order['sys_time']:
                    order['sys_time'] += datetime.timedelta(hours=1)

            elif order['frequency'] == 'MINUTELY':
                order['sys_time'] = datetime.datetime(
                    now.year, now.month, now.day, now.hour, now.minute, 0)
                if now > order['sys_time']:
                    order['sys_time'] += datetime.timedelta(minutes=1)
        return True

    def market_buy(self, order):
        params = {
            'symbol': order['symbol'],
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': order['amount'],
        }
        try:
            res = self.client.new_order(**params)
            fill = res['fills'][-1]
            now = datetime.datetime.now()
            ny, nm, nd, nh, nmi, ns = now.year, now.month, now.day, now.hour, now.minute, now.second
            trade_info = '{}/{}/{}, {}:{}:{}, {}, status: {}, price: {}, qty: {}, amount: {} \n'.format(
                            ny, nm, nd, nh, nmi, ns, res['symbol'], res['status'], fill['price'], \
                            res['executedQty'], res['cummulativeQuoteQty'])
            self.logger.info(trade_info)
            with open(self.history_dir + '{}_{}'.format(ny, nm) + '.history.txt', 'a') as file:
                file.write(trade_info)
            
        except ClientError as error:
            self.logger.error(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )
            if error.error_code == -1013:
                self.logger.error("[ERROR]: Order amount is too low!")
        except:
            self.logger.warning("Try connecting to a different server.")
            self.change_base_url()
            self.market_buy(order)

    def main_loop(self):
        while self.update_sys_time():
            closest_time = float('inf')
            tmp_order_list = []
            for order in self.order_list:
                time_difference = \
                    (order['sys_time'] - datetime.datetime.now()).total_seconds()
                if time_difference < closest_time:
                    closest_time = time_difference
                if time_difference < 30.0:
                    tmp_order_list.append(order)

            if 30.0 < closest_time < float('inf'):
                time.sleep(closest_time - 30.0)

            for order in tmp_order_list:
                time_difference = \
                    (order['sys_time'] - datetime.datetime.now()).total_seconds()
                if time_difference > 0.0:
                    time.sleep(time_difference)
                self.market_buy(order)


if __name__ == "__main__":
    bot = AutoInvestBot()
    bot.main_loop()