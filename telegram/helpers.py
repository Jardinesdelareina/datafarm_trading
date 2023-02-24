from service.config_binance import GENERAL_BALANCE, AVAILABLE_BALANCE

START = '''
<b>Главное меню</b>
Здесь вы можете ознакомиться с описанием проекта <b>DataFarm</b>, изучить инструкцию по работе с алгоритмом, 
посмотреть баланс своего фьючерсного счета на бирже Binance, или приступить к настройке параметров торгового алгоритма.
'''

DESCRIPTION = '''
<em>
Здравствуйте!
<b>DataFarmBot</b> - это телеграм-интерфейс для удобного управления торговым алгоритмом <b>DataFarm</b>. 
Логика подхода к трейдингу в данной системе несколько отличается от наиболее распространенных на рынке
торговых стратегий. Поэтому разработчиком было принято решение вынести <b>DataFarm</b> в отдельную самостоятельную 
систему, а не помещять ее в библиотеку алгоритмов <b>Antrade</b>. К тому же, дополнительное отличие в том, что 
<b>DataFarm</b> предназначена для торговли фьючерсами, что само по себе подразумевает совершенно отличную от 
спотового рынка механику открытия ордеров.

Торговая стратегия, которая запрограммирована "под капотом" <b>DataFarm</b>, не подразумевает использование
каких-либо технических индикаторов, а исчисление времени происходит за рамками таймфреймов и ценовых свечей.
Единственным источником торговых сигналов является цена, обрабатываемая алгоритмом в реальном времени.

Удачной охоты!
</em>
'''

HELP = '''

'''

BALANCE = f'Общий баланс: <b>{GENERAL_BALANCE} USDT</b> \n Свободные средства: <b>{AVAILABLE_BALANCE} USDT</b>'
