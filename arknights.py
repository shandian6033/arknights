import requests
import pandas as pd
from scipy.optimize import linprog
# todo: all in one file

MAX_VALUE = 9999
FILE_NAME = './my_arknights_backup.xlsx'
OUTPUT = './ark_value.xlsx'
API_URL = 'https://penguin-stats.io/PenguinStats/api/result/matrix'
MONEY_URL = 'https://raw.githubusercontent.com/Perfare/ArknightsGameData/master/excel/stage_table.json'
PARAMS = {
    'show_item_details': True,
    'show_stage_details': True,
    'show_close_zone': False
}
MATERIAL_API_COLUMNS = [
    'name',  # 材料名称
    'quantity',  # 掉落数
    'code',  # 关卡
    'times',  # 样本数
    'apCost'
]
MONEY_API_COLUMNS = [
    'code',  # 关卡
    'goldGain',
    'apCost'
]


def calculate_value():
    output_writer = pd.ExcelWriter(OUTPUT)
    mission_data = pd.read_excel(FILE_NAME, sheet_name='Mission')
    manufacture_data = pd.read_excel(FILE_NAME, sheet_name='Manufacture')
    all_items = [x for x in mission_data.columns if x not in ['Action', 'San']]
    producible_items = list(set(manufacture_data['Action']))
    fundamental_items = [x for x in all_items if x not in producible_items]

    value_df = pd.DataFrame(
        index=all_items,
        columns=['Value by Mission', 'Value', 'Method']
    )

    for item in all_items:
        per_san_series = (mission_data[item] / mission_data['San'])
        per_san_min = per_san_series.min()
        value = -1 / per_san_min
        if pd.notna(value):
            mission = mission_data[per_san_series == per_san_min]['Action'].iloc[0]
            value_df.loc[item]['Method'] = mission
        value_df.loc[item]['Value by Mission'] = value
        if item in fundamental_items:
            value_df.loc[item]['Value'] = value

    loop = 0
    while value_df['Value'].isna().any() and loop < len(producible_items):
        loop += 1
        for item in producible_items:
            can_price = True
            item_row = value_df.loc[item]
            methods_df = manufacture_data[manufacture_data['Action'] == item]
            item_value = (
                MAX_VALUE
                if pd.isna(item_row['Value by Mission'])
                else item_row['Value by Mission']
            )
            for index, row in methods_df.iterrows():
                requires = list(row[row < 0].index)
                requires_values = value_df.loc[requires]['Value']
                if requires_values.isna().any():
                    can_price = False
                    break
                method_value = -(row[row < 0] * requires_values).sum()
                if method_value < item_value:
                    item_value = method_value
            if not can_price:
                continue
            item_row['Value'] = item_value
            if item_value < item_row['Value by Mission'] or pd.isna(item_row['Value by Mission']):
                item_row['Method'] = 'Produce'

    value_df.to_excel(output_writer, sheet_name='byMaterial')


def trans_to_fundamental_df(all_item_df, manufacture_data):
    all_items = [x for x in all_item_df.columns if x not in ['Action', 'San']]
    producible_items = list(set(manufacture_data['Action']))
    fundamental_items = [x for x in all_items if x not in producible_items]
    for index, row in all_item_df.iterrows():
        pass


def get_material_api_data(url, params):
    api_r = requests.get(url, params=params)
    api_data = pd.DataFrame.from_records(api_r.json()['matrix'])
    api_data = api_data.join(api_data['item'].apply(pd.Series), lsuffix='_api')
    api_data = api_data.join(api_data['stage'].apply(pd.Series), lsuffix='_api')
    assert all([x in api_data.columns for x in MATERIAL_API_COLUMNS]), 'some API_COLUMNS not in raw_data columns'
    api_data = api_data[MATERIAL_API_COLUMNS]
    # apcost_df = api_data[['code', 'apCost']].drop_duplicates()
    # apcost_df['apCost'] = -apcost_df['apCost']
    api_data = (
        api_data
        .groupby(['name', 'code'])
        .agg(
            {
                'quantity': 'sum',
                'times': 'sum'
            }
        )
        .reset_index()
    )
    api_data['probability'] = api_data['quantity'] / api_data['times']
    api_data = api_data.pivot(index='code', columns='name', values='probability')
    # api_data = pd.merge(api_data.reset_index(), apcost_df, on='code', how='left')
    api_data = (
        api_data
        .reset_index()
        .rename(
            columns={
                'code': 'Action',
                'apCost': '理智'
            }
        )
    )
    return api_data


# def get_money_data(url):
#     api_r = requests.get(url)
#     api_data = pd.DataFrame.from_dict(api_r.json()['stages'], orient='index')
#     api_data = api_data[MONEY_API_COLUMNS]
#     api_data['goldGain'] = (
#             (api_data['goldGain'] / api_data['apCost'] * 1.2)
#             .fillna(0)
#             .apply(round)
#             * api_data['apCost']
#     )
#     return api_data

def prepare_mission_data(template_path, sheet_name=None):
    money_df = pd.read_excel(template_path, sheet_name=sheet_name)
    # columns = money_df.columns
    money_df = money_df[['Action', '理智', '龙门币']]
    material_api_df = get_material_api_data(API_URL, PARAMS)

    mission_data = pd.merge(money_df, material_api_df, on='Action', how='left')
    return mission_data


def action_by_demand(formula_df, demand_df, output):
    a_matrix_columns = list(demand_df.iloc[:, 0])
    # formula_df[a_matrix_columns].to_excel('./debug.xlsx')
    a_matrix = formula_df[a_matrix_columns].fillna(0).transpose().values
    b_vector = demand_df.iloc[:, 1].fillna(0)
    c_vector = formula_df['理智'].fillna(0)

    res = linprog(
        c=-c_vector,
        A_ub=-a_matrix,
        b_ub=-b_vector,
        bounds=[0, None],
        options={
            'tol': 0.00001
        }
    )
    result = pd.DataFrame(
        {
            'Mission': list(formula_df['Action']),
            'Times': res.x
        }
    )
    result.to_excel(output)


if __name__ == '__main__':
    manufacture_df = pd.read_excel(FILE_NAME, sheet_name='Manufacture')
    mission_df = prepare_mission_data(FILE_NAME, sheet_name='Mission')
    action_df = mission_df.append(manufacture_df, ignore_index=True)

    my_demand_df = pd.read_excel('./action_by_demand.xlsx', sheet_name='demand', header=None)
    action_by_demand(action_df, my_demand_df, './to_do.xlsx')

