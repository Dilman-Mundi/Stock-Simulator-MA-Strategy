from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
import yfinance as yf
import pandas as pd
import numpy as np
import json
import math
from dateutil.parser import parse
from openpyxl import load_workbook
from openpyxl.styles import Font

def getInput():
    placeHolders = {
        "ticker":"AAPL",
        "fsma":5,
        "ssma":20,
        "transaction_fee":5,
        "start_date":"",
        "end_date":"",
        "money":50000
    }

    for key in placeHolders.keys():
        temp = request.form.get(key, "")
        if temp:
            placeHolders[key] = temp

    placeHolders["ticker"] = placeHolders["ticker"].upper()
    placeHolders["ticker"] = placeHolders["ticker"].replace(" ", "")
    placeHolders["ticker"] = placeHolders["ticker"].replace(".","-")
    placeHolders["money"] = str(placeHolders["money"]).replace("$", "").replace(",", "")
    
    return placeHolders.values()

def validateInput(ticker, fSMA, sSMA, transaction_fee, start_date, end_date, money):
    check = []
    error = []
    #ticker
    stockName = []
    tickerList = ticker.split(",")
    for i in range(len(tickerList)):
        data = yf.Ticker(tickerList[i])
        try:
            info = data.get_info()
            stockName.append(info.get("shortName", None))
            if i == len(tickerList)-1:
                check.append(True)
                error.append(None)
        except:
            check.append(False)
            error.append("Invalid ticker: " + tickerList[i].replace("-", "."))
            break
        
    #fSMA & sSMA
    try:
        fSMA = int(fSMA)
        sSMA = int(sSMA)
        if fSMA>0 and sSMA>0 and fSMA < sSMA:
            check.append(True)
            check.append(True)
            error.append(None)
            error.append(None)
        elif fSMA<=0 and sSMA>0:
            check.append(False)
            check.append(True)
            error.append("fSMA must be greater than 0")
            error.append(None)
        elif fSMA<0 and sSMA<0 and fSMA < sSMA:
            check.append(False)
            check.append(False)
            error.append("fSMA must be greater than 0")
            error.append("sSMA must be greater than 0")
        else:
            check.append(False)
            check.append(False)
            error.append("fSMA must be lesser than sSMA")
            error.append("sSMA must be greater than fSMA")
    except:
        try:
            fSMA = int(fSMA)
            if fSMA > 0:
                check.append(True)
                error.append(None)
            else:
                check.append(False)
                error.append("fSMA must be greater than 0")
        except:
            check.append(False)
            error.append("fSMA must be a number")

        try:
            sSMA = int(sSMA)
            if sSMA > 0:
                check.append(True)
                error.append(None)
            else:
                check.append(False)
                error.append("sSMA must be greater than 0")
        except:
            check.append(False)
            error.append("sSMA must be a number")
    
    #transaction_fee
    try:
        transaction_fee = float(transaction_fee)
        if transaction_fee >= 0:
            check.append(True)
            error.append(None)
        else:
            check.append(transaction_fee>=0)
            error.append("Transaction fee must be >= 0")
    except: 
        check.append(False)
        error.append("Transaction fee must be a number")

    #start_date & end_date
    start_date = start_date.replace("-","")
    end_date = end_date.replace("-","")


    if start_date and end_date:
        start_date = int(start_date)
        end_date = int(end_date) 

        if (start_date < end_date and start_date <= int(datetime.today().strftime('%Y-%m-%d').replace("-",""))):
            check.append(True)
            check.append(True)
            error.append(None)
            error.append(None)
        else:
            if (start_date > end_date):
                check.append(False)
                check.append(False)
                error.append("Start date must be before the end date")
                error.append("End date must be after the start date")
            else:
                check.append(False)
                check.append(True)
                error.append("Start date can't be later than today")
                error.append(None)

    elif start_date:
        start_date = int(start_date)
        if start_date <= int(datetime.today().strftime('%Y-%m-%d').replace("-","")):
            check.append(True)
            check.append(True)
            error.append(None)
            error.append(None)
        else:
            check.append(False)
            check.append(True)
            error.append("Start date can't be later than today")
            error.append(None)
    else:
        check.append(True)
        check.append(True)
        error.append(None)
        error.append(None)

    #money
    try:
        money = float(money)
        check.append(money>0)
        error.append(None)
    except:
        check.append(False)
        error.append("Money must be a number")

    return check, error, stockName

def download_data(ticker, start_date, end_date):

    if start_date and end_date:
        data = yf.download(ticker, start=start_date, end=end_date)
    elif start_date:
        data = yf.download(ticker, start=start_date)
    elif end_date:
        data = yf.download(ticker, end=end_date)
    else:
        data = yf.download(ticker)

    return data

def stock_simulation(ticker, fSMA, sSMA, transaction_fee, start_date, end_date, money, plotDates, plotNetWorth):
    numOfTrades = 0
    prevMoney = money
    data = download_data(ticker, start_date, end_date)
    #calculating the average price movement every day
    data['fSMA'] = data['Close'].rolling(window=fSMA).mean()
    data['sSMA'] = data['Close'].rolling(window=sSMA).mean()
    data['Ans'] =  data['fSMA']-data['sSMA']

    #Looks at difference of SMA before, True if +, False if -
    sign = None
    numOfStocks = 0

    dates, prices, fsma_values, ssma_values, actions, shares_list, PL_list, net_worth_list = [], [], [], [], [], [], [], []

    for i in range(0,len(data)):
        curr = data.iloc[i]['Ans']['']
        price = data.iloc[i]['Close'][ticker]

        if np.isnan(curr) or curr == 0:
            continue
        if money/price < 1 and numOfStocks == 0:
            break

        #Buy signal
        if curr>0 and sign == False:
            numOfStocks = money//price
            money -= numOfStocks*price
            money -= transaction_fee
            numOfTrades+=1
            buyPrice = price
            
            dates.append(data.index[i].date())
            prices.append(f"{price: .2f}")
            fsma_values.append(f"{data.iloc[i]['fSMA']['']: .2f}")
            ssma_values.append(f"{data.iloc[i]['sSMA']['']: .2f}")
            actions.append("Buy")
            shares_list.append(numOfStocks)
            PL_list.append("-")
            net_worth_list.append(round(float(money+numOfStocks*price),2))

        #Sell signal
        elif curr<0 and sign == True:
            if not numOfStocks == 0:
                PL_list.append(round((price-buyPrice)*numOfStocks,2))

                money += numOfStocks*price
                numOfStocks = 0
                numOfTrades+=1

                dates.append(data.index[i].date())
                prices.append(f"{price: .2f}")
                fsma_values.append(f"{data.iloc[i]['fSMA']['']: .2f}")
                ssma_values.append(f"{data.iloc[i]['sSMA']['']: .2f}")
                actions.append("Sell")
                shares_list.append(numOfStocks)
                net_worth_list.append(round(float(money+numOfStocks*price),2))

        #Giving the previous curr a sign, given no transactions
        if curr>0:
            sign = True
        elif curr<0:
            sign = False
        plotDates.append(data.index[i].date())
        plotNetWorth.append(round(float(money+numOfStocks*price),2))

    df = pd.DataFrame({
        "Date": dates,
        "Price": prices,
        "fSMA": fsma_values,
        "sSMA": ssma_values,
        "Action": actions,
        "Shares": shares_list,
        "P/L": PL_list,
        "Net Worth": net_worth_list
    })

    max_points = 1000
    total_points = len(plotDates)
    if total_points > max_points:
        step = total_points // max_points
        plotDates = plotDates[::step]
        plotNetWorth = plotNetWorth[::step]
    
    transactions = numOfTrades
    netWorth = round(float(money+numOfStocks*data.iloc[-1]['Close'][ticker]),2)
    pL = round(netWorth - prevMoney,2)

    years = int(df["Date"].iloc[-1].year) - int(df["Date"].iloc[0].year) + 1
    ret = round(((netWorth / prevMoney) ** (1 / years) - 1)*100, 2)

    return df, plotDates, plotNetWorth, transactions, pL, ret

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/verifyInput", methods=['POST'])
def verifyInput():
    ticker, fSMA, sSMA, transaction_fee, start_date, end_date, money = getInput()
    valid, error, fullStockNames = validateInput(ticker, fSMA, sSMA, transaction_fee, start_date, end_date, money)

    if not all(valid):
        return jsonify({"success": False, "valid": valid, "errors": error})

    form_values = [ticker, int(fSMA), int(sSMA), int(transaction_fee), start_date, end_date, int(money), fullStockNames]
    return jsonify({"success": True, "valid": valid, "errors": error, "form_values": form_values})

@app.route("/runSimulation", methods=['POST'])
def runSimulation():
    ticker = request.form.get("ticker", None)
    fsma = int(request.form.get("fSMA", None))
    ssma = int(request.form.get("sSMA", None))
    transaction_fee = int(request.form.get("transaction_fee", 0))
    start_date = request.form.get("start_date", "")
    end_date = request.form.get("end_date", "")
    money = int(request.form.get("money", None))

    ticker_list = ticker.split(",")
    df = [0]*len(ticker_list)
    plotDates = [[] for _ in range(len(ticker_list))]
    plotNetWorth = [[] for _ in range(len(ticker_list))]

    transactions, pL, ret = [0]*len(ticker_list), [0]*len(ticker_list), [0]*len(ticker_list)

    for i in range(len(ticker_list)):
        df[i], plotDates[i], plotNetWorth[i], transactions[i], pL[i], ret[i] = stock_simulation(ticker_list[i], fsma, ssma, transaction_fee, start_date, end_date, money, [], [])
    
    return jsonify({"df": [d.to_dict(orient="records") for d in df], "plotDates": plotDates, "plotNetWorth": plotNetWorth, "transactions": transactions, "pL": pL, "ret": ret})

@app.route("/loadResults")
def loadResults():
    return render_template("results.html")

@app.route("/getTableValues", methods=['POST'])
def getTableValues():
    ans = []
    stockName = json.loads(request.form.get("fullStockNames"))
    transactions = json.loads(request.form.get("transactions"))
    pL = json.loads(request.form.get("pL"))
    ret = json.loads(request.form.get("ret"))

    for i in range(len(stockName)):
        ans.append({"stockName": stockName[i], "transactions": transactions[i], "PL": pL[i], "ret": ret[i]})
    
    return ans

@app.route("/plot", methods=['POST'])
def plot():
    data = []
    stockName = json.loads(request.form.get("fullStockNames"))
    plotDates = json.loads(request.form.get("plotDates"))
    plotNetWorth = json.loads(request.form.get("plotNetWorth"))

    for i in range(len(stockName)):
        sampled_dates = plotDates[i]
        sampled_networth = plotNetWorth[i]

        sampled_dates = [parse(d) for d in sampled_dates]

        data.append({
            "name": stockName[i],
            "x": [d.isoformat() for d in sampled_dates],
            "y": sampled_networth,
            "hover": [
                f"Date: {d}<br>Net Worth: ${v:,.2f}"
                for d, v in zip(sampled_dates, sampled_networth)
            ]
        })

    return jsonify(data)

@app.route('/download_excel', methods=['POST'])
def download_table():
    stockName = json.loads(request.form.get("fullStockNames"))
    tickers = request.form.get("tickers")
    fSMA = request.form.get("fsma")
    sSMA = request.form.get("ssma")
    df_json = json.loads(request.form.get('df_json'))  # this is now a list of lists of dicts
    df_list = []

    expected_columns = ["Date", "Price", "fSMA", "sSMA", "Action", "Shares", "P/L", "Net Worth"]
    df_list = [pd.DataFrame.from_records(stock)[expected_columns] for stock in df_json]

    for df in df_list:
        df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=False).dt.strftime("%Y-%m-%d")

    for stock in df_json:
        df_list.append(pd.DataFrame.from_records(stock))

    print(tickers,fSMA,sSMA)
    filename = f"{tickers}_{fSMA}_{sSMA}.xlsx"

    with pd.ExcelWriter(filename, engine = "openpyxl") as writer:
        for i in range(len(stockName)):
            df_list[i].to_excel(writer, sheet_name= stockName[i], index=False)

    wb = load_workbook(filename)
    for i in range(len(stockName)):
        sheet = wb[stockName[i]]

        for cell in sheet['G'][1:]:
            if not cell.value == "-":
                try:
                    if float(cell.value) > 0:
                       cell.font = Font(color = "FF217346")
                    elif float(cell.value) < 0:
                        cell.font = Font(color = "FFC00000")
                except:
                    break
    wb.save(filename)
    
    return send_file(filename, as_attachment=True, download_name=filename)

if __name__ == "__main__":
    app.run(debug=True)