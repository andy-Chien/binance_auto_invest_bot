import os
import time
import yaml
import zipfile
import getpass
import logging
import datetime
import argparse
from binance.spot import Spot
from binance.error import ClientError

class AutoInvestBot:
    def __init__(self, cfg_fname):
        self.logger = logging.getLogger("logger")
        c_handler = logging.StreamHandler()
        self.logger.addHandler(c_handler)
        self.logger.setLevel(logging.DEBUG)

        pkg_path = os.path.dirname(os.path.abspath(__file__)) + '/../'
        cfg_path = pkg_path + 'config/' + cfg_fname
        if not os.path.exists(cfg_path):
            cfg_path, _ = os.path.splitext(cfg_path)
            if not os.path.exists(cfg_path):
                raise ValueError(f"Config file not found: {cfg_path}")

        self.history_dir = pkg_path + 'trading_history/'

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
        now = datetime.datetime.now()
        zp = lambda x: '0' + str(x) if x < 10 else x
        ny, nm, nd = now.year, zp(now.month), zp(now.day)
        nh, nmi, ns = zp(now.hour), zp(now.minute), zp(now.second)
        try:
            res = self.client.new_order(**params)
            fill = res['fills'][-1]
            trade_info = ('{}/{}/{}, {}:{}:{}, {}, '
                'status: {}, price: {}, qty: {}, amount: {} \n'
                ).format(ny, nm, nd, nh, nmi, ns,
                res['symbol'], res['status'], fill['price'],
                res['executedQty'], res['cummulativeQuoteQty']
            )
            self.logger.info(trade_info)
            with open(self.history_dir + '{}_{}'.format(ny, nm) + '.history.txt', 'a') as file:
                file.write(trade_info)
            
        except ClientError as error:
            trade_info = ('[Error]. {}/{}/{}, {}:{}:{}, {}, '
                'status: {}, error code: {}, error message: {} \n'
                ).format(ny, nm, nd, nh, nmi, ns,
                order['symbol'], error.status_code,
                error.error_code, error.error_message
            )
            if error.error_code == -1013:
                trade_info += ', Order amount is too low!'
            self.logger.error(trade_info)
            with open(self.history_dir + '{}_{}'.format(ny, nm) + '.history.txt', 'a') as file:
                file.write(trade_info)
        except:
            trade_info = ('[Warn]. {}/{}/{}, {}:{}:{}, {}, '
                'Server issues, Trying to connect to antoher server.'
                ).format(ny, nm, nd, nh, nmi, ns, order['symbol']
            )
            self.logger.warning(trade_info)
            with open(self.history_dir + '{}_{}'.format(ny, nm) + '.history.txt', 'a') as file:
                file.write(trade_info)
            self.change_base_url()
            self.market_buy(order)

    def main_loop(self):
        while self.update_sys_time():
            closest_time = float('inf')
            seconds_30 = 30.0
            tmp_order_list = []
            for order in self.order_list:
                time_difference = \
                    (order['sys_time'] - datetime.datetime.now()).total_seconds()
                if time_difference < closest_time:
                    closest_time = time_difference
                if time_difference < seconds_30:
                    tmp_order_list.append(order)

            if seconds_30 < closest_time < float('inf'):
                time.sleep(closest_time - seconds_30)

            for order in tmp_order_list:
                time_difference = \
                    (order['sys_time'] - datetime.datetime.now()).total_seconds()
                if time_difference > 0.0:
                    time.sleep(time_difference)
                self.market_buy(order)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Auto invest bot via Binance API.')
    parser.add_argument('cfg_fname', default='cfg.yaml.zip', nargs='?', type=str,
                        help='Name of config file.')
    args = parser.parse_args()

    bot = AutoInvestBot(args.cfg_fname)
    bot.main_loop()