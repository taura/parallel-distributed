#!/usr/bin/python3
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
import pandas as pd 
import numpy as np
import sqlite3
import time

################################################
# the app object
################################################

if __name__ == "__main__":
    app = dash.Dash(__name__)
else:
    app = dash.Dash(__name__, requests_pathname_prefix='/viewer/')

application = app.server
a_sqlite = "/home/tau/public_html/lecture/parallel_distributed/parallel-distributed-handson/20vgg/records/vgg_records/a.sqlite"

################################################
# nuts and bolts
################################################

def do_sql(conn, cmd):
    # print(cmd)
    return conn.execute(cmd)

def preface_div():
    div = html.Div([
        html.H2("Preface", style=h2_style()),
        html.P("This is a page showing the results of executing vgg."
               " It accumulates all submitted results and allows you to"
               " choose runs you are interested in"
               " and see different aspects of them."),
        html.P(["In order to submit a result, you do",
                html.Pre("  ssh YOUR-USER-ID-ON-TAULEC@taulec.zapto.org submit < vgg.log"),
                " from IST (or whichever machine you have vgg.log in)"]),
        html.P(["If you are not able to ssh from IST to taulec, see ",
                html.A("this page",
                       href="https://www.eidos.ic.i.u-tokyo.ac.jp/~tau/lecture/parallel_distributed/html/ist_cluster.html#ist-to-taulec",
                       target="_blank")]),
        
    ])
    return div

################################################
# selector + run table
################################################

def run_table_div():
    cols = [(1, "seqid"),(1, "owner"),(1, "host"),(1, "algo_s"),(1, "gpu_algo"),
            (1, "batch_sz"),(1, "iters"),(1, "learnrate"),
            (1, "partial_data"),(1, "single_batch"),
            (1, "start_at"),(1, "end_at"),
            (1, "pt(end_at) - pt(start_at) as elapsed"),
            (1, "(pt(end_at) - pt(start_at)) / (batch_sz * iters) as tps"),
            (0, "verbose"),(0, "cifar_data"),
            (0, "dropout"),(0, "validate_ratio"),(0, "validate_interval"),
            (0, "sample_seed"),(0, "weight_seed"),(0, "dropout_seed"),(0, "partial_data_seed"),
            (0, "grad_dbg"),(0, "algo"),
            (0, "log"),(0, "USER"),(0, "PWD"),
            (0, "SLURM_SUBMIT_DIR"),(0, "SLURM_SUBMIT_HOST"),(0, "SLURM_JOB_NAME"),(0, "SLURM_JOB_CPUS_PER_NODE"),
            (0, "SLURM_NTASKS"),(0, "SLURM_NPROCS"),(0, "SLURM_JOB_ID"),(0, "SLURM_JOBID"),
            (0, "SLURM_NNODES"),(0, "SLURM_JOB_NUM_NODES"),(0, "SLURM_NODELIST"),(0, "SLURM_JOB_PARTITION"),
            (0, "SLURM_TASKS_PER_NODE"),(0, "SLURM_JOB_NODELIST"),(0, "CUDA_VISIBLE_DEVICES"),(0, "GPU_DEVICE_ORDINAL"),
            (0, "SLURM_CPUS_ON_NODE"),(0, "SLURM_TASK_PID"),(0, "SLURM_NODEID"),(0, "SLURM_PROCID"),
            (0, "SLURM_LOCALID"),(0, "SLURM_JOB_UID"),(0, "SLURM_JOB_USER"),(0, "SLURM_JOB_GID"),
            (0, "SLURMD_NODENAME"),]
    all_cols = [col for val, col in cols]
    on_cols = [col for val, col in cols if val]
    # seqid,start_at,verbose,cifar_data,batch_sz,learnrate,iters,partial_data,single_batch,dropout,
    # validate_ratio,validate_interval,sample_seed,weight_seed,dropout_seed,partial_data_seed,
    # grad_dbg,algo_s,algo,gpu_algo,log,host,
    # USER,PWD,SLURM_SUBMIT_DIR,SLURM_SUBMIT_HOST,SLURM_JOB_NAME,SLURM_JOB_CPUS_PER_NODE,
    # SLURM_NTASKS,SLURM_NPROCS,SLURM_JOB_ID,SLURM_JOBID,SLURM_NNODES,SLURM_JOB_NUM_NODES,
    # SLURM_NODELIST,SLURM_JOB_PARTITION,SLURM_TASKS_PER_NODE,SLURM_JOB_NODELIST,
    # CUDA_VISIBLE_DEVICES,GPU_DEVICE_ORDINAL,SLURM_CPUS_ON_NODE,SLURM_TASK_PID,
    # SLURM_NODEID,SLURM_PROCID,SLURM_LOCALID,SLURM_JOB_UID,SLURM_JOB_USER,SLURM_JOB_GID,
    # SLURMD_NODENAME,end_at,owner
    div = html.Div([
        html.H2("Select runs to display", style=h2_style()),
        html.P("Build an SQL expression below"),
        html.P(('In order to be useful, you do not want to display too many runs.'
                ' Come up with a filtering expression that chooses what you want to compare.'
                ' I will hopefully make some buttons to quickly display most "interesting" runs'
                ' (e.g., "best" in various criterion, such as best samples/time, best achieved loss, etc.)')),
        html.P(["select "]),
        html.P([dcc.Checklist(id="sql_selected",
                              options=[{"label" : "{}, ".format(x), "value" : x} for x in all_cols],
                              value=on_cols),
                dcc.Input(id="sql_selected2", value="")]),
        html.P(["from info where ", dcc.Input(id="sql_where")]),
        html.P(["group by ", dcc.Input(id="sql_group_by")]),
        html.P(["order by ", dcc.Input(id="sql_order_by", value="tps")]),
        html.P(["limit ", dcc.Input(id="sql_limit", value="100")]),
        html.P([html.Button("update", id="sql_update_button")]),
        html.P("", id="sql_cmd"),
        html.P("", id="how_many_runs"),
        dcc.Graph(id="run_table"),
        # dcc.Graph(id="cols_table"),
    ])
    return div

def parse_time(st):
    #print("parse_time(%s)" % st)
    return time.mktime(time.strptime(st, "%Y-%m-%dT%H-%M-%S"))

def sqlite_connect(a_sqlite):
    conn = sqlite3.connect(a_sqlite)
    conn.row_factory = sqlite3.Row
    conn.create_function("pt", 1, parse_time)
    return conn

def build_sql(selected, selected2, where, group_by, order_by, limit):
    where = "where {}".format(where) if where else ""
    group_by = "group by {}".format(group_by) if group_by else ""
    order_by = "order by {}".format(order_by) if order_by else ""
    selected2 = [x for x in selected2.strip().split(",") if x != ""]
    limit = "limit {}".format(limit) if limit != "" else ""
    cmd = ("select {} from info {} {} {} {}"
           .format(",".join(selected + selected2), where, group_by, order_by, limit))
    return cmd

@app.callback(
    Output("sql_cmd",  "children"),
    Output("how_many_runs",  "children"),
    Output("run_table",      "figure"),
    Input( "sql_update_button", "n_clicks"),
    State( "sql_selected", "value"),
    State( "sql_selected2", "value"),
    State( "sql_where", "value"),
    State( "sql_group_by", "value"),
    State( "sql_order_by", "value"),
    State( "sql_limit", "value"),
)
def update_run_table(n_clicks, selected, selected2, where, group_by, order_by, limit):
    conn = sqlite_connect(a_sqlite)
    cmd = build_sql(selected, selected2, where, group_by, order_by, limit)
    result = list(do_sql(conn, cmd))
    conn.close()
    if len(result) > 0:
        row = result[0]
        cols = list(row.keys())
        cells = [[row[c] for row in result] for c in cols]
    else:
        cols = []
        cells = []
    table = go.Table(header=dict(values=cols), cells=dict(values=cells))
    run_tbl = go.Figure(data=[table])
    run_tbl.update_layout(height=500)
    n_runs = "%d runs selected" % len(result)
    return cmd, n_runs, run_tbl

################################################
# loss accuracy
################################################

def loss_accuracy_graph_div():
    cols = ["samples", "t",
            "train_loss", "train_accuracy", "validate_loss", "validate_accuracy"]
    options = [{'label': x, 'value': x} for x in cols]
    div = html.Div([
        html.H2("Loss/accuracy evolution with samples/time", style=h2_style()),
        html.P("This section is mainly for displaying how loss or accuracy evolves over time.  x-axis is typically t (for wall clock time time) or samples (the number of samples trained) and y-axis loss (measured by the cross entropy between the predicted probability distribution over the ten classses and the true distribution (1 for the true class and 0 for others)) or accuracy (the proportion of the correctly labeled samples).  Each is measured for training samples (a mini batch) or the samples left for validation."),
        html.P("You may also want to set x-axis to t and y-axis samples, to show the throughput of your program in terms of samples/sec."),
        html.P("choose x-axis:"),
        dcc.RadioItems(id="loss_accuracy_graph_x", options=options, value="samples"),
        html.P("choose y-axis:"),
        dcc.RadioItems(id="loss_accuracy_graph_y", options=options, value="train_loss"),
        dcc.Graph(id="loss_accuracy_graph"),
    ])
    return div

@app.callback(
    Output("loss_accuracy_graph",      "figure"),
    Input( "loss_accuracy_graph_x",    "value"),
    Input( "loss_accuracy_graph_y",    "value"),
    Input( "sql_update_button", "n_clicks"),
    State( "sql_selected", "value"),
    State( "sql_selected2", "value"),
    State( "sql_where", "value"),
    State( "sql_group_by", "value"),
    State( "sql_order_by", "value"),
    State( "sql_limit", "value"),
)
def update_loss_accuracy_graph(selected_x, selected_y, n_clicks, selected, selected2, where, group_by, order_by, limit):
    conn = sqlite_connect(a_sqlite)
    cmd = build_sql(selected, selected2, where, group_by, order_by, limit)
    seqids = [row["seqid"] for row in do_sql(conn, cmd)]
    cmdx = ("select {},{},seqid from loss_accuracy where seqid in ({}) order by {}"
            .format(selected_x, selected_y, ",".join([str(x) for x in seqids]), selected_x))
    result = list(do_sql(conn, cmdx))
    conn.close()
    x = [row[selected_x] for row in result]
    y = [row[selected_y] for row in result]
    seqid = [row["seqid"] for row in result]
    df = pd.DataFrame(dict(x=x, y=y, seqid=seqid))
    fig = px.line(df, x="x", y="y", color="seqid")
    return fig

################################################
# kernel times table
################################################

def kernel_times_table_div():
    div = html.Div([
        dcc.Graph(id="kernel_times_table"),
    ])
    return div

#@app.callback(
#    Output("kernel_times_table",      "figure"),
#    Input( "sql_selector", "value"),
#)
def update_kernel_times_table(kernel_times_table_cond):
    conn = sqlite3.connect(a_sqlite)
    where = "where {}".format(kernel_times_table_cond) if kernel_times_table_cond else ""
    cols = ["seqid", "cls", "cargs", "fun", "fargs", "sum(t1-t0)", "sum(dt)"]
    cmd = ("""select {} from kernel_times 
    {}
    group by seqid,cls,cargs,fun,fargs"""
           .format(",".join(cols), where))
    result = list(do_sql(conn, cmd))
    conn.close()
    cells = [[row[i] for row in result] for i in range(len(cols))]
    table = go.Table(header=dict(values=cols), cells=dict(values=cells))
    fig = go.Figure(data=[table])
    fig.update_layout(height=1000)
    return fig

################################################
# kernel times graph
################################################

def kernel_times_bar_chart_div():
    div = html.Div([
        html.H2("Execution time breakdown", style=h2_style()),
        html.P("Per-sample execution time of each kernel, in the form of stacked bar chart."
               " This is useful when you want to see the performance of your parallelized/vectorized/optimized code relative to baseline (either by you or friends)."
               " Each area in the stack shows time spent per sample in each function."
               " That is, the time is the total time spent in each function / total number of samples processed."),
        # html.Ul([
        #     html.Li(["select *,sum(dt)/sum(b-a) from kernel_times where ", dcc.Input(id="kernel_times_where", value=""), " group by ", dcc.Input(id="kernel_times_group_by", value="cls,fun"), " ", html.Button("update", id="kernel_times_update_button")])
        # ]),
        # html.P("Specify above an expressions to choose kernels of interest and attributes with which to group (aggregate) their execution times."),
        # html.P("Below are 10 selected records of kernel execution times."
        #        " You can specify expressions involving the columns of the table to choose kernels."),
        # html.Ul([
        #     html.Li("cls : kernel name such as Convolution2D, Linear, etc.  Each kernel is implemented as a class template taking size parameters."),
        #     html.Li("cargs : values that instantiate the class templates, representing the size of input/output/parameters"),
        #     html.Li("fun : function name, either of forward, backward, or update"),
        # ]
        # ),
        # html.P("For example,"),
        # html.Ul([
        #     html.Li('cls = "Linear" : only shows execution time of the Linear kernel'),
        #     html.Li('fun = "forward" : only shows forward kernels'),
        # ]
        # ),
        # dcc.Graph(id="kernel_times_table"),
        # html.P('In the second box (after "group by") above, you can specify a comma-separated list of columns (attributes) with which to group (aggregate) their execution times.'
        #        ' For example,'),
        # html.Ul([
        #     html.Li('cls,fun : distinguishes Convolution2D::forward, Convolution2D::backward, Convolution2D::update, Linear::forward, etc.,'
        #             ' but does not distinguish different instantiations of Convolution2D with different size parameters.'),
        #     html.Li('cls,cargs,fun : distinguishes different instantiations of all kernels'),
        # ]),
        dcc.Graph(id="kernel_times_bar_chart"),
    ])
    return div

def make_kernel_name(row, group_by):
    dic = dict(row)
    cls = dic.get("cls")
    cargs = dic.get("cargs")
    fun = dic.get("fun")
    fargs = dic.get("fargs")
    cls_cargs = "{}{}".format((cls if cls else ""), (cargs if cargs else ""))
    fun_fargs = "{}{}".format((fun if fun else ""), (fargs if fargs else ""))
    if cls_cargs:
        return "{}::{}".format(cls_cargs, fun_fargs)
    else:
        return fun_fargs

@app.callback(
    # Output("kernel_times_table",      "figure"),
    Output("kernel_times_bar_chart",  "figure"),
    Input( "sql_update_button", "n_clicks"),
    # Input( "kernel_times_update_button", "n_clicks"),
    State( "sql_selected", "value"),
    State( "sql_selected2", "value"),
    State( "sql_where", "value"),
    State( "sql_group_by", "value"),
    State( "sql_order_by", "value"),
    State( "sql_limit", "value"),
    #State( "kernel_times_where", "value"),
    #State( "kernel_times_group_by", "value"),
)
def update_kernel_times_bar_chart(sql_selector_n_clicks, 
                                  selected, selected2, where, group_by, order_by, limit):
    kernel_times_where = ""
    kernel_times_group_by = "cls,fun"
    conn = sqlite_connect(a_sqlite)
    cmd = build_sql(selected, selected2, where, group_by, order_by, limit)
    print("cmd=", cmd)
    seqids = [row["seqid"] for row in do_sql(conn, cmd)]
    kernel_times_where = "and {}".format(kernel_times_where) if kernel_times_where else ""
    kernel_times_group_by = "seqid,{}".format(kernel_times_group_by) if kernel_times_group_by else "seqid"
    # table
    if 0:
        cmd0 = ("""select *
        from kernel_times 
        where seqid in ({}) {}
        limit 10
        """.format(",".join([str(x) for x in seqids]), kernel_times_where))
        print("cmd0=", cmd0)
        result0 = list(do_sql(conn, cmd0))
        print("{} results".format(len(result0)))
        if len(result0) > 0:
            row = result0[0]
            cols = row.keys()
            cells = [[row[col] for row in result0] for col in cols]
        else:
            cols = []
            cells = []
        table = go.Table(header=dict(values=cols), cells=dict(values=cells))
        tbl = go.Figure(data=[table])
    if 1:
        # graph
        cmd1 = ("""select {},sum(dt)/sum(b-a) as avg_dt
        from kernel_times 
        where seqid in ({}) {}
        group by {}
        order by seqid,avg_dt desc
        """.format(kernel_times_group_by, ",".join([str(x) for x in seqids]),
                   kernel_times_where,
                   kernel_times_group_by))
        print("cmd1=", cmd1)
        result1 = list(do_sql(conn, cmd1))
        print("{} results".format(len(result1)))
        seqid = [str(row["seqid"]) for row in result1]
        kernel = [make_kernel_name(row, kernel_times_group_by) for row in result1]
        avg_dt = [row["avg_dt"] for row in result1]
        df = pd.DataFrame({"seqid" : seqid, "kernel" : kernel, "avg_dt" : avg_dt})
        fig = px.bar(df, x="seqid", y="avg_dt", color="kernel")
        fig.update_layout(height=1000)
    conn.close()
    return fig

################################################
# the whole page
################################################

def h1_style():
    return {
        "textAlign" : "center",
        "border-color" : "#99A1AA",
        "background-color" : "#BBDDBB"
    }

def h2_style():
    return {
        "border-color" : "#99A1AA",
        "background-color" : "#CCEECC"
    }

app.layout = html.Div(
    [
        html.H1("Records of VGG Executions", style=h1_style()),
        preface_div(),
        run_table_div(),
        kernel_times_bar_chart_div(),
        loss_accuracy_graph_div(),
    ],
    style={"padding": "2%", "margin": "auto"},
)

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")
