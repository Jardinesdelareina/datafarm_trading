import asyncio, requests, os
import pandas as pd
import plotly.graph_objects as go
import plotly.graph_objs as gos
from binance import BinanceSocketManager
from binance.helpers import round_step_size
from datafarm.config_binance import CLIENT
from datafarm.utils import round_list, remove_file, round_float
from telegram.config_telegram import TELETOKEN, CHAT_ID

online = True
closed = False


def bot_off() -> bool:
    """ Остановка алгоритма
    """
    global online
    online = False
    

def bot_closed() -> bool:
    """ Продажа по рынку
    """
    global closed
    closed = True


def start_single_bot(symbol, qnty):
    """ Запуск алгоритма извне по одному выбранному тикеру
    """
    global online
    online = True
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(Datafarm(symbol, qnty).socket_stream())


class Datafarm:
    """ Базовый класс, содержащий инфраструктуру обработки данных, торговую стратегию, 
        построенную на основе полученных данных и логику взаимодействия с API Binance.
    """

    # Наличие открытой позиции в рынке
    OPEN_POSITION = False

    # Процент дистанции от экстремума
    PERCENT_BUY = 0.01
    PERCENT_SELL = 0.007

    # Рабочий временной диапазон
    TIME_RANGE = 1


    def __init__(self, symbol, qnty=15):
        """ Конструктор класса Datafarm

            symbol (str): Тикер криптовалютной пары

            qnty (float): Объем ордера, по-умолчанию 15

            __last_signal (str): Текстовое сообщение о торговом сигнале, передаваемое как 
                                уведомление в Telegram и в терминал.

            __last_log (str): Текстовое уведомление, логирующее работу алгоритма в состоянии
                            ожидания торгового сигнала.

            ** __last_signal и __last_log служат для предотвращения дублирования уведомлений
            при поступающих через вебсокеты идентичных данных.
        """
        self.symbol = symbol.upper()
        self.qnty = qnty
        self.data_file = f'{self.symbol}.csv'
        self.__last_signal = None
        self.__last_log = None


    def send_message(self, message: str):
        """ Уведомления в Telegram 
        """
        return requests.get(
            f'https://api.telegram.org/bot{TELETOKEN}/sendMessage', 
            params=dict(chat_id=CHAT_ID, text=message)
        )


    def calculate_quantity(self) -> float:
        """ Расчет объема ордера 
        """
        symbol_info = CLIENT.get_symbol_info(self.symbol)
        step_size = symbol_info.get('filters')[1]['stepSize']
        order_volume = self.qnty / self.last_price
        order_volume = round_step_size(order_volume, step_size)
        return order_volume


    def place_order(self, order_side: str):
        """ Размещение ордеров
            
            order_side (str): Направление ордера, передаваемое при вызове функции в алгоритме.
        """

        if order_side == 'BUY':
            order = CLIENT.create_order(
                symbol=self.symbol, 
                side='BUY', 
                type='MARKET', 
                quantity=self.calculate_quantity(),
            )
            self.OPEN_POSITION = True
            self.buy_price = round(
                float(order.get('fills')[0]['price']), 
                round_float(num=self.last_price)
            )
            message = f'{self.symbol} \n Buy \n {self.buy_price}'
            self.send_message(message)
            print(message)

        elif order_side == 'SELL':
            order = CLIENT.create_order(
                symbol=self.symbol, 
                side='SELL', 
                type='MARKET', 
                quantity=self.calculate_quantity(),
            )
            self.OPEN_POSITION = False
            self.sell_price = round(
                float(order.get('fills')[0]['price']), 
                round_float(num=self.last_price)
            )
            result = round(((self.sell_price - self.buy_price) * self.calculate_quantity()), 2)
            message = f'{self.symbol} \n Sell \n {self.sell_price} \n Результат: {result} USDT'
            self.send_message(message)
            print(message)


    def create_frame(self, stream):
        """ Получение данных, сохранение их в виде таблицы в файл формата .csv
            чтение файла с данными и построение стратегии на основе полученных данных

            Структура таблицы файла .csv:
            
            Symbol (str): Название тикера
            Time (datetime): Время поступления данных
            Price (float): Значение цены тикера
            stream (dict): Данные, поступающие через вебсокеты
        """
        global closed

        # Запись
        df = pd.DataFrame(stream['data'], index=[0])
        df = df.loc[:,['s', 'E', 'p']]
        df.columns = ['Symbol', 'Time', 'Price']
        df.Time = pd.Series(pd.to_datetime(df.Time, unit='ms', utc=True)).dt.strftime('%Y-%m-%d %H:%M:%S')
        df.Price = round(df.Price.astype(float), round_list[f'{self.symbol}'])
        with open(self.data_file, 'a') as f:
            if os.stat(self.data_file).st_size == 0:
                df.to_csv(f, mode='a', header=True, index=False)
            else:
                df.to_csv(f, mode='a', header=False, index=False)

        # Чтение
        df_csv = pd.read_csv(f'{self.symbol}.csv')
        df_csv.Time = pd.to_datetime(df_csv.Time)
        self.last_price = df_csv.Price.iloc[-1]
        time_period = df_csv[df_csv.Time > (df_csv.Time.iloc[-1] - pd.Timedelta(hours=self.TIME_RANGE))]
        
        signal_buy = round(
            (time_period.Price.min() + (time_period.Price.min() * self.PERCENT_BUY)),
            round_float(num=self.last_price)
        )
        signal_sell = round(
            (time_period.Price.max() - (time_period.Price.max() * self.PERCENT_SELL)),
            round_float(num=self.last_price)
        )


        def report_signal(order_side):
            """ Логирование сигнала
            """
            message = f'{self.symbol} {order_side}'
            if message != self.__last_signal:
                print(message)
                self.__last_signal = message


        def report_log(order_side):
            """ Логирование ожидания сигнала
            """
            signal = signal_buy if not self.OPEN_POSITION else signal_sell
            message = f'{self.symbol}: {self.last_price} {order_side}: {signal}'
            if message != self.__last_log:
                print(message)
                self.__last_log = message


        if not self.OPEN_POSITION:
            if self.last_price > signal_buy:
                self.place_order('BUY')
                remove_file(self.data_file)
                report_signal('BUY')
            else:
                report_log('BUY')

        if self.OPEN_POSITION:
            if (self.last_price < signal_sell) or closed:
                self.place_order('SELL')
                remove_file(self.data_file)
                report_signal('SELL')
            else:
                report_log('SELL')


    def report_graph(self):
        df_gph = pd.read_csv(self.data_file)
        chart = go.Scatter(
            x=df_gph.Time, 
            y=df_gph.Price,
            mode='lines', 
            line=dict(width=2), 
            marker=dict(color='blue')
        )
        layout = go.Layout(
            title=self.symbol,
            yaxis=dict(side='right', showgrid=False, zeroline=False),
            xaxis=dict(showgrid=False, zeroline=False),
        )
        data = [chart]
        fig = go.Figure(data=data, layout=layout)
        fig.write_image('report.png')


    async def socket_stream(self):
        """ Подключение к потоку Binance через вебсокеты
        """
        global online
        bm = BinanceSocketManager(client=CLIENT)
        ts = bm.symbol_mark_price_socket(self.symbol, fast=False)
        async with ts as tscm:
            while online:
                res = await tscm.recv()
                if res:
                    self.create_frame(res)
                await asyncio.sleep(0)
            if not online:
                remove_file(self.data_file)
