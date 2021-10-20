import os
import requests
import json
import re
from tabulate import tabulate
import html
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

default_args = {'owner': 'airflow'}
AUTH_USER = 'otestsender'
AUTH_PASSWORD = 'SzX~B8Cotl8X'
DEPARTMENT = 'company.100.02.05'
DEPARTMENTS=['company.100.02.05.06','company.100.02.05.05','company.100.02.05.04']
EXCLUDED_LOGIN = ['nmalinovskaya', '^company','otestsender']  # ??????????? ??????
RECIVERS = ['abaturin', 'nmalinovskaya', 'nmedvediuk','tchuvanko']  # ?????????? ?????? ??????????
# RECIVERS = ['abaturin']
ERROR_RECIVERS = ['abaturin']  # ?????????? ?????? ??????????
TASK_CATEGORY = [
    'CAT_TESTTASK', 'CAT_ACCEPTTASK', 'CAT_QAJOB', 'CAT_REGTESTTASK',
    'CAT_ANALTASK', 'CAT_FIRSTANAL', 'CAT_BUSINESSANAL', 'CAT_CONFIRMATION',
    'CAT_MAINTENANCE', 'CAT_MIGRATION', 'CAT_DEVTASK', 'CAT_SUPPORT', 'CAT_TEACHROLE',
    'CAT_GAP_FEATURE', 'CAT_GAP', 'CAT_POTENTIALGAP', 'CAT_TECHTASK'
]  # ????????? ????? ??? ??????

TIME_DELTA = 0
curr_date = datetime.isoformat(datetime.today() + timedelta(days=TIME_DELTA))

with DAG(
        'planning_and_penalty_prod',
        default_args=default_args,
        description='?????? ? ??????????? ?????? ? ????????????????',
        schedule_interval="30 8 * * 1-5",
        start_date=days_ago(0, minute=5),
        tags=['notify']
) as dag:
    def category_task(data):
        """????????? ??????"""
        return data["category"]["id"]


    def fact_time(data):
        """?????????? ??????????? ????? """
        return data["abudget"]


    def plan_time(data):
        """??????????? ????? ??? ???????????"""
        try:
            return int(data["udfs"]["UDF_WORKTASK_AWAITBUDGET"]["numberValue"] * 3600)
        except Exception:
            return False


    def user_time(data):
        """????????? ???? ??????????"""
        try:
            return int(data["udfs"]["UDF_WORKTASK_PLANBUDGET"]["numberValue"] * 3600)
        except Exception:
            return False


    def task_category(data):
        """????????? ??????"""
        try:
            return data["category"]["name"]
        except Exception:
            return False


    def inplanning(data):
        """?????? ?? ????????????????"""
        try:
            if data["udfs"]["UDF_WORKTASK_INREPLAN"]["listValue"][0]['code'] == 'YES':
                return True
            else:
                return False
        except Exception:
            return False


    def plan_date(data):
        """??????????? ???? ??????????"""
        try:
            return data["udfs"]["UDF_WORKTASK_PLANTD"]["dateValue"][0:10]
        except Exception:
            return False


    def wait_date(data):
        """????????? ???? ??????????"""
        try:
            return data["udfs"]["UDF_WORKTASK_AWAITTD"]["dateValue"][0:10]
        except Exception:
            return False


    def analyze_date(data):
        """???? ?????????? ???????????????? ???????"""
        try:
            return data["udfs"]["UDF_WORKTASK_ANALYSISFD"]["dateValue"][0:10]
        except Exception:
            return False


    def template_table(table):
        """"""
        return f"""
                <html>
                <head>
                <style> 
                table, th, td {{ border: 1px solid black; border-collapse: collapse; }}
                th, td {{ padding: 5px; }}
                </style>
                </head>
                <body>
                {table}
                </body></html>
                """


    def send_mess(data, desc, receiver):
        server = "mail.colvir.ru"
        server_password = AUTH_PASSWORD
        message = MIMEMultipart()
        message['From'] = f"{AUTH_USER}@colvir.ru"
        message['To'] = receiver
        message['Subject'] = desc
        data = template_table(data)
        body = html.unescape(data)

        message.attach(MIMEText(body, "html"))
        msg_body = message.as_string()

        with smtplib.SMTP_SSL(server, 465) as smtp:
            smtp.ehlo()
            smtp.login(message['From'], server_password)
            smtp.sendmail(message['From'], message['To'], msg_body)
            smtp.quit()


    def prepare(**kwargs):
        """??????? ?????????? ??????????"""
        for dirpath, dirnames, filenames in os.walk("."):
            for filename in filenames:
                result = re.search(r'_task.json', filename)
                if result:
                    print(filename)
                    path = os.path.join(os.path.abspath(filename))
                    print(path)
                    os.remove(path)


    def load_user():
        """???????? ?????? ????????????? ??? ?????????? ??????? ?????"""
        url_user = f"https://cdp.colvir.ru/TrackStudio/rest/user/children/{DEPARTMENT}?recursive=true&active=true"

        response = requests.get(
            url=url_user,
            auth=(AUTH_USER, AUTH_PASSWORD)
        )
        users = response.json()
        excluded_logins = re.compile("(" + "|".join(EXCLUDED_LOGIN) + ")")
        user_list = [
            {'login': user["login"], 'name': user["name"]} for user in users if
            not excluded_logins.search(user["login"])
        ]
        return user_list


    # def load_user():
    #     """???????? ?????? ????????????? ??? ?????????? ??????? ?????"""
    #     user_list = []
    #     for department in DEPARTMENTS:
    #         url_department = f"https://cdp.colvir.ru/TrackStudio/rest/user/{department}"
    #         response = requests.get(
    #             url=url_department,
    #             auth=(AUTH_USER, AUTH_PASSWORD)
    #         )
    #         department_info = response.json()
    #
    #         url_user = f"https://cdp.colvir.ru/TrackStudio/rest/user/children/{department}?recursive=true&active=true"
    #         response = requests.get(
    #             url=url_user,
    #             auth=(AUTH_USER, AUTH_PASSWORD)
    #         )
    #         users = response.json()
    #         for user in users:
    #             user_list.append({'login': user["login"], 'name': user["name"], "department": department_info["name"]})
    #
    #     return user_list


    def get_task(user, **kwargs):
        """???????? ?????? ????? ??? ???????????? ?? login, ????????? ? json"""
        login = user['login']
        user_name = user['name']
        url_department = f"https://cdp.colvir.ru/TrackStudio/rest/udfval/UDF_PRS_DEP/value/user/{login}"
        response = requests.get(
            url=url_department,
            auth=(AUTH_USER, AUTH_PASSWORD)
        )
        department_info = response.json()
        department=department_info["userValue"][0]["name"]
        url_task_user = f"https://cdp.colvir.ru/TrackStudio/rest/portlet/personalqueue/{login}/tasks"
        response_task = requests.get(url=url_task_user, auth=(AUTH_USER, AUTH_PASSWORD))
        tasks_users = response_task.json()
        task_categories = re.compile("(" + "|".join(TASK_CATEGORY) + ")")

        tasks_users = [{'task_id': tasks_user["id"], "login": login, "user_name": user_name, "department":department ,
                        "info": {}, "planning": 0,"penalty": 0, "desc": []} for tasks_user in tasks_users if
                       task_categories.search(tasks_user["category"]["id"])]

        with open(f'{login}_task.json', 'w', encoding='utf-8') as f:
            json.dump(tasks_users, f, ensure_ascii=False, indent=4)


    def analyze_task(user, **kwargs):
        """?????? ????? ?? ????????? ???????????? ? ??????"""
        login = user['login']
        filename = f'{login}_task.json'
        with open(filename, 'r', encoding='utf-8') as f:
            user_tasks = json.load(f)
            for user_task in user_tasks:
                task_id = user_task["task_id"]
                url_task_info = f"https://cdp.colvir.ru/TrackStudio/rest/task/infoById/{task_id}"
                response = requests.get(url=url_task_info, auth=(AUTH_USER, AUTH_PASSWORD))
                task = response.json()
                user_task['info'] = {"name": task["name"], 'number': task["number"], 'link': task["taskLink"]}

                if inplanning(task):
                    user_task['planning'] = 1

                if not inplanning(task):
                    ftime = fact_time(task)
                    ptime = plan_time(task)
                    utime = user_time(task)
                    pdate = plan_date(task)
                    wdate = wait_date(task)
                    adate = analyze_date(task)

                    if any([pdate, wdate, adate]):
                        if wdate:
                            if curr_date > wdate:
                                user_task['penalty'] = 1
                                user_task['desc'].append(f'<div>????????? ???? ?????????? {wdate} ?????? ??? ????? ??????? </div>')

                        elif adate and not pdate:
                            if curr_date > adate:
                                user_task['penalty'] = 1
                                user_task['desc'].append(
                                    f'<div>???? ?????????? ??????????? {adate} ?????? ??? ????? ??????? </div>')
                        elif pdate and not adate:
                            if curr_date > pdate:
                                user_task['penalty'] = 1
                                user_task['desc'].append(
                                    f'<div>?????????? ???? ?????????? {pdate} ?????? ??? ????? ??????? </div>')

                    if ftime and utime:
                        if ftime > utime:
                            fm, fs = divmod(ftime, 60)
                            fh, fm = divmod(fm, 60)

                            um, us = divmod(utime, 60)
                            uh, um = divmod(um, 60)

                            user_task['penalty'] = 1
                            user_task['desc'].append(
                                f'<div>??????????? ???????????? {fh} ? {fm} ?  ?????? ??????????????? {uh} ? {um} ?</div>')

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(user_tasks, f, ensure_ascii=False, indent=4)


    def notify_user_task(user, **kwargs):
        """ ?????????? ????????????"""
        list_penalty = []
        login = user['login']
        user_name = user['name']
        filename = f'{login}_task.json'
        print(filename)
        with open(filename, 'r', encoding='utf-8') as f:
            user_tasks = json.load(f)
            for task in user_tasks:
                if task['penalty'] == 1:
                    task_name = f"<a href={task['info']['link']}> {task['info']['name']} </a>"
                    task_number = f"<a href={task['info']['link']}> {task['info']['number']} </a>"
                    list_penalty.append([task_number, task_name, task['user_name'], ' '.join(task['desc'])])
        print(list_penalty)
        if len(list_penalty):
            list_penalty = tabulate(list_penalty, headers=['?????', '????????????', "?????????????", "???????????"],
                                    tablefmt='html')
            send_mess(data=list_penalty, desc=f'?????? ????????? ?????????? ?????? ? ?????? ???????????',
                      receiver=f'{login}@colvir.ru')


    def notify_boss_task(**kwargs):
        """ ?????????? ??? ?????"""
        list_planning = []
        list_penalty = []
        for dirpath, dirnames, filenames in os.walk("."):
            for filename in filenames:
                result = re.search(r'_task.json', filename)
                if result:
                    print(filename)
                    with open(filename, 'r', encoding='utf-8') as f:
                        user_tasks = json.load(f)
                        for task in user_tasks:
                            if task['penalty'] == 1:
                                task_name = '<a href=\"' + task['info']["link"] + '\">' + task['info']["name"] + '</a>'
                                task_number = '<a href=\"' + task['info']["link"] + '\">' + task['info'][
                                    "number"] + '</a>'
                                list_penalty.append([task['department'],task_number, task_name, task['user_name'], ' '.join(task['desc'])])
                            if task['planning'] == 1:
                                task_name = '<a href=\"' + task['info']["link"] + '\">' + task['info']["name"] + '</a>'
                                task_number = '<a href=\"' + task['info']["link"] + '\">' + task['info'][
                                    "number"] + '</a>'
                                list_planning.append([task['department'],task_number, task_name, task['user_name']])

        if len(list_penalty) > 0:
            list_penalty = sorted(list_penalty, key=lambda val: val[0])
            list_penalty = tabulate(
                list_penalty, headers=['?????????????', '?????', '????????????', "?????????????", "???????????"],
                                    tablefmt='html')
            for receiver in RECIVERS:
                send_mess(data=list_penalty, desc='?????? ????????? ?????????? ?????? ? ?????? ???????????',
                          receiver=f'{receiver}@colvir.ru')

        if len(list_planning) > 0:
            list_planning = sorted(list_planning, key=lambda val: val[0])
            list_planning = tabulate(list_planning, headers=['?????????????','?????', '????????????', "?????????????"], tablefmt='html')
            for receiver in RECIVERS:
                send_mess(data=list_planning, desc='?????? ????????? ???????????? ????????????????',
                          receiver=f'{receiver}@colvir.ru')


    def notify_error_task(**kwargs):
        text = "<div>ERROR DAG</div>"
        for receiver in ERROR_RECIVERS:
            send_mess(data=text, desc='?????? ????',
                      receiver=f'{receiver}@colvir.ru')


    users = load_user()
    task_prepare = PythonOperator(task_id=f'prepare', python_callable=prepare)
    task_notify_boss = PythonOperator(task_id=f'notify_boss', python_callable=notify_boss_task,
                                      trigger_rule=TriggerRule.ALL_SUCCESS)
    task_notify_error = PythonOperator(task_id=f'notify_error', python_callable=notify_error_task,
                                       trigger_rule=TriggerRule.ONE_FAILED)

    for user in users:
        login = user["login"]
        task_login = PythonOperator(task_id=f'tasks_{login}', python_callable=get_task, op_kwargs={'user': user})
        task_analyze = PythonOperator(task_id=f'analyze_{login}', python_callable=analyze_task,
                                      op_kwargs={'user': user})
        task_notify_user = PythonOperator(task_id=f'notify_{login}', python_callable=notify_user_task,
                                          op_kwargs={'user': user})
        task_prepare >> task_login >> task_analyze >> task_notify_user >> [task_notify_boss, task_notify_error]
