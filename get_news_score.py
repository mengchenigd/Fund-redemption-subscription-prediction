import re
import requests
import csv
import time
import json
import datetime
import pandas as pd
from snownlp import SnowNLP
from bs4 import BeautifulSoup

headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18362',
    }

news_titles = []
news_date = []
news_content = []
news_tags = []

#save news information in excel
def savefile(news_titles,news_date,news_tags,news_content):
    print(f'標題筆數: {len(news_titles)}')
    print(f'日期筆數: {len(news_date)}')
    print(f'標籤筆數: {len(news_tags)}')  
    print(f'內文筆數: {len(news_content)}')  
    df = pd.DataFrame({'標題':news_titles,'日期':news_date,'標籤':news_tags,'內文':news_content})
    df.to_excel("previous_month_news.xlsx")

def parse(headers,newsID,num,total):
    content_list = []
    tags_list = []
    fnews_url = 'https://news.cnyes.com/news/id/{}?exp=a'.format(newsID)

    for attempt in range(3):
        try:
            res = requests.get(fnews_url, headers=headers, timeout=(10,30)) 
            res.raise_for_status
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
            print(f'第{attempt+1}次連線失敗:{fnews_url}')
            print(e)
            if attempt==2:
                raise
            time.sleep(3)
    soup = BeautifulSoup(res.text, 'html.parser')

    titles = soup.select('article h1')
    date = soup.select('article time')
    content = soup.select('#article-container p')
    tags = soup.select('.t1jl5nqd a') 

    if titles:
        for title in titles:
            news_titles.append(title.get_text(strip=True))
    else:
        news_titles.append("")

    if date:
        for item in date:
            news_date.append(item.get_text(strip=True)[:10])
    else:
        news_date.append("")

    for p in content:
        text=p.get_text(strip=True)
        if text:
            content_list.append(text)
    news_content.append(content_list)

    for tag in tags:
        tags_list.append(tag.get_text(strip=True))
    news_tags.append(tags_list)
 
    if num == total:
        savefile(news_titles,news_date,news_tags,news_content)

def crawler(beginday,stopday):   
    be_day=beginday
    st_day=stopday
    startday = int(datetime.datetime.timestamp(datetime.datetime.strptime(be_day, "%Y-%m-%d")))
    endday = int(datetime.datetime.timestamp(datetime.datetime.strptime(st_day, "%Y-%m-%d"))-1)
    url ='https://api.cnyes.com/media/api/v1/newslist/category/fund?startAt={}&endAt={}&limit=30'.format(startday,endday)
    res = requests.get(url, headers)

    newsID_lt=[]
    last_page = json.loads(res.text)['items']['last_page']
    total = json.loads(res.text)['items']['total']
    newsIDlist=json.loads(res.text)['items']['data']
    for i in newsIDlist:
        newsID=i['newsId']
        newsID_lt.append(newsID)
    time.sleep(0.5)

    for p in range(2,last_page+1):
        oth_url ='https://api.cnyes.com/media/api/v1/newslist/category/fund?startAt={}&endAt={}&limit=30&page={}'.format(startday,endday,p)
        res=requests.get(oth_url, headers)
        newsIDlist=json.loads(res.text)['items']['data']
        for j in newsIDlist:        
            newsID=j['newsId']
            newsID_lt.append(newsID)
        time.sleep(0.5)
    
    for k,n in enumerate(newsID_lt): 
        data=parse(headers,n,k+1,total)
        time.sleep(0.5)

def main(beginyear,beginmonth,crawlrange,stopmonth=12):
    #確認抓上半月或下半月
    if crawlrange==1:
        #抓上半個月
        for m in range(beginmonth,stopmonth+1):        
            if m < 10:
                beginday='{}-0{}-01'.format(beginyear,m)
                stopday='{}-0{}-16'.format(beginyear,m)
            else:
                beginday='{}-{}-01'.format(beginyear,m)
                stopday='{}-{}-16'.format(beginyear,m)
            crawler(beginday,stopday)
            if m ==12:
                break
            time.sleep(5)

    elif crawlrange==2:
        #抓下半個月
        for m in range(beginmonth,stopmonth+1):
            beginday='{}-0{}-16'.format(beginyear,m)  
            if m == 9:        
                stopday='{}-{}-01'.format(beginyear,m+1)
            elif m >= 10:
                beginday='{}-{}-16'.format(beginyear,m)
                if m == 12:
                    stopday='{}-01-01'.format(beginyear+1)
                else:
                    stopday='{}-{}-01'.format(beginyear,m+1)
            else:
                stopday='{}-0{}-01'.format(beginyear,m+1)
            
            crawler(beginday,stopday)
            if m ==stopmonth:
                break
            time.sleep(5)
    else:
        print('爬取區間設定錯誤!')

def get_news():
    beginyear=int(str(datetime.date.today().replace(day=1) - datetime.timedelta(days=1))[0:4])
    beginmonth= int(str(datetime.date.today().replace(day=1) - datetime.timedelta(days=1))[5:7])
    stopmonth=beginmonth
    for i in range(1,3):
        main(beginyear,beginmonth,i,stopmonth)

def append_score_with_SnowNLP():
    file = pd.read_excel("previous_month_news.xlsx")
    score_list = []
    num = len(file)
    for i in range(0,num):
        total_score = 0
        total = 0
        text1 = file["內文"][i]

        if not isinstance(text1,str):
            score_list.append(None)
            continue
        for word in text1:
            if word in "】【、：\n''（）;；()[]abcdefghijklmnopqrstuvwxyz\\:/F＊":
                text1 = text1.replace(word,'')
        text1=text1.strip()

        if not text1:
            score_list.append(None)
            continue

        s = SnowNLP(text1)
        for sentence in s.sentences:
            if sentence in sentence.strip():
                total_score += SnowNLP(sentence).sentiments
                total += 1

        score = total_score/total if total>0 else None
        score_list.append(score)

    file['score'] = score_list
    file.to_excel("previous_month_news.xlsx")

def get_news_score(fundname):
    get_news()
    append_score_with_SnowNLP()
    file = pd.read_excel("previous_month_news.xlsx",usecols='E,G')
    fund_name_table = pd.read_excel('fund_name_table.xlsx',usecols='B,C:D,J')
    tags_table = pd.read_excel('tags_table.xlsx',usecols='B:E')
    fund = fund_name_table.loc[fund_name_table['基金名稱']==fundname] 
    fund_tag_list = [fund['基金組別'].item(),fund['投資地區'].item(),fund['發行公司'].item()]
    tag_df = tags_table.loc[tags_table['基金組別']==fund_tag_list[0]]
    t2 = tags_table.loc[tags_table['投資地區']==fund_tag_list[1]]
    t3 = tags_table.loc[tags_table['發行公司']==fund_tag_list[2]]
    if (len(tag_df)>0) & (len(t2)>0):
        tag_df = pd.concat([tag_df,t2], join='inner')
    if (len(tag_df)>0) & (len(t3)>0):
        tag_df = pd.concat([tag_df,t3], join='inner')
    if (len(t2)>0) & (len(t3)>0):
        tag_df = pd.concat([t2,t3], join='inner')
    scores = []
    for i in range(len(file)):
        tag_list = re.sub(r"\]|\[|\'|\ ","",file.loc[i,'標籤']).split(',')
        if any(x in tag_list for x in list(tag_df['標籤名稱'])) :
            scores.append(file.loc[i,'score'])
            
    if len(scores) == 0:
        score = 0
    else:
        score = sum(scores) / len(scores)
    return score
