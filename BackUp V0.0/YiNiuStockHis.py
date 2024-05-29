import requests
import pandas as pd
from flask import Flask, jsonify, render_template

app = Flask(__name__)

def generate_aligned_data():
    urls  = [
        'https://eniu.com/chart/marketvaluea/sh600309',  # Value
        'https://eniu.com/chart/pea/sh600309/t/all',  # PETTM
        'https://eniu.com/chart/roea/sh600309/q/0', # ROE
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36"
    }

    # 获取市值数据
    url = urls[0]
    response = requests.get(url, headers=headers)
    data = response.json()
    date1 = data["date"]
    market_value = data["market_value"]

    # 获取PETTM数据
    url = urls[1]
    response = requests.get(url, headers=headers)
    data = response.json()
    date2 = data["date"]
    pe_ttm = data["pe_ttm"]

    # 获取ROE数据
    #url = urls[1]
    #response = requests.get(url, headers=headers)
    #data = response.json()
    #date3 = data["date"]
    #roe = data["roe"]

    # 将数据转换为 Pandas 的 DataFrame 对象
    df1 = pd.DataFrame({'date': date1, 'Market Value': market_value})
    df2 = pd.DataFrame({'date': date2, 'PE TTM': pe_ttm})
    #df3 = pd.DataFrame({'date': date3, 'ROE': roe})

    # 将日期列设置为索引
    df1.set_index('date', inplace=True)
    df2.set_index('date', inplace=True)
    #df3.set_index('date', inplace=True)

    # 使用 join 方法将两个 DataFrame 对象根据日期对齐
    aligned_data = df1.join(df2, how='inner')

    date_array = aligned_data.index.tolist()[::7]  # 每7个取一个值
    market_value_array = aligned_data['Market Value'].tolist()[::7]  # 每7个取一个值
    pettm_array = aligned_data['PE TTM'].tolist()[::7]  # 每7个取一个值

    # 组成一个新的包含三个元素的数组
    date_dict = {"date": date_array}
    market_value_dict = {"market_value": market_value_array}
    pettm_dict = {"pe_ttm": pettm_array}

    # 将三个字典组成一个新的数组
    combined_array = [date_dict, market_value_dict, pettm_dict]
    return combined_array

# 定义一个路由，处理 GET 请求，用于获取数据
@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify(generate_aligned_data())

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

