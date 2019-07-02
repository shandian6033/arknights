import os
import requests
import json
import pandas as pd
from scipy.optimize import linprog

FILE_PATH = os.path.dirname(os.path.realpath(__file__)) + '\\all_in_one.xlsx'
API_URL = 'https://penguin-stats.io/PenguinStats/api/result/matrix'
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


def get_material_api_data(url, params):
    try:
        api_r = requests.get(url, params=params)
        api_data = pd.DataFrame.from_records(api_r.json()['matrix'])
    except Exception as e:
        print(e)
        with open('./matrix.json', 'r', encoding='utf8') as f:
            api_data = pd.DataFrame.from_records(json.load(f)['matrix'])
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


def prepare_stage_data(template_df, update_template=False):
    money_df = template_df[['Action', '理智', '龙门币']]
    material_api_df = get_material_api_data(API_URL, PARAMS)
    if update_template:
        temp_df = pd.merge(
            template_df[['Action']],
            material_api_df,
            on='Action',
            how='left',
            sort=True
        )
        template_df[temp_df.columns] = temp_df
        # template_df.to_excel(update_writer, sheet_name='Stage', index=False)
    stage_data = pd.merge(money_df, material_api_df, on='Action', how='left', sort=True)
    return stage_data, template_df


def action_by_demand(formula_df, demand_df):
    a_matrix_columns = list(demand_df.iloc[:, 0])
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
            'Stage': list(formula_df['Action']),
            'Times': res.x
        }
    )
    total_san = - (result['Times'] * formula_df['理智']).sum()
    return result, total_san


def value_by_demand(formula_df, demand_df):
    n_items = demand_df.shape[0]
    result_df, cur_san = action_by_demand(formula_df, demand_df)
    values = []
    for i in range(n_items):
        new_demand = demand_df.copy().fillna(0)
        new_demand.iloc[i, 1] -= 1
        _, new_san = action_by_demand(formula_df, new_demand)
        values.append(cur_san - new_san)
    demand_df['Value'] = values
    return demand_df


if __name__ == '__main__':
    manufacture_df = pd.read_excel(FILE_PATH, sheet_name='Manufacture')
    stage_df = pd.read_excel(FILE_PATH, sheet_name='Stage')
    my_demand_df = pd.read_excel(FILE_PATH, sheet_name='Demand')
    with pd.ExcelWriter(FILE_PATH) as file_writer:
        try:
            stage_df, new_template = prepare_stage_data(stage_df, update_template=True)
            action_df = stage_df.append(manufacture_df, ignore_index=True)
            todo_df, _ = action_by_demand(action_df, my_demand_df)
            new_template.to_excel(file_writer, sheet_name='Stage', index=False)
            manufacture_df.to_excel(file_writer, sheet_name='Manufacture', index=False)
            demand_value_df = value_by_demand(action_df, my_demand_df)
            demand_value_df.to_excel(file_writer, sheet_name='Demand', index=False)
            todo_df.to_excel(file_writer, sheet_name='Todo', index=False)
            print('SUCCESS ^_^')
        except Exception as e:
            print('FAIL!!')
            print(e)
            stage_df.to_excel(file_writer, sheet_name='Stage')
            manufacture_df.to_excel(file_writer, sheet_name='Manufacture')
            my_demand_df.to_excel(file_writer, sheet_name='Demand')


