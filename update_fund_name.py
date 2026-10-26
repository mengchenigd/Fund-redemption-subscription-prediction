import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from os import getcwd, chdir

def update_fund_name_table():
    df = pd.read_excel('fund_name_table.xlsx', usecols='B:J')
    chrome_options = Options() 
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu') 
    driver = webdriver.Chrome('chromedriver',options=chrome_options)

    industry_column = []
    area_column = []
    Sharp_column = []
    Beta_column = []
    St_column = []

    for name in df['基金名稱']:
        result = 0
        while result == 0:
            try:
                driver.get(f"https://www.cnyes.com/search/all?keyword={name}")
                button = driver.find_element(By.XPATH, '//*[@id="_SearchAll"]/section[1]/div[2]/a[1]/article')
                button.click()
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                current_url = driver.current_url
                document = current_url+'/document'
                driver.get(document)
                industry = driver.find_element(By.XPATH,'//*[@id="anue-ga-wrapper"]/div/div[2]/div[2]/main[2]/section/main/table[1]/tbody/tr[7]/td[2]')
                area = driver.find_element(By.XPATH,'//*[@id="anue-ga-wrapper"]/div/div[2]/div[2]/main[2]/section/main/table[1]/tbody/tr[6]/td[2]')
                risk = current_url+'/risk'
                industry_text,area_text = industry.text,area.text
                driver.get(risk)
                Sharp = driver.find_element(By.XPATH,'//*[@id="anue-ga-wrapper"]/div/div[2]/div[2]/main[2]/section/main/div/div[2]/table/tbody/tr[1]/td[1]')
                Beta = driver.find_element(By.XPATH,'//*[@id="anue-ga-wrapper"]/div/div[2]/div[2]/main[2]/section/main/div/div[2]/table/tbody/tr[2]/td[1]')
                St = driver.find_element(By.XPATH,'//*[@id="anue-ga-wrapper"]/div/div[2]/div[2]/main[2]/section/main/div/div[2]/table/tbody/tr[4]/td[1]')
                industry_column.append(industry_text)
                area_column.append(area_text)
                Sharp_column.append(Sharp.text)
                Beta_column.append(Beta.text)
                St_column.append(St.text)
                result = 1
            except:
                pass
    driver.quit()
    df['基金組別'] = industry_column
    df['投資地區'] = area_column
    df['夏普值'] = Sharp_column
    df['Beta值'] = Beta_column
    df['標準差'] = St_column
    df.to_excel("fund_name_table.xlsx")
