from BaseController import *

# ========== Statistics go late =====================
@app.route('/statistics_go_late.html')
@login_required
@user_is("admin")
def statistics_go_late():
    today = datetime.now().strftime('%Y-%m-%d')
    startTime = request.args.get('startTime') or today
    endTime = request.args.get('endTime') or today
    time = {"startTime": startTime, "endTime":endTime}
    address = request.args.get('address') or 0
    address = int(address)
    timeList = []
    diachi = {}
    if address:
        diachi = Addresses.query.filter_by(id=address).first()
        if diachi.start:
            tmp = diachi.start.strftime("%H:%M:%S")
            tmp = datetime.strptime(tmp,"%H:%M:%S")
            for i in range(7):
                timeList.append(tmp.strftime("%H:%M"))
                tmp = tmp + timedelta(minutes=10)
        diachi = diachi.to_dict()
    addressesData = []
    addresses = Addresses.query.filter_by(company_id=current_user.company_id).all()
    for addr in addresses:
        addressesData.append(addr.name)
    return render_template( 'pages/statistics_go_late.html', addresses=addresses, time=time, address=address, addressesData=addressesData, timeList=timeList, diachi=diachi)

@app.route('/statistical_go_late_data')
@login_required
@user_is("admin")
def statistical_go_late_data():
    """Return server side data."""
    startTime = request.args.get('startTime')
    endTime = request.args.get('endTime')
    address_id = request.args.get('address')
    address_id = int(address_id)
    startDatetime = datetime.strptime(startTime,"%Y-%m-%d").date()
    endDatetime = datetime.strptime(endTime,"%Y-%m-%d").date() + timedelta(days=1)
    # defining columns
    # defining the initial query depending on your purpose
    if int(address_id) == 0:
        columns = [
            ColumnDT(Addresses.id),
            ColumnDT(Addresses.name),
            ColumnDT(Addresses.address),
            ColumnDT(Addresses.id),
            ColumnDT(Addresses.id),
        ]
        query = db.session.query().select_from(Addresses).filter(Addresses.company_id==current_user.company_id)
    else:
        address_startTime = 0
        addr = Addresses.query.filter_by(id=address_id).first()
        if addr.start:
            address_startTime = addr.start
        columns = [
            ColumnDT(User.id),
            ColumnDT(User.full_name),
            ColumnDT(Addresses.address),
            ColumnDT(User.id),
            ColumnDT(User.id),
        ]
        query = db.session.query().select_from(User).join(Addresses).filter(User.company_id==current_user.company_id).filter(User.address_id==address_id)

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    total_avg = []
    for i in range(len(rowTable.output_result()["data"])):
        avg = 0
        id_ = rowTable.output_result()["data"][i]['0']
        if int(address_id):
            if address_startTime:
                historieTimes = []
                startDate = startDatetime
                endDate   = endDatetime
                while startDate != endDate:
                    historieTime = db.session.query(func.min(Histories.time)).filter(Histories.user_id==id_).filter(Histories.time < startDate + timedelta(days=1)).filter(Histories.time >= startDate).group_by(Histories.user_id).all()
                    startDate = startDate + timedelta(days=1)
                    if(len(historieTime)):
                        historieTimes.append(historieTime[0][0])
                if len(historieTimes):
                    for historieTime in historieTimes:
                        his_time = historieTime.time()
                        if his_time > address_startTime:
                            avg = avg + (datetime.combine(date.today(), his_time) - datetime.combine(date.today(), address_startTime)).total_seconds()
                    if len(historieTimes):
                        avg = avg/len(historieTimes)
                hours = divmod(avg, 3600)
                minutes = divmod(hours[1], 60)
                total_avg.append(avg)
                rowTable.output_result()["data"][i]['3'] = '%d giờ, %d phút' % (hours[0],minutes[0])
        else:
            addr = Addresses.query.filter_by(id=id_).first()
            if addr.start:
                address_startTime = addr.start
                camera_list = []
                cameras = Cameras.query.filter_by(company_id=current_user.company_id).filter_by(address_id=id_).all()
                for camera in cameras:
                    camera_list.append(camera.id)
                historieTimes = []
                startDate = startDatetime
                endDate   = endDatetime
                while startDate != endDate:
                    historieTime = db.session.query(func.min(Histories.time)).filter(Histories.camera.in_(camera_list)).filter(Histories.time < startDate + timedelta(days=1)).filter(Histories.time >= startDate).group_by(Histories.user_id).all()
                    startDate = startDate + timedelta(days=1)
                    if(len(historieTime)):
                        historieTimes.append(historieTime[0][0])
                if len(historieTimes):
                    for historieTime in historieTimes:
                        his_time = historieTime.time()
                        if his_time > address_startTime:
                            avg = avg + (datetime.combine(date.today(), his_time) - datetime.combine(date.today(), address_startTime)).total_seconds()
                    if len(historieTimes):
                        avg = avg/len(historieTimes)
                hours = divmod(avg, 3600)
                minutes = divmod(hours[1], 60)
                total_avg.append(avg)
                rowTable.output_result()["data"][i]['3'] = '%d giờ, %d phút' % (hours[0],minutes[0])
    if len(total_avg):
        total_avg = sum(total_avg) / len(total_avg)
    else: 
        total_avg = 0
    hours = divmod(total_avg, 3600)
    minutes = divmod(hours[1], 60)
    total_avg = '%d giờ, %d phút' % (hours[0],minutes[0])
    for i in range(len(rowTable.output_result()["data"])):
        rowTable.output_result()["data"][i]['4'] = total_avg
    # print(rowTable.output_result())

    return jsonify(rowTable.output_result())

@app.route('/chart_statistical', methods=['GET','POST'])
@login_required
@user_is("admin")
def chart_statistical():
    address_id = request.form['address']
    address_id = int(address_id)
    start =  request.form['start']
    end =  request.form['end']
    data = {} 
    if address_id:
        address = Addresses.query.filter_by(id=address_id).first()
        data[address.name] = statistical_chart_data(address.id, start, end)
    else:
        addresses = Addresses.query.filter_by(company_id=current_user.company_id).all()
        for address in addresses:
            data[address.name] = statistical_chart_data(address.id, start, end)
    return json.dumps(data)

@app.route('/staffTableData')
@login_required
@user_is("admin")
def staffTableData():
    """Return server side data."""
    time = request.args.get('time')
    address_id = request.args.get('address')
    address_id = int(address_id)
    time = datetime.strptime(time,"%Y-%m-%d").date()
    # defining columns
    addr = Addresses.query.filter_by(id=address_id).first()
    columns = [
        ColumnDT(User.id),
        ColumnDT(User.full_name),
        ColumnDT(Addresses.name),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.id),
    ]
    # defining the initial query depending on your purpose
    query = db.session.query().select_from(User).join(Addresses).filter(User.company_id==current_user.company_id).filter(User.address_id==address_id)

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns) 

    # returns what is needed by DataTable
    total_avg = []
    for i in range(len(rowTable.output_result()["data"])):
        avg = 0
        id_ = rowTable.output_result()["data"][i]['3']
        if addr.start:
            address_startTime = addr.start
            startDate = time
            historieTimes = db.session.query(func.min(Histories.time)).filter(Histories.user_id==id_).filter(Histories.time < startDate + timedelta(days=1)).filter(Histories.time >= startDate).group_by(Histories.user_id).all()
            for historieTime in historieTimes:
                his_time = historieTime[0].time()
                if his_time > address_startTime:
                    avg = avg + (datetime.combine(date.today(), his_time) - datetime.combine(date.today(), address_startTime)).total_seconds()
            if len(historieTimes):
                avg = avg/len(historieTimes)
        hours = divmod(avg, 3600)
        minutes = divmod(hours[1], 60)
        total_avg.append(avg)
        rowTable.output_result()["data"][i]['3'] = '%d giờ, %d phút' % (hours[0],minutes[0])
        for j in range(4,11):
            rowTable.output_result()["data"][i][str(j)] = 0

    if len(total_avg):
        total_avg = sum(total_avg) / len(total_avg)
    else: 
        total_avg = 0
    hours = divmod(total_avg, 3600)
    minutes = divmod(hours[1], 60)
    total_avg = '%d giờ, %d phút' % (hours[0],minutes[0])

    if addr.start:
        address_startTime = addr.start
        for i in range(len(rowTable.output_result()["data"])):
            id_ = rowTable.output_result()["data"][i]['0']
            addressStartTime = address_startTime
            tmp = time.strftime("%Y-%m-%d") + " " + addressStartTime.strftime("%H:%M:%S")
            tmp = datetime.strptime(tmp,"%Y-%m-%d %H:%M:%S")
            for j in range(4,11):
                count = (db.session.query(Histories)
                            .filter(Histories.user_id==id_)
                            .filter(Histories.time < tmp + timedelta(minutes=10))
                            .filter(Histories.time >= tmp)
                            .count())
                rowTable.output_result()["data"][i][str(j)] = 1 if count else 0
                tmp = tmp + timedelta(minutes=10)
            rowTable.output_result()["data"][i]['11'] = total_avg
            count = (db.session.query(Histories)
                        .filter(Histories.user_id==id_)
                        .filter(Histories.time < time + timedelta(days=1))
                        .filter(Histories.time >= time)
                        .count())
            rowTable.output_result()["data"][i]['12'] = "Có mặt" if count else "Vắng mặt"

    # print(rowTable.output_result())

    return jsonify(rowTable.output_result())

def statistical_chart_data(address_id, start, end):
    value = {}
    startDatetime = datetime.strptime(start,"%Y-%m-%d").date()
    endDatetime = datetime.strptime(end,"%Y-%m-%d").date()
    addr = Addresses.query.filter_by(id=address_id).first()
    if addr.start:
        while startDatetime != endDatetime + timedelta(days=1):
            minutes = 0
            avg = 0
            address_startTime = addr.start
            camera_list = []
            cameras = Cameras.query.filter_by(company_id=current_user.company_id).filter_by(address_id=addr.id).all()
            for camera in cameras:
                camera_list.append(camera.id)
            historieTimes = db.session.query(func.min(Histories.time)).filter(Histories.camera.in_(camera_list)).filter(Histories.time < startDatetime + timedelta(days=1)).filter(Histories.time >= startDatetime).group_by(Histories.user_id).all()
            for historieTime in historieTimes:
                his_time = historieTime[0].time()
                if his_time > address_startTime:
                    avg = avg + (datetime.combine(date.today(), his_time) - datetime.combine(date.today(), address_startTime)).total_seconds()
            if len(historieTimes):
                avg = avg/len(historieTimes)
            minutes = divmod(avg, 60)
            value[startDatetime.strftime("%Y-%m-%d")]=minutes[0]
            startDatetime = startDatetime + timedelta(days=1)
    
    return value


# ========== Statistics go late =====================
@app.route('/statistics_absent.html')
@login_required
@user_is("admin")
def statistics_absent():
    today = datetime.now().strftime('%Y-%m-%d')
    startTime = request.args.get('startTime') or today
    endTime = request.args.get('endTime') or today
    time = {"startTime": startTime, "endTime":endTime}
    address = request.args.get('address') or 0
    addressesData = []
    addresses = Addresses.query.filter_by(company_id=current_user.company_id).all()
    for addr in addresses:
        addressesData.append(addr.name)
    return render_template( 'pages/statistics_absent.html', addresses=addresses, time=time, address=address, addressesData=addressesData)

@app.route('/chart_statistical_absent', methods=['GET','POST'])
@login_required
@user_is("admin")
def chart_statistical_absent():
    address_id = request.form['address']
    address_id = int(address_id)
    start =  request.form['start']
    end =  request.form['end']
    data = {} 
    if address_id:
        address = Addresses.query.filter_by(id=address_id).first()
        data[address.name] = statistical_absent_chart_data(address.id, start, end)
    else:
        addresses = Addresses.query.filter_by(company_id=current_user.company_id).all()
        for address in addresses:
            data[address.name] = statistical_absent_chart_data(address.id, start, end)
    return json.dumps(data)

def statistical_absent_chart_data(address_id, start, end):
    value = {}
    absentEvent = Events.query.filter_by(name="Vắng mặt").first()
    startDatetime = datetime.strptime(start,"%Y-%m-%d").date()
    endDatetime = datetime.strptime(end,"%Y-%m-%d").date()
    while startDatetime != endDatetime + timedelta(days=1):
        eventLogsTime = (db.session.query(EventLogs)
                            .filter(EventLogs.address_id==int(address_id))
                            .filter(EventLogs.event_id==absentEvent.id)
                            .filter(EventLogs.time < startDatetime + timedelta(days=1))
                            .filter(EventLogs.time >= startDatetime)
                            .count())
        startDatetime = startDatetime + timedelta(days=1)
        if start == end:
            userNum = User.query.filter_by(address_id=int(address_id)).count()
            if userNum:
                value[startDatetime.strftime("%Y-%m-%d")]="{:.2f}".format(eventLogsTime/userNum)
            else:
                value[startDatetime.strftime("%Y-%m-%d")]=eventLogsTime
        else:
            value[startDatetime.strftime("%Y-%m-%d")]=eventLogsTime
    
    return value


@app.route('/statistical_absent_data')
@login_required
@user_is("admin")
def statistical_absent_data():
    """Return server side data."""
    startTime = request.args.get('startTime')
    endTime = request.args.get('endTime')
    address_id = request.args.get('address')
    address_id = int(address_id)
    startDatetime = datetime.strptime(startTime,"%Y-%m-%d").date()
    endDatetime = datetime.strptime(endTime,"%Y-%m-%d").date() + timedelta(days=1)
    # defining columns
    # defining the initial query depending on your purpose
    if int(address_id) == 0:
        columns = [
            ColumnDT(Addresses.id),
            ColumnDT(Addresses.name),
            ColumnDT(Addresses.address),
            ColumnDT(Addresses.id),
            ColumnDT(Addresses.id),
        ]
        query = db.session.query().select_from(Addresses).filter(Addresses.company_id==current_user.company_id)
    else:
        addr = Addresses.query.filter_by(id=address_id).first()
        columns = [
            ColumnDT(User.id),
            ColumnDT(User.full_name),
            ColumnDT(Addresses.address),
            ColumnDT(User.id),
            ColumnDT(User.id),
        ]
        query = db.session.query().select_from(User).join(Addresses).filter(User.company_id==current_user.company_id).filter(User.address_id==address_id)

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    absentEvent = Events.query.filter_by(name="Vắng mặt").first()
    total_avg = []
    for i in range(len(rowTable.output_result()["data"])):
        avg = 0
        id_ = rowTable.output_result()["data"][i]['0'] # user_id if address_id is not None else is address id
        if int(address_id):
            eventLogsTimes = []
            startDate = startDatetime
            endDate   = endDatetime
            while startDate != endDate:
                eventLogsTime = db.session.query(EventLogs).filter(EventLogs.address_id==int(address_id)).filter(EventLogs.user_id==id_).filter(EventLogs.event_id==absentEvent.id).filter(EventLogs.time < startDate + timedelta(days=1)).filter(EventLogs.time >= startDate).count()
                startDate = startDate + timedelta(days=1)
                if eventLogsTime:
                    eventLogsTimes.append(eventLogsTime)
            # print(id_, eventLogsTimes)
            if len(eventLogsTimes):
                avg = sum(eventLogsTimes) / len(eventLogsTimes)
            total_avg.append(avg)
            rowTable.output_result()["data"][i]['3'] = "{:.2f}".format(avg)
        else:
            addr = Addresses.query.filter_by(id=id_).first()
            eventLogsTimes = []
            startDate = startDatetime
            endDate   = endDatetime
            while startDate != endDate:
                eventLogsTime = db.session.query(EventLogs).filter(EventLogs.address_id==addr.id).filter(EventLogs.event_id==absentEvent.id).filter(EventLogs.time < startDate + timedelta(days=1)).filter(EventLogs.time >= startDate).count()
                startDate = startDate + timedelta(days=1)
                # if eventLogsTime:
                #     eventLogsTimes.append(eventLogsTime)
                eventLogsTimes.append(eventLogsTime)
            # print(addr.name, eventLogsTimes)
            if len(eventLogsTimes):
                avg = sum(eventLogsTimes) / len(eventLogsTimes)
            total_avg.append(avg)
            rowTable.output_result()["data"][i]['3'] = "{:.2f}".format(avg)


    if len(total_avg):
        total_avg = sum(total_avg) / len(total_avg)
    else: 
        total_avg = 0
    for i in range(len(rowTable.output_result()["data"])):
        rowTable.output_result()["data"][i]['4'] = "{:.2f}".format(total_avg)
    # print(rowTable.output_result())

    return jsonify(rowTable.output_result())