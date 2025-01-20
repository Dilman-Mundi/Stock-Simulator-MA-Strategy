import yfinance as yf
#import pandas as pd
import numpy as np

def download_data(stock, start_date, end_date):
    if '.' in stock:
        stock = stock.replace(".","-")

    if not start_date and not end_date:
        data = yf.download(stock)
    elif start_date:
        data = yf.download(stock, start=start_date)
    else:
        data = yf.download(stock, end=end_date)

    return data

def main():
    #Should be input (get input function)
    money = 10000
    stock = "AAPL"
    fSMA = 5
    sSMA = 20
    transaction_fee = 5
    #Max if not stated
    start_date = '2010-01-02'
    #Max if not stated
    end_date = ''

    numOfTrades = 0

    data = download_data(stock, start_date, end_date)

    #calculating the average price movement every day
    data['fSMA'] = data['Close'].rolling(window=fSMA).mean()
    data['sSMA'] = data['Close'].rolling(window=sSMA).mean()
    data['Ans'] =  data['fSMA']-data['sSMA']

    #Looks at difference of SMA before, True if +, False if -
    sign = None
    numOfStocks = 0
    for i in range(0,len(data)):
        curr = data.iloc[i]['Ans']['']
        price = data.iloc[i]['Close']['AAPL']

        if np.isnan(curr) or curr == 0:
            continue
        if money/price < 1 and numOfStocks == 0:
            print(f"Inadequate funds on: {data.index[i].date()} you have ${money}, {stock} price: {price}")
            break

        #Buy signal
        if curr>0 and sign == False:
            numOfStocks = money//price
            money -= numOfStocks*price
            money -= transaction_fee
            numOfTrades+=1
        #Sell signal
        elif curr<0 and sign == True:
            if not numOfStocks == 0:
                money += numOfStocks*price
                numOfStocks = 0
                money -= transaction_fee
                numOfTrades+=1

        #Giving the previous curr a sign, given no transactions
        if curr>0:
            sign = True
        elif curr<0:
            sign = False

    print(money,numOfTrades)
    #data.iloc[4]['SMA_5']['']

    #print(data.loc['1980-12-12']['Close']['AAPL'])
    #print(data.iloc[0]['Close']['AAPL'])


    '''
    import time
    start_time = time.time()
    print("--- %s seconds ---" % (time.time() - start_time))
    '''

if __name__ == "__main__":
    main()