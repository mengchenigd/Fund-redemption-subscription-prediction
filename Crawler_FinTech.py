from math import log
import pandas as pd
import time
import requests
import datetime
import urllib
import numpy as np
import yfinance as yf
import pickle 
from os import getcwd, chdir
from get_news_score import *
from update_fund_name import *
from pathlib import Path

# change cwd to your working directory
cwd = r"/Users/yangmengkui/Desktop/Profile/Redemption prediction project"
chdir(cwd)

class Crawler:
    def __init__(self):
        self.vix_dict = {}
        self.currency_dict = {}
        self.future_price_oi_url = 'https://stock.wearn.com/taifexphoto.asp'
        self.lend_url = 'https://histock.tw/stock/three.aspx?m=mg'

        self.data_forMLP = None  # data for MLP
        self.data_forLR = None  # data for Logistic Regression

    def get_vix_raw_data(self):
        base = datetime.datetime.today().date()
        if base.month==1:
            last_month = str(base.year-1) + str(12)
            month_list = [int(base.strftime('%Y%m')),int(last_month)]
        else:
            month_list=  [int(base.strftime('%Y%m')),int(base.strftime('%Y%m'))-1]
        for i in month_list[::-1]:
            try:
                vix_url = 'https://www.taifex.com.tw/file/taifex/Dailydownload/vix/log2data/'+str(i)+'new.txt'
                file = urllib.request.urlopen(vix_url)
                
                for line in file:  
                    decoded_line = line.decode("big5")
                    try:
                        self.vix_dict[decoded_line.split('\t')[-7].strip()] = float(decoded_line.split('\t')[-3].strip())
                    except ValueError:
                        pass
            except UnicodeDecodeError :
                pass
        return self.vix_dict
    
    def vix_data_processing(self):
        vix_dict = self.get_vix_raw_data()
        vix_df = pd.DataFrame(vix_dict.items())
        
        # Process data...
        for i in range(1, len(vix_df)):
            vix_df.loc[i, 'VIX_logReturns_annualized'] = log(vix_df.loc[i, 1]/vix_df.loc[i-1, 1])*250
        vix_df['VIX_5DMA_annualized'] = vix_df['VIX_logReturns_annualized'].rolling(5).mean()
        vix_df = vix_df.drop(vix_df.columns[1], axis=1)
        vix_df = vix_df.dropna()

        return vix_df
    
    def price_oi_data_processing(self):  # future_price_oi_url
        price = pd.read_html(self.future_price_oi_url)[0]
        price = price.drop(0)
        price = price.reset_index(drop=True)
        new_header = price.iloc[0]  # grab the first row for the header
        price = price[1:]  # take the data less the header row
        price.columns = new_header  # set the header row as the df header
        price = price.reset_index(drop=True)

        price = price[['日期', '收盤']]
        price = price.sort_values(by='日期')
        price = price.reset_index(drop=True)

        # Process data...
        for i in range(len(price)):
            price.loc[i, '收盤'] = int(price.loc[i, '收盤'])
            if i >= 1:
                price.loc[i, 'TAIEX_logReturns_annualized'] = log(price.loc[i, '收盤']/price.loc[i-1, '收盤'])*250
        price['TAIEX_5DMA_annualized'] = price['TAIEX_logReturns_annualized'].rolling(5).mean()
        price['TAIEX_20DMA_annualized'] = price['TAIEX_logReturns_annualized'].rolling(20).mean()

        # RSV_9D
        price['max_price'] = price['收盤'].rolling(9).max()
        price['min_price'] = price['收盤'].rolling(9).min()
        price['RSV_9D'] = 100*(price['收盤']  - price['min_price'])/(price['max_price'] - price['min_price'])
        
        # KD
        price.loc[8, 'K'] = 0
        price.loc[8, 'D'] = 0
        for i in range(9, len(price)):
            price.loc[i, 'K'] = price.loc[i-1, 'K']*0.67 + price.loc[i, 'RSV_9D']*0.33
            price.loc[i, 'D'] = price.loc[i-1, 'D']*0.67 + price.loc[i, 'K']*0.33

        price = price.drop(['收盤', 'max_price', 'min_price'], axis = 1)
        price = price.dropna()

        return price
    
    def lend_data_processing(self):
        lend_df = pd.read_html(self.lend_url)[0]
        lend_df = lend_df.sort_values(by='日期')
        
        # Process data...
        lend_df['融資餘額變動率'] = lend_df['融資餘額(億)'].pct_change()
        lend_df = lend_df[['日期', '融資餘額變動率']]
        lend_df = lend_df.dropna()

        return lend_df

    def extract_data_today(self, vix_df, lend_df, price_oi_df):
        '''
        Preprocess given datas for each model.
            Outputs:
                self.data_forMLP
                self.data_forLR
        '''

        data_today = pd.DataFrame()
        data_today.loc[0, 'TAIEX_logReturns_annualized'] = price_oi_df.iloc[-1]['TAIEX_logReturns_annualized']
        data_today.loc[0, 'TAIEX_5DMA_annualized'] = price_oi_df.iloc[-1]['TAIEX_5DMA_annualized']
        data_today.loc[0, 'TAIEX_20DMA_annualized'] = price_oi_df.iloc[-1]['TAIEX_20DMA_annualized']
        data_today.loc[0, 'RSV_9D'] = price_oi_df.iloc[-1]['RSV_9D']
        data_today.loc[0, 'K'] = price_oi_df.iloc[-1]['K']
        data_today.loc[0, 'D'] = price_oi_df.iloc[-1]['D']
        data_today.loc[0, 'VIX_logReturns_annualized'] = vix_df.iloc[-1]['VIX_logReturns_annualized']
        data_today.loc[0, 'VIX_5DMA_annualized'] = vix_df.iloc[-1]['VIX_5DMA_annualized']
        data_today.loc[0, '融資餘額變動率'] = lend_df.iloc[-1]['融資餘額變動率']

        # MLP model's data
        data_forMLP = data_today[['TAIEX_5DMA_annualized', 'TAIEX_20DMA_annualized', 'RSV_9D', 'K', 'D', 'VIX_5DMA_annualized', '融資餘額變動率']].copy()
        self.data_forMLP = data_forMLP

        # LR model's data
        data_forLR = data_today[['TAIEX_5DMA_annualized', 'TAIEX_20DMA_annualized', 'RSV_9D', 'K', 'D', 'VIX_5DMA_annualized', '融資餘額變動率']].copy()
        self.data_forLR = data_forLR

    def execute(self):
        print('Start crawling data...')
        vix_df = self.vix_data_processing()
        lend_df = self.lend_data_processing()
        price_oi_df = self.price_oi_data_processing()
        print('Finished crawling data.')

        print('Start preprocessing data...')
        self.extract_data_today(vix_df, lend_df, price_oi_df)
        print('Finished preprocessing data.')

class Models:
    def __init__(self, crawler, fund_name):
        self.data_forMLP = crawler.data_forMLP
        self.data_forLR = crawler.data_forLR
        self.fund_name = fund_name
        self.value_missing = True
        
    def integrate_data(self):
        main = pd.DataFrame()
        main.loc[0, '基金名稱'] = self.fund_name
        
        ###
        # by fund name get fund data
        ###
        folder=Path(__file__).resolve().parent
        fund_name = pd.read_excel(folder/'fund_name_table.xlsx')
        main = pd.merge(left = main, right = fund_name, right_on = '基金名稱', left_on = '基金名稱')
        main = main.drop(['基金組別', '投資地區', 'Beta值', '基金檔數', '交易總額', '發行公司'], axis = 1)

        # merge with crawled data
        self.data_forMLP = pd.merge(left = main, right = self.data_forMLP, left_index = True, right_index = True)
        self.data_forLR = pd.merge(left = main, right = self.data_forLR, left_index = True, right_index = True)

        # by fund name get news score
        print('Start getting news score...')
        news_score = get_news_score(self.fund_name)
        print('Finished getting news score.')
        self.data_forMLP.loc[0, 'Score of prev Month'] = news_score
        self.data_forLR.loc[0, 'Score of prev Month'] = news_score
        
        # if there's missing value in fund data..
        # MLP
        if self.data_forMLP.loc[0, '夏普值'] == '--' or self.data_forMLP.loc[0, '標準差'] == '--%':
            self.data_forMLP = self.data_forMLP.drop(['夏普值', '標準差'], axis = 1)
            self.value_missing = True
        else:
            # convert data type
            self.data_forMLP.loc[0, '標準差'] = float(self.data_forMLP.loc[0, '標準差'].strip('%'))/100
            self.data_forMLP.loc[0, '夏普值'] = float(self.data_forMLP.loc[0, '夏普值'])
            self.value_missing = False
        
        # LR
        if self.value_missing == True:
            self.data_forLR = self.data_forLR.drop(['夏普值', '標準差'], axis = 1)
        else:
            # convert data type
            self.data_forLR.loc[0, '標準差'] = float(self.data_forLR.loc[0, '標準差'].strip('%'))/100
            self.data_forLR.loc[0, '夏普值'] = float(self.data_forLR.loc[0, '夏普值'])

        # drop value and convert to list to fit ML model
        self.data_forMLP = self.data_forMLP.drop(['基金名稱', self.data_forMLP.columns[1]], axis = 1)
        self.data_forMLP = self.data_forMLP.iloc[0].to_list()

        self.data_forLR = self.data_forLR.drop(['基金名稱', self.data_forLR.columns[1]], axis = 1)
        self.data_forLR = self.data_forLR.iloc[0].to_list()

    # ==================== Multi-Layer Perceptron ====================
    def predict_mlp(self):
        data_today = self.data_forMLP
        with open('Multi-Layer_Perceptron', 'rb') as f:
            mlp = pickle.load(f)
            SUBorRED = mlp.predict([data_today])
            
        if SUBorRED == 1:
            return '(Multi-layer Perceptron Classifier) Predicted Outcome : Subscription'
        else:
            return '(Multi-layer Perceptron Classifier) Predicted Outcome : Redemption'
    
    # value-missing ver.
    def predict_mlp_value_missing(self):
        data_today = self.data_forMLP
        with open('Multi-Layer_Perceptron_missing', 'rb') as f:
            mlp = pickle.load(f)
            SUBorRED = mlp.predict([data_today])
            
        if SUBorRED == 1:
            return '(Multi-layer Perceptron Classifier) Predicted Outcome : Subscription'
        else:
            return '(Multi-layer Perceptron Classifier) Predicted Outcome : Redemption'

    # ==================== Logistic Regression ====================
    # for SUB
    def predict_lr_SUB(self):
        data_today = self.data_forLR
        with open('Logistic_Regression_SUB', 'rb') as f:
            lr = pickle.load(f)
            SUBorRED = lr.predict([data_today])
            probs = lr.predict_proba([data_today])
            probs = probs.tolist()
            
        return f'(Logistic Regression) Predicted probabiliy of subscription = {round(probs[0][1], 2)}'
    
    # value-missing ver.
    def predict_lr_SUB_value_missing(self):
        data_today = self.data_forLR
        with open('Logistic_Regression_SUB_missing', 'rb') as f:
            lr = pickle.load(f)
            SUBorRED = lr.predict([data_today])
            probs = lr.predict_proba([data_today])
            probs = probs.tolist()
            
        return f'(Logistic Regression) Predicted probabiliy of subscription = {round(probs[0][1], 2)}'
    
    # for RED
    def predict_lr_RED(self):
        data_today = self.data_forLR
        with open('Logistic_Regression_RED', 'rb') as f:
            lr = pickle.load(f)
            SUBorRED = lr.predict([data_today])
            probs = lr.predict_proba([data_today])
            probs = probs.tolist()
            
        return f'(Logistic Regression) Predicted probabiliy of redemption = {round(probs[0][1], 2)}'
    
    # value-missing ver.
    def predict_lr_RED_value_missing(self):
        data_today = self.data_forLR
        with open('Logistic_Regression_RED_missing', 'rb') as f:
            lr = pickle.load(f)
            SUBorRED = lr.predict([data_today])
            probs = lr.predict_proba([data_today])
            probs = probs.tolist()
            
        return f'(Logistic Regression) Predicted probabiliy of redemption = {round(probs[0][1], 2)}'

def job(fund_name):
    # crawl data
    crawl = Crawler()
    crawl.execute()
    models = Models(crawl, fund_name)

    # integrate data
    models.integrate_data()

    # predict with models
    if models.value_missing == False:
        print('All good. Start fitting model...')
        equalLine = "=" * 60 + "\n"
        dashLine = "-" * 60 + "\n"
        text = f"[ Red / Sub Trend Prediction ]\n{equalLine}" + f"{models.predict_lr_SUB()}\n{dashLine}{models.predict_lr_RED()}\n{dashLine}{models.predict_mlp()}\n"
        print(text)
    else:
        print('All good. Start fitting model...')
        equalLine = "=" * 60 + "\n"
        dashLine = "-" * 60 + "\n"
        text = f"[ Red / Sub Trend Prediction ]\n{equalLine}" + f"{models.predict_lr_SUB_value_missing()}\n{dashLine}{models.predict_lr_RED_value_missing()}\n{dashLine}{models.predict_mlp_value_missing()}\n"
        print(text)
    return text

def change_directory(path):
    path = input()
    chdir(path)

if __name__=="__main__":
    fund_name = input('輸入基金名稱:\n')
    job(fund_name)

