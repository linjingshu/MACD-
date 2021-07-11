import tushare as ts
import pandas as pd
import numpy as np
import os

# 获取token
ts.set_token('bf6447d5d55ca68af70daf2e0da632b88af60adad6f40d56a82b4683')
pro = ts.pro_api()

# 显示最大列
pd.set_option('display.max_columns', None)
# 禁止换行
pd.set_option('expand_frame_repr', False)
# 显示最大行
pd.set_option('display.max_row', None)

# 设置时间范围
start_date = '20191129'
end_date = '20210614'

# 设置股票代码列表,如果为空，则按默认
stock_code_list = ['002288.SZ']

# 从外部导入股票的路径(支持xlsx格式)
outside_paths = []


# 获取股票代码列表
def get_stock_code_list():
    if len(stock_code_list) == 0:
        stock_list = pro.query('stock_basic', exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,'
                                                                                   'list_date')
        code_list = stock_list['ts_code']
    else:
        return stock_code_list
    return code_list


# 获取股票数据
def get_stock_data(ts_code, start_day, end_day):
    # 股票代码
    code = ts_code
    # 获取一年的日线行情数据
    data = pro.daily(ts_code=code, start_date=start_day, end_date=end_day)
    # 因为取到的数据是按时间由近到远排序的，我们反过来
    df_sorted = data.sort_values(by='trade_date')
    # 修改索引
    df_sorted.index = list(range(len(df_sorted)))
    return df_sorted


# 计算EMA,返回ema数组
def fun_ema(closes, N):
    a = 2 / (N + 1)
    ema = []
    length = len(closes)
    if length > 0:
        for i in range(length):
            if i == 0:
                ema.append(closes[i])
            else:
                ema.append(a * closes[i] + (1 - a) * ema[i - 1])
    # 转换为numpy数组，保留两位小数点
    ema_np = np.round(np.array(ema), 2)
    return ema_np


# 构建MACD模型,返回以初始数据为基础，再加上MACD模型列的DataFrame
def MACD(df, s=12, l=26, M=9):
    fast = fun_ema(df['close'], s)
    slow = fun_ema(df['close'], l)
    # 增加相应的列
    # 快线
    df['Fast'] = fast
    # 慢线
    df['Slow'] = slow
    # DIF线
    df['DIF'] = df['Fast'] - df['Slow']
    # DEA线
    df['DEA'] = fun_ema(df['DIF'], M)
    # MACD 值
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])
    return df


# 将数据框导入Excel
def put_to_excel(df, filename):
    path = os.path.dirname(os.getcwd()) + "\\excel_1\\"
    try:
        if not os.path.exists(path):
            os.mkdir(path)
            print("文件夹", path, "创建成功")
        print("写入excel...")
        excel_path = path + filename + ".xlsx"
        df.to_excel(excel_path)
        print('写入成功！！')
    except Exception as e:
        print("写入失败：", e)


# 从excel中获取股票数据()
def get_stock_data_from_excel(path):
    try:
        if not os.path.exists(path):
            print("文件路径不存在！！！")
            return
        else:
            print("读取excel文件中...")
            df = pd.read_excel(path)
            print("读取成功！！！")
            return df
    except Exception as e:
        print("读取失败：", e)


# 模拟交易,假定每次交易价格为收盘价格
def simulated_transaction(df):
    # 是否持有资产，默认为false,不持有资产
    is_hold = False
    # 记录买入价格和卖出价格
    buys = []
    sells = []
    # 卖出时每股盈利
    benefit = []
    close_macd = df[['close', 'MACD']]
    for i in range(len(close_macd) - 1):
        # 舍弃第一个值
        if i == 0:
            continue
        if close_macd['MACD'][i] >= 0:
            # 有正变负，将持有卖出
            if is_hold is True and close_macd['MACD'][i + 1] < 0:
                sells.append(close_macd['close'][i + 1])
                benefit.append(sells[len(sells) - 1] - buys[len(buys) - 1])
                is_hold = False
            continue
        elif close_macd['MACD'][i] < 0:
            # 由负变正,买入
            if close_macd['MACD'][i + 1] > 0:
                buys.append(close_macd['close'][i + 1])
                is_hold = True

    # 统计
    # 买入次数
    buys_num = len(buys)
    # 卖出次数
    sells_num = len(sells)
    # 统计盈利次数
    gain_num = 0
    for i in benefit:
        if i > 0:
            gain_num = gain_num + 1
    success_rate = round(gain_num / sells_num, 4) * 100
    print("股票代码=", df['ts_code'][0])
    # print("买入次数=", buys_num, "卖出次数=", sells_num, "盈利次数=", gain_num)
    # print("成功率=", success_rate, "%")
    return buys_num, sells_num, gain_num, success_rate, df['ts_code'][0]


# 处理参数，开始分析,is_to_excel是否下载数据到excel
def go(in_codes=None, out_paths=None, is_to_excel=False):
    # 创建空的数据表，用来统计所有股票代码模拟交易的数据
    total_df = pd.DataFrame()
    # 每支股票成功率
    success_rate_list = []
    # 每支股票买入次数
    each_buys = []
    # 每支股票卖出次数
    each_sells = []
    # 每支股票盈利次数
    each_earns = []
    # 股票列表
    ts_codes = []
    # 如果股票代码为空则执行默认方法
    if out_paths is None:
        out_paths = []
    if in_codes is None:
        in_codes = []
    if len(in_codes) == 0:
        df_ts_code_list = get_stock_code_list()
    else:
        df_ts_code_list = in_codes
        # （默认）就先计算300个股票吧
    if len(df_ts_code_list) > 0:
        for i in range(len(df_ts_code_list)):
            if i > 300:
                break
            ts_code = df_ts_code_list[i]
            data = get_stock_data(ts_code, start_date, end_date)
            df_macd = MACD(data)
            t = simulated_transaction(df_macd)
            if len(t) != 0:
                each_buys.append(t[0])
                each_sells.append(t[1])
                each_earns.append(t[2])
                success_rate_list.append(t[3])
                ts_codes.append(ts_code)
                # df_macd['模拟交易'] = ["买入次数", "卖出次数", "盈利次数", "成功率"]
            # df_macd['值'] = [t[0],t[1],t[2],t[3]]
            # if is_to_excel:
            #     put_to_excel(df_macd,ts_code[:-3])

    elif len(out_paths) > 0:
        for i in out_paths:
            if i > 300:
                break
            da_f = get_stock_data_from_excel(i)
            da_f_macd = MACD(da_f)
            t0 = simulated_transaction(da_f_macd)
            if len(t0) != 0:
                each_buys.append(t0[0])
                each_sells.append(t0[1])
                each_earns.append(t0[2])
                success_rate_list.append(t0[3])
                ts_codes.append(t0[4])
        # avg_rate = np.round(np.sum(np.array(success_rate_list))/len(success_rate_list),2)
        # print("平均成功率：",avg_rate,"%")
    total_df['股票代码'] = ts_codes
    total_df['买入次数'] = each_buys
    total_df['卖出次数'] = each_sells
    total_df['盈利次数'] = each_earns
    total_df['成功率/%'] = success_rate_list
    print("一共买入", np.sum(each_buys), "次")
    print("一共卖出", np.sum(each_sells), "次")
    print("一共盈利", np.sum(each_earns), "次")
    print("平均成功率=", np.round(np.sum(each_earns) / np.sum(each_sells), 4) * 100, "%")
    if is_to_excel:
        put_to_excel(total_df, "total_df")
    return total_df


# 测试
if __name__ == '__main__':
    go(is_to_excel=False)
