import pandas as pd
import numpy as np
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

file = 'data/HC_DAILY.xlsx'
monthly = pd.read_excel(file, sheet_name = 'HC_Monthly').rename(str.lower, axis = 1)
daily = pd.read_excel(file, sheet_name = 'HC_Daily').rename(str.lower, axis = 1)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server


#Monthly Dash Preprocessing 

monthly['di_date'] = pd.to_datetime(monthly['di_date'], format = '%Y%m').dt.to_period('m')
three_monthly = monthly.loc[monthly['di_date'] >= np.unique(monthly['di_date'])[-3]].reset_index(drop = True)
cust_nousage = three_monthly.loc[three_monthly['f_customer_use'] != '1) Customer Hv Usage'].reset_index(drop = True)
cust_usage = three_monthly.loc[three_monthly['f_customer_use'] == '1) Customer Hv Usage'].reset_index(drop = True)
inactive_user = dict([(str(x), cust_nousage.loc[cust_nousage['di_date'] == x, ['cnt_cust']]['cnt_cust'].sum()) for x in np.unique(cust_nousage['di_date'])])
active_user = dict([(str(x), cust_usage.loc[cust_usage['di_date'] == x, ['cnt_cust']]['cnt_cust'].sum()) for x in np.unique(cust_usage['di_date'])])
pct_active = dict([(u,(active_user[u]/(inactive_user[u] + active_user[u]))*100) for u in inactive_user.keys()])


amt_user = dict([(str(x), (cust_usage.loc[cust_usage['di_date'] == x, ['cnt_txn_day']]['cnt_txn_day'].sum(), cust_usage.loc[cust_usage['di_date'] == x, ['sum_amt']]['sum_amt'].sum())) for x in np.unique(cust_usage['di_date'])])

def relabel(x):
    if x == 'บุคคลในครอบครัวของผู้มิสิทธิ': return 'ครอบครัว'
    elif x == 'ตัวผู้มิสิทธิเอง':return 'ข้าราชการ'
def accum_pct():
    def sumpct(x): return np.sum(x)/total
    sumpct.__name__ = 'sum_pct'
    return sumpct

use_col = ['relation_desc_group', 'cnt_cust','hospital_type', 'hospital_department', 'dim_cnt_hospital', 'dim_cnt_manual_txn', 'dim_cnt_off_time'] 
latest_date, oldest_date = max(cust_usage['di_date']), min(cust_usage['di_date'])
latest_usage = cust_usage.loc[cust_usage['di_date'] == latest_date, use_col].reset_index(drop = True) 
latest_no_usage = cust_nousage.loc[cust_nousage['di_date'] == latest_date, ['cnt_cust']].reset_index(drop = True)
total = latest_usage['cnt_cust'].sum() + latest_no_usage['cnt_cust'].sum()

latest_usage['relation_desc_group'] = latest_usage['relation_desc_group'].apply(lambda x: relabel(x))
accum_data = latest_usage.groupby(['relation_desc_group']).agg({'cnt_cust' : accum_pct()}).reset_index()
accum_data = accum_data.append({'relation_desc_group' : 'ผู้ไม่ใช้สิทธิ', 'cnt_cust' : latest_no_usage['cnt_cust'].sum()/total}, ignore_index = True)

def accum():
    def sum_cnt(x): return np.sum(x)
    sum_cnt.__name__ = 'sum_cnt'
    return sum_cnt
def rename(x):
    if x == 'เบิกค่ารังสีผู้ป่วยมะเร็ง': return 'เบิกค่ารังสีมะเร็ง'
    elif x == 'เบิกค่าฟอกเลือดด้วยเครื่องไตเทียม': return 'เบิกค่าฟอกไต'
    elif x == 'ผู้ป่วยนอกทั่วไป': return 'ผู้ป่วยนอกทั่วไป'

accum_dep = latest_usage.groupby(['hospital_department', 'hospital_type']).agg({'cnt_cust' : accum()}).reset_index()
total_dep = accum_dep.groupby(['hospital_department']).agg({'cnt_cust' : accum()}).reset_index().rename(columns = {'cnt_cust' : 'total_cust'})

latest_dep = accum_dep.merge(total_dep, how = 'left', on = 'hospital_department')
latest_dep['cnt_cust_pct'] = latest_dep['cnt_cust']/latest_dep['total_cust']
latest_dep['hospital_department'] = latest_dep['hospital_department'].apply(lambda x: x.split(')')[1])

gov_hosp = latest_dep[latest_dep['hospital_type'] == 'รัฐบาล'].reset_index(drop = True)
priv_hosp = latest_dep[latest_dep['hospital_type'] == 'เอกชน'].reset_index(drop = True)

gov_hosp['hospital_department'] = gov_hosp['hospital_department'].apply(lambda x: rename(x.lstrip().rstrip()))
priv_hosp['hospital_department'] = priv_hosp['hospital_department'].apply(lambda x: rename(x.lstrip().rstrip()))

off_time = latest_usage.loc[latest_usage['dim_cnt_off_time'] > 5, ['cnt_cust']]['cnt_cust'].sum()
hosp_eli = latest_usage.loc[latest_usage['dim_cnt_hospital'] >3 ]['cnt_cust'].sum()
manual_txn = latest_usage.loc[latest_usage['dim_cnt_manual_txn'] >5]['cnt_cust'].sum()


#Daily Dashboard Preprocessing
latest_daily = daily[daily['di_date'] == max(daily['di_date'])].reset_index(drop = True)
daily_usage = latest_daily.loc[latest_daily['f_customer_use'] == '1) Customer Hv Usage'].reset_index(drop = True)
daily_no_usage = latest_daily.loc[latest_daily['f_customer_use'] != '1) Customer Hv Usage'].reset_index(drop = True)
last_daily = str(max(daily['last_date'])).split(' ')[0]
daily_cnt = daily_usage.groupby(['last_date']).agg({'cnt_cust' : accum(), 'sum_amt' : accum()}).reset_index()
daily_cnt['prev'] = daily_cnt['cnt_cust'].shift().fillna(0)
daily_cnt['daily_cust'] = daily_cnt['cnt_cust'] - daily_cnt['prev']
daily_cnt['last_date'] = daily_cnt['last_date'].apply(lambda x: str(x).split(' ')[0].split('-')[-1])
last_date = max(latest_daily['last_date'])
daily_off = daily_usage.loc[(daily_usage['last_date'] == last_date) & (daily_usage['dim_cnt_off_time'] > 5), ['cnt_cust']]['cnt_cust'].sum()
daily_eli = daily_usage.loc[(daily_usage['last_date'] == last_date) & (daily_usage['dim_cnt_hospital'] > 3), ['cnt_cust']]['cnt_cust'].sum()
daily_manual = daily_usage.loc[(daily_usage['last_date'] == last_date) & (daily_usage['dim_cnt_manual_txn'] > 5), ['cnt_cust']]['cnt_cust'].sum()


#Dashboard app

def Header(name, app):
    title = html.H4(name, style={"margin-top": 5})
    return dbc.Row([dbc.Col(title, md=6)])

def sub_Header(name, app):
    sub_title = html.H5(name, style = {'margin_top': 5})
    return dbc.Row([dbc.Col(sub_title, md = 5)])

def LabeledSelect(label, **kwargs):
    return dbc.FormGroup([dbc.Label(label), dbc.Select(**kwargs)])


fraud_box = [
    dbc.Card(
        [
            html.H2('{:,.0f} คน'.format(off_time), className="card-title"),
            html.P("ใช้สิทธิระหว่าง 20.00 น. - 8.00 น. > 5 ครั้ง", className="card-text"),
        ],
        body=True,
        color="secondary",
        inverse = True,
    ),
    dbc.Card(
        [
            html.H2('{:,.0f} คน'.format(hosp_eli), className="card-title"),
            html.P("ไปใช้สิทธิ > 3 โรงพยาบาล", className="card-text"),
        ],
        body=True,
        color="dark",
        inverse=True,
    ),
    dbc.Card(
        [
            html.H2('{:,.0f} คน'.format(manual_txn), className="card-title"),
            html.P("ทำรายการแบบ Manual > 5 ครั้ง", className="card-text"),
        ],
        body=True,
        color="info",
        inverse=True,
    ),
]

fraud_box_daily = [
    
    dbc.Card(
        [
            html.H2('{:,.0f} คน'.format(daily_off), className = 'card-title'),
            html.P("ใช้สิทธิระหว่าง 20.00 น. - 8.00 น. > 5 ครั้ง", className = "card-text"),
            
        ],
        body = True,
        color = 'info',
        inverse = True
    ),
    
    dbc.Card(
        [
            html.H2('{:,.0f} คน'.format(daily_eli), className = 'card-title'),
            html.P('ไปใช้สิทธิ > 3 โรงพยาบาล', className = 'card-text'),
        ],
        body = True,
        color = 'success',
        inverse = True
    ),
    dbc.Card(
        [
            html.H2('{:,.0f} คน'.format(daily_manual), className = 'card-title'),
            html.P('ทำรายการแบบ Manual > 5 ครั้ง', className = 'card-text'),
        ],
        body = True,
        color = 'warning',
        inverse = True
    ),
]

graph_comp = [
    [dcc.Graph(id = 'cnt_monthly', figure = {'data' : [{'x' : [u for u in inactive_user.keys()], 
                                                        'y' : [inactive_user[m] for m in inactive_user.keys()], 
                                                        'type' : 'bar', 
                                                        'name' : 'Inactive_users',
                                                       'text' : ['{:.2f}M'.format(inactive_user[h]/1000000) for h in inactive_user.keys()],
                                                       'textposition' : 'auto',
                                                       'hoverinfo' : 'skip',
                                                       'marker' : dict(color = '#c7ecee', line = dict(color = '#2C3A47', width = 2))},
                                                      {'x' : [k for k in active_user.keys()],
                                                      'y': [active_user[h] for h in active_user.keys()],
                                                      'type' : 'bar',
                                                      'name' : 'Active_users',
                                                      'text' : ['{:.2f}M'.format(active_user[h]/1000000) for h in active_user.keys()],
                                                      'textposition' : 'auto',
                                                      'hoverinfo' : 'skip',
                                                      'marker' : dict(color = '#FEA47F', line = dict(color = '#2C3A47', width = 2))},
                                                       {'x' : [l for l in pct_active.keys()],
                                                        'y' : [float('{:,.2f}'.format(pct_active[n]/100)) for n in pct_active.keys()],
                                                        'type' : 'line',
                                                        'name' : '% Active_users',
                                                        'yaxis' : 'y2',
                                                       'hovertext':['{:,.2f}%'.format(pct_active[n]) for n in pct_active.keys()],
                                                       'hoverinfo' : 'text'}],
                                            'layout': dict(title = '%Active ของผู้มีสิทธิ',
                                                           legend = dict(orientation = 'h', font = dict(family = 'sans-serif', size = 12)),
                                                           yaxis = dict(title = 'Cnt Users',
                                                                        side = 'left',
                                                                        showline = False,
                                                                        range = [0, max([inactive_user[m] for m in inactive_user.keys()]) + 500000],
                                                                        showgrid = True),
                                                           yaxis2 = dict(title = '% Active User',
                                                                         overlaying = 'y',
                                                                         side = 'right',
                                                                         tickformat = ',.0%',
                                                                         range = [0,max([float('{:,.2f}'.format(pct_active[n]/100)) for n in pct_active.keys()]) + 0.1],
                                                                         anchor = 'x', showgrid = False),
                                                          hovermode = 'x')})], 
    [dcc.Graph(id = 'amt_monthly', figure = {'data' : [{'x' : [k for k in amt_user.keys()],
                                                       'y' : [amt_user[p][1] for p in amt_user.keys()],
                                                       'type' : 'line',
                                                       'name' : 'มูลค่าการใช้สิทธิ',
                                                       'hovertext' : ['{:.2f} พันล้านบาท'.format(amt_user[j][1]/1000000000) for j in amt_user.keys()],
                                                       'hoverinfo' : 'text',
                                                       'line' : dict(color = '#574b90')},
                                                      {'x' : [k for k in amt_user.keys()],
                                                      'y' : [amt_user[p][0] for p in amt_user.keys()],
                                                      'type' : 'bar',
                                                      'name' : '# ครั้งที่ใช้สิทธิ',
                                                      'text' : ['{:.2f}M'.format(amt_user[p][0]/1000000) for p in amt_user.keys()],
                                                      'textposition' : 'auto',
                                                      'hoverinfo' : 'skip',
                                                      'yaxis' : 'y2',
                                                      'marker' : dict(color = '#227093', line = dict(color = '#2C3A47', width = 2))}],
                                            'layout' : dict(title = 'มูลค่าและจำนวนครั้งในการใช้สิทธิ',
                                                           legend = dict(orientation = 'h', font = dict(family = 'sans-serif', size = 12)),
                                                           yaxis = dict(title = 'มูลค่าสิทธิ ฿',
                                                                        side = 'left',
                                                                        range = [0, max([amt_user[p][1] for p in amt_user.keys()]) + 1000000000],
                                                                        anchor = 'x', showgrid = False),
                                                           yaxis2 = dict(title = 'จำนวนสิทธิที่ใช้',
                                                                        overlaying = 'y',
                                                                        side = 'right',
                                                                        range = [0, max([amt_user[p][0] for p in amt_user.keys()]) * 2],
                                                                        anchor = 'x', showgrid = True))})]
]

graph_asof = [
    [dcc.Graph(id = 'donut_chart', figure = {'data' : [{'labels' : [p for p in accum_data['relation_desc_group']],
                                                         'values' : [m for m in accum_data['cnt_cust']],
                                                         'type' : 'pie',
                                                         'hole' : 0.5,
                                                        'hovertext' : ['{0} = {1:,.1f}%'.format(k,j * 100) for k,j in zip(accum_data['relation_desc_group'], accum_data['cnt_cust'])],
                                                        'hoverinfo' : 'text',
                                                        'marker' : dict(colors = ['#e55039','#7bed9f','#60a3bc'], line = dict(color = '#2C3A47', width = 2))
                                                         }],
                                            'layout' : dict(title = '%Active ของผู้ใช้สิทธิ ณ เดือนนั้น',
                                                           legend = dict(orientation = 'h', font = dict(family = 'sans-serif', size = 12)))})],
    [dcc.Graph(id = 'bar_split', figure = {'data' : [{'x': [m*100 for m in gov_hosp['cnt_cust_pct']],
                                                      'y' : [k for k in gov_hosp['hospital_department']],
                                                      'type' : 'bar',
                                                      'name' : 'รัฐบาล',
                                                      'orientation' : 'h',
                                                      'hovertext' : ['รัฐบาล - {:,.2f}%'.format(w*100) for w in gov_hosp['cnt_cust_pct']],
                                                      'hoverinfo' : 'text',
                                                      'marker' : dict(color = 'rgba(246, 78, 139, 0.6)',
                                                                      line = dict(color='rgba(246, 78, 139, 1.0)', width=2))},
                                                    {'x' : [h*100 for h in priv_hosp['cnt_cust_pct']],
                                                     'y' : [m for m in priv_hosp['hospital_department']],
                                                     'type' : 'bar',
                                                     'name' : 'เอกชน',
                                                     'orientation' : 'h',
                                                     'hovertext' : ['เอกชน - {:,.2f}%'.format(n*100) for n in priv_hosp['cnt_cust_pct']],
                                                     'hoverinfo' : 'text',
                                                     'marker' : dict(color = 'rgba(58, 71, 80, 0.6)',
                                                                     line = dict(color='rgba(58, 71, 80, 1.0)', width=2))}],
                                           'layout' : dict(barmode = 'stack',
                                                           title = '% ใช้สิทธิตามประเภทและแผนกของโรงพยาบาลที่ไปใช้สิทธิ',
                                                           legend = dict(font = dict(family = 'sans-serif', size = 12)),
                                                           yaxis = dict(size = 9))})]
]

graph_daily_cnt = [
    [dcc.Graph(id = 'bar_daily', figure = {'data' : [{'x' : [n for n in daily_cnt['last_date']],
                                                      'y' : [r for r in daily_cnt['daily_cust']],
                                                      'type' : 'bar',
                                                      'name' : 'จำนวนผู้มาใช้สิทธิ',
                                                      'text' : ['{:,.1f}k'.format(x/1000) for x in daily_cnt['daily_cust']],
                                                      'textposition' : 'outside',
                                                      'hoverinfo' : 'skip',
                                                      'marker' : dict(color = '#6a89cc', line = dict(color = '2C3A47', width = 2))
                                                     }],
                                          'layout' : dict(title = 'จำนวนผู้มาใช้สิทธิรายวัน', 
                                                          legend = dict(orientation = 'h',
                                                                        font = dict(family = 'sans-serif', 
                                                                                    size = 12)),
                                                          xaxis = dict(title = 'วันที่'),
                                                          yaxis = dict(title = 'จำนวนผู้มาใช้สิทธิ',
                                                                       side = 'left',
                                                                       range = [0, max([r for r in daily_cnt['daily_cust']]) + 30000]),
                                                          showgrid = True)})]
]

graph_daily_amt = [
    [dcc.Graph(id = 'bar_daily_amt', figure = {'data' : [{'x' : [j for j in daily_cnt['last_date']],
                                                          'y' : [l for l in daily_cnt['cnt_cust']],
                                                          'type' : 'bar',
                                                          'name' : 'จำนวนผู้มาใช้สิทธิสะสม',
                                                          'text' : ['{:,.1f}k'.format(m/1000) for m in daily_cnt['cnt_cust']],
                                                          'textposition' : 'outside',
                                                          'hoverinfo' : 'skip',
                                                          'marker' : dict(color = '#78e08f', line = dict(color = '2C3A47', width = 2))},
                                                         {'x' : [j for j in daily_cnt['last_date']],
                                                          'y' : [d for d in daily_cnt['sum_amt']],
                                                          'type' : 'line',
                                                          'name' : 'มูลค่าการใช้สิทธิสะสม',
                                                          'hovertext' : ['{:.2f} พันล้านบาท'.format(k/1000000000) for k in daily_cnt['sum_amt']],
                                                          'hoverinfo' : 'text',
                                                          'yaxis' : 'y2'}],
                                              'layout' : dict(title = 'จำนวนผู้ใช้สิทธิและมูลค่าการใช้สิทธิสะสม',
                                                              legend = dict(orientation = 'h',
                                                                            font = dict(family = 'san-serif', 
                                                                                        size = 12)),
                                                              xaxis = dict(title = 'วันที่'),
                                                              yaxis = dict(title = 'จำนวนผู้มาใช้สิทธิ',
                                                                           side = 'left',
                                                                           anchor = 'x',
                                                                           range = [0, max([l for l in daily_cnt['cnt_cust']]) + 100000],
                                                                           showgrid = False),
                                                              yaxis2 = dict(title = 'มูลค่าของสิทธิทั้งหมด (พันบ้านบาท)',
                                                                            overlaying = 'y',
                                                                            side = 'right', 
                                                                            anchor = 'x',
                                                                            range = [0, max([d for d in daily_cnt['sum_amt']]) + 1000000000],
                                                                            showgrid = True))})]
]

app.layout = dbc.Container(
    [
        dcc.Tabs([
            dcc.Tab(label = 'รายงานสรุปรายเดือน', children = [
                html.Br(),
                html.H1("รายงานสิทธิรักษาพยาบาลข้าราชการย้อนหลัง", style={'text-align': 'center', 'color' : '#17c0eb'}),
                html.Hr(),
                Header('เงื่อนไขเสี่ยงที่ก่อให้เกิดการทุจริต - {0}'.format(str(latest_date)), app),
                dbc.Row([dbc.Col(fraud) for fraud in fraud_box]),
                html.Br(),
                html.Br(),
                Header('ข้อมูลย้อนหลัง 3 เดือน - ({0} ถึง {1})'.format(str(oldest_date), str(latest_date)), app),
                dbc.Row([dbc.Col(graph) for graph in graph_comp]),
                html.Br(),
                html.Hr(),
                Header('ข้อมูล ณ สิ้นเดือนก่อนหน้า - {0}'.format(str(latest_date)), app),
                dbc.Row([dbc.Col(graph2) for graph2 in graph_asof])
            ]),
            dcc.Tab(label = 'รายงานสรุปรายวัน', children = [
                html.Br(),
                html.H1("รายงานสิทธิรักษาพยาบาลข้าราชการรายวัน - ถึงวันที่ {0}".format(last_daily), style={'text-align': 'center', 'color' : '#0c2461'}),
                html.Hr(),
                Header('เงื่อนไขเสี่ยงที่ก่อให้เกิดการทุจริต', app),
                dbc.Row([dbc.Col(fraud_daily) for fraud_daily in fraud_box_daily]),
                html.Br(),
                html.Br(),
                Header('ข้อมูลรายวัน', app),
                dbc.Row([dbc.Col(graph3) for graph3 in graph_daily_cnt]),
                html.Hr(),
                html.Br(),
                dbc.Row([dbc.Col(graph4) for graph4 in graph_daily_amt])
            ])])])

if __name__ == "__main__":
    app.run_server(debug=False)

