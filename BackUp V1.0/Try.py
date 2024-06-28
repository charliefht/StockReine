import logging
from flask import Flask, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import requests
from bs4 import BeautifulSoup

# 设置日志记录级别和格式
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

def fetch_table_data(stock_code):
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
        for row in table_element.find_elements(By.TAG_NAME, "tr"):
            row_data = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, "td")]
            table_data.append(row_data)

        # 检查表格是否为空
        if not table_data:
            # 返回固定的默认值
            columns = ["No Data"]
            data = [["No Data Available"]]
        else:
            # 提取表头
            columns = table_data[0]
            # 提取数据
            data = table_data[1:]

        # 记录调试信息
        logging.debug(f"Data fetched successfully for stock code: {stock_code}")

        return {"columns": columns, "data": data}

    except Exception as e:
        # 记录异常信息
        logging.error(f"An error occurred while fetching data for stock code {stock_code}: {e}")
        raise  # 将异常继续抛出以便上层处理

    finally:
        # 关闭 WebDriver
        logging.debug("Closing WebDriver")
        driver.quit()
#
#@app.route('/api/data/<stock_code>', methods=['GET'])
#def get_data(stock_code):
#    try:
#        data = fetch_table_data(stock_code)
#        return jsonify(data)
#    except Exception as e:
#        return jsonify({'error': str(e)})
#
#@app.route('/<stock_code>')
#def index(stock_code):
#    return render_template('index-try.html', stock_code=stock_code)
#
#if __name__ == '__main__':
#    app.run(host='0.0.0.0', port=5000, debug=True)
#

# 发送 HTTP 请求获取网页内容
import requests
from bs4 import BeautifulSoup

# 发送 GET 请求获取网页内容
url = "https://xueqiu.com/S/SH603129"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
response = requests.get(url, headers=headers)

# 使用 BeautifulSoup 解析 HTML
soup = BeautifulSoup(response.text, "html.parser")

# 找到总股本所在的 div 元素
quote_info_div = soup.find("table", class_="quote-info")
if quote_info_div:
    # 找到总股本所在的 td 元素
    total_share_td = quote_info_div.find("td", string="总股本")
    if total_share_td:
        # 获取总股本的值
        total_share_value = total_share_td.find_next_sibling("td").get_text(strip=True)
        print("总股本:", total_share_value)
    else:
        print("未找到总股本数据")
else:
    print("未找到 quote-info 元素")



