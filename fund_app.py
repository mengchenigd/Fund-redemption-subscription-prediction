import tkinter as tk
from update_fund_name import update_fund_name_table
import pandas as pd
app = tk.Tk() 
from Crawler_FinTech import job

#add app title
app.title("Fund Redemption and Subscription System")
app.geometry('500x330')
app.resizable(False,False) 

def callbackFunc():
    aaa = job(fundString3.get())
    resultLabel=tk.Label(app, text=aaa).place(x=5,y=100)
    
def loading():
    load = tk.Label(app,text = "更新中...",font=('Arial', 16,'bold','underline'),fg='Crimson').place(x=150, y=260)
    update_fund_name_table()
    fin = tk.Label(app,text = "完成！",font=('Arial', 16,'bold','underline'),fg='Crimson').place(x=150, y=260)
    
labelapp = tk.Label(app,text = "Fund Redemption and Subscription Prediction System",font=('Arial', 16,'bold','underline'),fg='Crimson').place(x=25, y=20)
interval_text = "="*60
interval = tk.Label(app,text = interval_text,font=('Arial'),fg='Crimson').place(x=8, y=240)
        
#update fund basic information
resultButton2 = tk.Button(app, text = 'Update fund info',command=loading).place(x=15,y=260)
annotation1 = tk.Label(app,text = "＊更新基金特徵資料(送入模型的變數)",font=('Arial',10)).place(x=15, y=290)

#search for fund redemption and subscription recommendation
labelfund3 = tk.Label(app,text = "Fund Name",font=('Arial')).place(x=15, y=60)
fundString3 = tk.StringVar()
entryfund3= tk.Entry(app, width=20, textvariable=fundString3).place(x=105,y=57.5)
resultButton3 = tk.Button(app, text = 'Search',command=callbackFunc).place(x=305,y=57.5)

app.mainloop()