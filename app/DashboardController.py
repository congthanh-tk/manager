# import Base Controller
from BaseController import *

def day_time(type, data):
    value = []
    day = {}
    for i in range(24):
        t = ''
        if i<10:
            time_begin = data + ' 0' + str(i) + ':00:00'
            if i == 9:
                time_end   = data + ' ' + str(i+1) + ':00:00'
                t = str(i+1) + ':00'
            else:
                time_end   = data + ' 0' + str(i+1) + ':00:00'
                t = '0' + str(i+1) + ':00'
        else:
            time_begin = data + ' ' + str(i) + ':00:00'
            time_end   = data + ' ' + str(i+1) + ':00:00'
            t = str(i+1) + ':00'

        if type == 0:
            count = Histories.query.join(User).filter(User.company_id == current_user.company_id).join(User.roles).filter(Role.name == "user").filter((Histories.time>=time_begin) &  (Histories.time<=time_end)).count()
        elif type == 1:
            count = Histories.query.join(User).filter(User.company_id == current_user.company_id).join(User.roles).filter(Role.name == "staff").filter((Histories.time>=time_begin) &  (Histories.time<=time_end)).count()
        elif type == 2:
            count = User.query.filter((User.confirmed_at>=time_begin) &  (User.confirmed_at<=time_end)).count()
        elif type == 3:
            count = Histories.query.filter((Histories.time>=time_begin) &  (Histories.time<=time_end)).count()
        value.append(count)
        day[t] = count
    return day

def stringtodate(str):
    return datetime.strptime(str,'%Y-%m-%d')

def PlusDay(date):
    date = stringtodate(date)
    date = date + timedelta(days=1)
    return date.strftime('%Y-%m-%d')

def days_time(type, start, end):
    value = []
    days = {}
    data = start
    fis = PlusDay(end)
    while data != fis:
        time_begin = data + ' 00:00:00'
        time_end   = data + ' 23:59:59'
        if type == 0:
            count = Histories.query.join(User).join(User.roles).filter(User.company_id == current_user.company_id).filter(Role.name == "user").filter((Histories.time>=time_begin) &  (Histories.time<=time_end)).count()
        elif type == 1:
            count = Histories.query.join(User).join(User.roles).filter(User.company_id == current_user.company_id).filter(Role.name == "staff").filter((Histories.time>=time_begin) &  (Histories.time<=time_end)).count()
        elif type == 2:
            count = User.query.filter(User.confirmed_at>=time_begin) &  ((User.confirmed_at<=time_end)).count()
        elif type == 3:
            count = Histories.query.filter((Histories.time>=time_begin) &  (Histories.time<=time_end)).count()
        days[data]=count
        data = PlusDay(data)
    
    return days



@app.route('/chart', methods=['GET','POST'])
@login_required
@user_is("admin")
def chart():
    start =  request.form['start']
    end =  request.form['end']
    if current_user.has_roles("superuser"):
        if start == end:
            return json.dumps({
                "user": day_time(2, end),
                "history":  day_time(3, end)
            })
        else:
            return json.dumps({
                "user": days_time(2, start,end),
                "history":  days_time(3, start,end)
            })
    elif current_user.has_roles("admin"):
        if start == end:
            return json.dumps({
                "visitor": day_time(0, end),
                "staff":  day_time(1, end)
            })
        else:
            return json.dumps({
                "visitor": days_time(0, start,end),
                "staff":  days_time(1, start,end)
            })

@app.route('/detail-timeline.html')
@login_required
@user_is("admin")
def detailtimeline():

    user_id = request.args.get('id')
    if not user_id:
        user_id = current_user.id

    users = db.session.query(User).join(User.roles).filter(User.id == user_id).filter(User.is_unknown == False).filter(Role.name == "staff").first()

    #print(histories)
    return render_template( 'pages/detail-timeline.html', users=users)


@app.route('/detail_time_dashboard', methods=['POST'])
@login_required
@user_is("admin")
def detail_time_dashboard():
    output = json.dumps({"success": True})
    user_id = request.form['user_id']
    startDate = request.form['startDate']
    endDate = request.form['endDate'] + ' 23:59:59'
    startDatetime = date.today()
    endDatetime = date.today()
    if startDate and endDate:
        startDatetime = datetime.strptime(startDate,"%Y-%m-%d").date()
        endDatetime = datetime.strptime(endDate,"%Y-%m-%d %H:%M:%S")

        in_late_count = 0
        out_early_count = 0
        escape_count = 0

        histories = db.session.query(Cameras, Histories.id, func.min(Histories.time), func.max(Histories.time)).join(Cameras, Histories.camera == Cameras.id).filter(Histories.user_id == user_id).filter(Histories.time <= endDatetime).filter(Histories.time >= startDatetime).group_by(func.strftime("%Y-%m-%d", Histories.time)).all()
        
        for cam, history_id, history_start, history_end in histories:
            address = db.session.query(Addresses).join(Cameras, Cameras.address_id == Addresses.id).filter(Cameras.id == cam.id).first()
            if address and history_start and address.start and address.start < history_start.time():
                in_late_count = in_late_count + 1
           
            if address and history_end and address.end and address.end > history_end.time():
                out_early_count = out_early_count + 1

        escape_count = len(histories)
        return_output = json.dumps({"escape_count": escape_count, "in_late_count": in_late_count, "out_early_count": out_early_count})  
        return success_handle(return_output)
    else:
        return error_handle("date is empty.")


@app.route('/time_dashboard', methods=['POST'])
@login_required
@user_is("admin")
def time_dashboard():
    output = json.dumps({"success": True})
    selected_date =  request.form['selected_date']

    if selected_date:
        selected_datetime = datetime.strptime(selected_date,"%Y-%m-%d").date()
        print("==================")
        print(selected_datetime)
        print("==================")
        users = db.session.query(User).join(User.roles).filter(User.company_id == current_user.company_id).filter(User.is_unknown == False).filter(Role.name == "staff").all()

        in_late_count = 0
        out_early_count = 0
        escape_count = 0
        for user in users:
            address_start, h_start, start = db.session.query(Addresses, Histories, func.min(Histories.time)).join(Cameras, Cameras.id==Histories.camera).join(Addresses, Cameras.address_id==Addresses.id).filter(Histories.user_id == user.id).filter(Histories.time <= selected_datetime + timedelta(days=1)).filter(Histories.time >= selected_datetime).first()
            address_end, h_end, end = db.session.query(Addresses, Histories, func.max(Histories.time)).join(Cameras, Cameras.id==Histories.camera).join(Addresses, Cameras.address_id==Addresses.id).filter(Histories.user_id == user.id).filter(Histories.time <= selected_datetime + timedelta(days=1)).filter(Histories.time >= selected_datetime).first()
            if address_start and start and address_start.start and address_start.start < start.time():
                in_late_count = in_late_count + 1
           
            if address_start and end and address_start.end and address_start.end > end.time():
                out_early_count = out_early_count + 1

            if not start:
                escape_count = escape_count + 1
        return_output = json.dumps({"escape_count": escape_count, "in_late_count": in_late_count, "out_early_count": out_early_count})  
        return success_handle(return_output)
    else:
        return error_handle("date is empty.")


@app.route('/time_data')
@login_required
@user_is("admin")
def time_data():

    selected_date = request.args.get('selected_date')
    selected_datetime = date.today()
    if selected_date:
        selected_datetime = datetime.strptime(selected_date,"%Y-%m-%d").date()
        print("==================")
        print(selected_datetime)
        print("==================")
    # defining columns
    columns = [
        ColumnDT(User.id),
        ColumnDT(User.user),
        ColumnDT(User.full_name),
        ColumnDT(User.position),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
    ]
 
    # defining the initial query depending on your purpose
    query = db.session.query().select_from(User).join(User.roles).filter(User.company_id == current_user.company_id).filter(User.is_unknown == False).filter(Role.name == "staff")

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    for i in range(len(rowTable.output_result()["data"])):
        address_start, h_start, start = db.session.query(Addresses, Histories, func.min(Histories.time)).join(Cameras, Cameras.id==Histories.camera).join(Addresses, Cameras.address_id==Addresses.id).filter(Histories.user_id == rowTable.output_result()["data"][i]['0']).filter(Histories.time <= selected_datetime + timedelta(days=1)).filter(Histories.time >= selected_datetime).first()
        address_end, h_end, end = db.session.query(Addresses,Histories, func.max(Histories.time)).join(Cameras, Cameras.id==Histories.camera).join(Addresses, Cameras.address_id==Addresses.id).filter(Histories.user_id == rowTable.output_result()["data"][i]['0']).filter(Histories.time <= selected_datetime + timedelta(days=1)).filter(Histories.time >= selected_datetime).first()
        if start:
            rowTable.output_result()["data"][i]['4'] = start.strftime("%I:%M %p")
        else:
            rowTable.output_result()["data"][i]['4'] = ''

        if end:
            rowTable.output_result()["data"][i]['5'] = end.strftime("%I:%M %p")
        else:
            rowTable.output_result()["data"][i]['5'] = ''

        if start and end:
            elapsedTime = end - start
            hours = divmod(elapsedTime.total_seconds(), 3600)
            minutes = divmod(hours[1], 60)
            rowTable.output_result()["data"][i]['6'] = '%d giờ, %d phút' % (hours[0],minutes[0])
            pprint(rowTable.output_result()["data"][i]['6'])
        else:
            rowTable.output_result()["data"][i]['6'] = ''

        rowTable.output_result()["data"][i]['7'] = 0
        rowTable.output_result()["data"][i]['8'] = 0
        if (address_start and start and address_start.start):
            rowTable.output_result()["data"][i]['7'] = address_start.start < start.time()
        if (address_end and end and address_end.end):
            rowTable.output_result()["data"][i]['8'] = address_end.end > end.time()

    #print(rowTable.output_result())

    return jsonify(rowTable.output_result())



@app.route('/detail_time_data')
@login_required
@user_is("admin")
def detail_time_data():
    user_id = request.args.get('user_id')
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate') + ' 23:59:59'
    startDatetime = date.today()
    endDatetime = date.today()
    if startDate and endDate:
        startDatetime = datetime.strptime(startDate,"%Y-%m-%d").date()
        endDatetime = datetime.strptime(endDate,"%Y-%m-%d %H:%M:%S")
        print("==================")
        print(startDatetime)
        print(endDatetime)
        print("==================")

    # defining columns
    columns = [
        ColumnDT(Histories.id),
        ColumnDT(func.strftime("%Y-%m-%d", Histories.time)),
        ColumnDT(func.count(Histories.id)),
        ColumnDT(func.min(Histories.time)),
        ColumnDT(func.max(Histories.time)),
        ColumnDT(Cameras.id),
        ColumnDT(Cameras.id),
        ColumnDT(Cameras.id),
        ColumnDT(Cameras.id),
    ]
 
    # defining the initial query depending on your purpose
    #query = db.session.query().select_from(User).join(User.roles).filter(User.company_id == current_user.company_id).filter(User.is_unknown == False).filter(Role.name == "staff")
    query = db.session.query().select_from(Histories, Cameras).join(Cameras, Cameras.id == Histories.camera).filter(Histories.user_id == user_id).filter(Histories.time <= endDatetime).filter(Histories.time >= startDatetime).group_by(func.strftime("%Y-%m-%d", Histories.time))
    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    for i in range(len(rowTable.output_result()["data"])):
        if rowTable.output_result()["data"][i]['3'] and rowTable.output_result()["data"][i]['4']:
            elapsedTime = rowTable.output_result()["data"][i]['4'] - rowTable.output_result()["data"][i]['3']
            hours = divmod(elapsedTime.total_seconds(), 3600)
            minutes = divmod(hours[1], 60)
            rowTable.output_result()["data"][i]['5'] = '%d giờ, %d phút' % (hours[0],minutes[0])

        cam_id = int(rowTable.output_result()["data"][i]['6'])
        address = db.session.query(Addresses).join(Cameras, Cameras.address_id == Addresses.id).filter(Cameras.id == cam_id).first()
        rowTable.output_result()["data"][i]['6'] = 0
        rowTable.output_result()["data"][i]['7'] = 0
        if (address and address.start and address.end):
            rowTable.output_result()["data"][i]['6'] = address.start < rowTable.output_result()["data"][i]['3'].time()
            rowTable.output_result()["data"][i]['7'] = address.end > rowTable.output_result()["data"][i]['4'].time()

        if rowTable.output_result()["data"][i]['3']:
            rowTable.output_result()["data"][i]['3'] = rowTable.output_result()["data"][i]['3'].strftime("%I:%M %p")

        if rowTable.output_result()["data"][i]['4']:
            rowTable.output_result()["data"][i]['4'] = rowTable.output_result()["data"][i]['4'].strftime("%I:%M %p")

    return jsonify(rowTable.output_result())
