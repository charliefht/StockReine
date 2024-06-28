#打开对应股票的历史数据
from bs4 import BeautifulSoup
import re
import pandas as pd
import requests
import logging
from flask import Flask, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import json


app = Flask(__name__)

# 定义一个函数来获取数据并检查响应
def fetch_data(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error fetching data from {url}: {response.status_code}")
        return None

def generate_aligned_data(stock_code):
    urls = [
        f'https://eniu.com/chart/marketvaluea/{stock_code}',  # 市值
        f'https://eniu.com/chart/pea/{stock_code}/t/all',  # PE TTM， “petttm, qfq_price”
        f'https://eniu.com/chart/pba/{stock_code}/t/all',  # PB
        f'https://eniu.com/chart/psa/{stock_code}/t/all',  # PS

        f'https://eniu.com/chart/roea/{stock_code}/q/0',  # ROE
        f'https://eniu.com/chart/incomea/{stock_code}/q/0', #营收
        f'https://eniu.com/chart/profitkfa/{stock_code}/q/0', #扣非净利润
        f'https://eniu.com/chart/grossprofitmargina/{stock_code}/q/0/t/table',   #毛利率，净利率
        f'https://eniu.com/chart/cashflowa/{stock_code}/q/0', #现金流
        
        f'https://eniu.com/chart/gbbA/{stock_code}', #股东数
        f'https://eniu.com/chart/jjcgA/{stock_code}/t/chart', #基金持股家数
        #f'https://eniu.com/table/sdgd/{stock_code}/q/ +date',#十大股东
        # https://eniu.com/chart/yjgk/sh600315
        # https://eniu.com/table/sdgd/sh600315/q/0
        # https://eniu.com/chart/pricea/sh600315/t/all
        ]

    Nameurl = f'https://xueqiu.com/S/{stock_code}'

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36"
    }

    try:
        response = requests.get(Nameurl, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        stock_detail = soup.select_one(".profile-detail").text.strip().split()
        stock_name = soup.select_one('.stock-name').text.strip()
        stock_name = re.match(r'(.+?)(?=\()', stock_name).group(0)
        print(stock_name, stock_code)
        print(stock_detail)

        data_dict = {}
        for td in soup.select('.quote-info td'):
            text = td.text.strip()
            if '：' in text:
                name, value = map(str.strip, text.split('：', 1))
                if value != '亏损':
                    data_dict[name] = float(value) if value.replace('.', '', 1).isdigit() else value

        # 只提取特定的总股本数据
        TotalStockNumber = 10000000000000000
        specific_pe = "总股本"
        if specific_pe in data_dict:
            Total_stock = data_dict[specific_pe]
            if "亿" in Total_stock:
                TotalStockNumber = float(Total_stock.replace("亿", "")) * 10000
            else:
                TotalStockNumber = float(Total_stock)
            print("总股本",TotalStockNumber,"万")
    except Exception as e:
        print(stock_name, "无股本数据")


    # 获取市值数据
    response = requests.get(urls[0], headers=headers)
    data = response.json()
    mv_date= data["date"]
    market_value = data["market_value"]
    stock_name = data.get("stock_name", stock_name)
    print("市值:",market_value)

    # 获取PE TTM和前复权数据
    response = requests.get(urls[1], headers=headers)
    data = response.json()
    pe_date = data["date"]
    pe_ttm = data["pe_ttm"]
    #qfq_price = data["price"]  #前复权价格
    print("市盈率:",pe_ttm)

    # 获取PB数据
    response = requests.get(urls[2], headers=headers)
    data = response.json()
    pb_date = data["date"]
    pb = data["pb"]
    print("市净值:",pb)

    # 获取PS数据
    response = requests.get(urls[3], headers=headers)
    data = response.json()
    ps_date = data["date"]
    ps = data["ps"]
    print("市销率:",ps)

    # 将数据转换为 Pandas 的 DataFrame 对象
    df1 = pd.DataFrame({'date': mv_date, 'Market Value': market_value})
    df2 = pd.DataFrame({'date': pe_date, 'PE TTM': pe_ttm})
    df3 = pd.DataFrame({'date': pb_date, 'PB': pb})
    df4 = pd.DataFrame({'date': ps_date, 'PS': ps})

    # 将日期列设置为索引
    df1.set_index('date', inplace=True)
    df2.set_index('date', inplace=True)
    df3.set_index('date', inplace=True)
    df4.set_index('date', inplace=True)

    # 使用 join 方法将 DataFrame 对象根据日期对齐
    aligned_data = df1.join([df2,df3,df4], how='inner')
    # 保留小数点后1位
    aligned_data['Market Value'] = round(aligned_data['Market Value'],1)
    aligned_data['PE TTM'] = round(aligned_data['PE TTM'],1)
    aligned_data['MV/PE'] = round(aligned_data['Market Value'] / aligned_data['PE TTM'], 1)
    aligned_data['PB'] = round(aligned_data['PB'],1)
    aligned_data['MV/PB'] = round(aligned_data['Market Value'] / aligned_data['PB'], 1)
    aligned_data['PS'] = round(aligned_data['PS'],1)
    aligned_data['MV/PS'] = round(aligned_data['Market Value'] / aligned_data['PS'], 1)

    # 获得字典数据，每7个取一个值，保留最近5年
    if len(aligned_data.index)>3000:
        date_array = aligned_data.index.tolist()[-3000::7]
        market_value_array = aligned_data['Market Value'].tolist()[-3000::7]
        pettm_array = aligned_data['PE TTM'].tolist()[-3000::7]
        mvpe_array =  aligned_data['MV/PE'].tolist()[-3000::7]
        pb_array = aligned_data['PB'].tolist()[-3000::7]
        mvpb_array =  aligned_data['MV/PB'].tolist()[-3000::7]
        ps_array = aligned_data['PS'].tolist()[-3000::7]
        mvps_array =  aligned_data['MV/PS'].tolist()[-3000::7]
    else:
        date_array = aligned_data.index.tolist()[::7]
        market_value_array = aligned_data['Market Value'].tolist()[::7]
        pettm_array = aligned_data['PE TTM'].tolist()[::7]
        mvpe_array =  aligned_data['MV/PE'].tolist()[::7]
        pb_array = aligned_data['PB'].tolist()[::7]
        mvpb_array =  aligned_data['MV/PB'].tolist()[::7]
        ps_array = aligned_data['PS'].tolist()[::7]
        mvps_array =  aligned_data['MV/PS'].tolist()[::7]

    #-----------------------------------------------------
    # 获取ROE数据
    roe_date = []
    roe = []
    response = requests.get(urls[4], headers=headers)
    data = response.json()
    if data:
        roe_date = data["date"]
        roe = [round(float(val), 2) for val in data["roe"]]
    print("ROE:",roe)

    # 获取营收数据
    response = requests.get(urls[5], headers=headers)
    data = response.json()
    income_date = []
    income = []
    if data:
        income_date = data["date"]
        income = data["income"]
    print("总收入:",income)

    # 获取扣非净利润数据、
    profit_date = []
    profit = []
    response = requests.get(urls[6], headers=headers)
    data = response.json()
    if data:
        profit_date = data["date"]
        profit = data["profit_kf"]
    print("总利润:",profit_date)

    # 获取毛/净利率数据
    margin_date = []
    gross_margin = []
    net_margin = []
    response = requests.get(urls[7], headers=headers)
    data = response.json()
    if data:
        margin_date = [item['date'] for item in data]
        gross_margin = [round(float(item['gross_profit_margin']), 2) for item in data if item.get('gross_profit_margin')]
        net_margin = [round(float(item['net_profit_margin']), 2) for item in data if item.get('net_profit_margin')]
        # 按照日期的倒序排序
        combined_data = list(zip(margin_date, gross_margin, net_margin))
        combined_data.sort(reverse = False)
        # 分离排序后的数据
        margin_date = [item[0] for item in combined_data]
        gross_margin = [item[1] for item in combined_data]
        net_margin = [item[2] for item in combined_data]
    print("毛利率:",gross_margin)
    print("净利率:",net_margin)

    # 将数据转换为 Pandas 的 DataFrame 对象
    dfA1 = pd.DataFrame({'date': roe_date, 'ROE': roe})
    dfA2 = pd.DataFrame({'date': income_date, 'INCOME': income})
    dfA3 = pd.DataFrame({'date': profit_date, 'PROFIT': profit})
    dfA4 = pd.DataFrame({'date': margin_date, 'GROSS MARGIN': gross_margin})
    dfA5 = pd.DataFrame({'date': margin_date, 'NET MARGIN': net_margin})

    # 将日期列设置为索引
    dfA1.set_index('date', inplace=True)
    dfA2.set_index('date', inplace=True)
    dfA3.set_index('date', inplace=True)
    dfA4.set_index('date', inplace=True)
    dfA5.set_index('date', inplace=True)

    # 使用 join 方法将 DataFrame 对象根据日期对齐
    aligned_data1 = dfA1.join([dfA2,dfA3,dfA4,dfA5], how='inner')
    aligned_data1['NM/GM'] = round((1- aligned_data1['NET MARGIN']/aligned_data1['GROSS MARGIN'])*100,1)
    #获得字典数据
    if len(aligned_data1.index)>6:
        year_array = dfA1.index.tolist()[-6:]
        roe_array = aligned_data1['ROE'].tolist()[-6:]
        income_array = aligned_data1['INCOME'].tolist()[-6:]
        profit_array = aligned_data1['PROFIT'].tolist()[-6:]
        gross_margin_array = aligned_data1['GROSS MARGIN'].tolist()[-6:]
        net_margin_array = aligned_data1['NET MARGIN'].tolist()[-6:]
        margin_cost_array = aligned_data1['NM/GM'].tolist()[-6:]
    else:
        year_array = dfA1.index.tolist()
        roe_array = aligned_data1['ROE'].tolist()
        income_array = aligned_data1['INCOME'].tolist()
        profit_array = aligned_data1['PROFIT'].tolist()
        gross_margin_array = aligned_data1['GROSS MARGIN'].tolist()
        net_margin_array = aligned_data1['NET MARGIN'].tolist()
        margin_cost_array = aligned_data1['NM/GM'].tolist()
    #-----------------------------------------------------
    # 获取股东数数据
    data = fetch_data(urls[9], headers)
    if data:
        gd_date = data["date"]
        gd_number = data["total"]
    else:
        gd_date = []
        gd_number =[]

    print("股东数:",gd_number)

    # 获取基金持股数据
    data = fetch_data(urls[10], headers)
    if data:
        jj_date = [item['jzrq'] for item in data]
        jj_number = [item['cgjs'] for item in data]
        jj_total = [item['cgs'] for item in data]
    else:
        jj_date = []
        jj_number = []
        jj_total = []
    print("基金家数:",jj_number)
    print("基金数:",jj_total)
    jj_total = [round(value *100 / TotalStockNumber, 2) for value in jj_total]
    print("基金占比",jj_total)

    dfB1 = pd.DataFrame({'date': gd_date, 'GD NUMBER': gd_number})
    dfB2 = pd.DataFrame({'date': jj_date, 'JJ NUMBER': jj_number, 'JJ TOTAL': jj_total})
    dfB1.set_index('date', inplace=True)
    dfB2.set_index('date', inplace=True)
    aligned_data2 = dfB1.join(dfB2, how='inner')

    if len(aligned_data2.index)>12:
        quater_array = dfB1.index.tolist()[-12:]
        gd_number_array = aligned_data2['GD NUMBER'].tolist()[-12:]
        jj_number_array = aligned_data2['JJ NUMBER'].tolist()[-12:]
        jj_total_array = aligned_data2['JJ TOTAL'].tolist()[-12:]
    else:
        quater_array = dfB1.index.tolist()
        gd_number_array = aligned_data2['GD NUMBER'].tolist()
        jj_number_array = aligned_data2['JJ NUMBER'].tolist()
        jj_total_array = aligned_data2['JJ TOTAL'].tolist()

    # 组成一个新的包含多个元素的数组
    data_dict = {
        "date": date_array,
        "market_value": market_value_array,
        "pe_ttm": pettm_array,
        "market_value_pe": mvpe_array,
        "pb": pb_array,
        "market_value_pb": mvpb_array,
        "ps": ps_array,
        "market_value_ps": mvps_array,
        #--------
        "year": year_array,
        "roe": roe_array,
        "income":income_array,
        "profit":profit_array,
        "gross_margin":gross_margin_array,
        "net_margin": net_margin_array,
        "margin_cost": margin_cost_array,
        #----------
        "quater": quater_array,
        "gd_number": gd_number_array,
        "jj_number":jj_number_array,
        "jj_total":jj_total_array,
        #----------
        "stock_name": stock_name,
        "stock_detail": stock_detail
    }
    print(data_dict)
    return data_dict


def fetch_table_data(stock_code):
    logging.info(f"Fetching data for stock code: {stock_code}")
    chrome_driver_path = ChromeDriverManager().install()
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 设置为无头模式
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # 记录调试信息
        logging.debug(f"Fetching data for stock code: {stock_code}")

        # 访问网页
        url = f'https://xueqiu.com/snowman/S/{stock_code}/detail#/SDGD'
        driver.get(url)
        # 使用 XPath 定位表格
        table_xpath = "/html/body/div[1]/div[2]/div[2]/div/table[1]"
        table_element = driver.find_element(By.XPATH, table_xpath)

        # 提取表格数据
        table_data = []
        for i, row in enumerate(table_element.find_elements(By.TAG_NAME, "tr")):
            if i == 0:  # 跳过第一行
                continue
            row_data = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, "td")]
            # 跳过第二列
            row_data = row_data[:1] + row_data[2:]
            table_data.append(row_data)

        # 检查表格是否为空
        if not table_data:
            logging.warning("Table data is empty, returning default values")
            columns = ["No Data"]
            data = [["No Data Available"]]
        else:
            logging.debug("Table data fetched successfully")
            # 提取表头，同时跳过第二列
            columns = table_data[0]
            # 提取数据，同时跳过第二列
            data = [row for row in table_data[1:]]

        return {"columns": columns, "data": data}

    except Exception as e:
        logging.error(f"Error fetching table data: {e}")
        return {"columns": ["Error"], "data": [[str(e)]]}

    finally:
        # 关闭 WebDriver
        driver.quit()

@app.route('/api/data/<stock_code>', methods=['GET'])
def get_data(stock_code):
    try:
        logging.info(f"Fetching aligned data for stock code: {stock_code}")
        data = generate_aligned_data(stock_code)
        logging.info(f"Data fetched successfully for stock code: {stock_code}")
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error fetching data for stock code {stock_code}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/excel_data/<stock_code>', methods=['GET'])
def get_excel_data(stock_code):
    try:
        logging.info(f"Fetching excel data for stock code: {stock_code}")
        excel_data = fetch_table_data(stock_code)
        logging.info(f"Excel data fetched successfully for stock code: {stock_code}")
        return jsonify(excel_data)
    except Exception as e:
        logging.error(f"Error fetching excel data for stock code {stock_code}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/<stock_code>')
def index(stock_code):
    logging.info(f"Rendering index page for stock code: {stock_code}")
    return render_template('index.html', stock_code=stock_code)

@app.route('/')
def home():
    logging.info("Rendering home page")
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

