# import Base Controller
from BaseController import *

@app.route('/managercamera.html')
@login_required
@user_is("superuser")
def managercamera():
    companies = db.session.query(Companies).all()
    return render_template( 'pages/managercamera.html', companies=companies)

@app.route('/manager-camera-company.html')
@login_required
@user_is("admin")
def company_managercamera():
    addresses = db.session.query(Addresses).filter(Addresses.company_id == current_user.company_id).all()
    return render_template( 'pages/manager-camera-company.html', addresses=addresses)


@app.route('/company_cameras_data')
@login_required
@user_is("admin")
def company_cameras_data():
    """Return server side data."""
    # defining columns
    columns = [
        ColumnDT(Cameras.id),
        ColumnDT(Cameras.udid),
        ColumnDT(Cameras.name),
        ColumnDT(Addresses.name),
        ColumnDT(Cameras.ipaddr),
        ColumnDT(func.strftime("%Y-%m-%d %H:%M:%S", Cameras.time)),
        ColumnDT(Cameras.type),
        ColumnDT(Cameras.link_stream)
    ]

    if (current_user.has_roles("superuser")):
        query = db.session.query().select_from(Cameras).outerjoin(Addresses).filter()
    else:
        query = db.session.query().select_from(Cameras).outerjoin(Addresses).filter(Cameras.company_id == current_user.company_id)

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    
    # print(rowTable.output_result())
    return jsonify(rowTable.output_result())

@app.route('/cameras_data')
@login_required
@user_is("superuser")
def cameras_data():
    """Return server side data."""
    # defining columns

    columns = [
        ColumnDT(Cameras.id),
        ColumnDT(Cameras.udid),
        ColumnDT(Companies.name),
        ColumnDT(Cameras.ipaddr),
        ColumnDT(func.strftime("%Y-%m-%d %H:%M:%S", Cameras.time)),
        ColumnDT(Cameras.version),
        ColumnDT(Cameras.version)
    ]

    # defining the initial query depending on your purpose
    query = db.session.query().select_from(Cameras).outerjoin(Companies).filter()

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    for i in range(len(rowTable.output_result()["data"])):
        max = db.session.query(func.max(Versions.id)).first()
        for max_ in max:
            if (rowTable.output_result()["data"][i]['6']):
                if (max_):
                    rowTable.output_result()["data"][i]['6'] = int(rowTable.output_result()["data"][i]['6']) < int(max_)
                else:
                    rowTable.output_result()["data"][i]['6'] = False
            else:
                rowTable.output_result()["data"][i]['5'] = 0
                rowTable.output_result()["data"][i]['6'] = False

    return jsonify(rowTable.output_result())

@app.route('/add_cam', methods=['POST'])
@login_required
@user_is("superuser")
def add_cam():
    output = json.dumps({"success": True})
    cam_udid =  request.form['cam_udid']
    company_id =  request.form['company']

    if company_id:
        cam = Cameras(udid= cam_udid, company_id=company_id)
        db.session.add(cam)
        db.session.commit()
        if cam:
            return success_handle(output)
        else:
            print("An error saving camera.")
            return error_handle("An error saving camera.")
    else:
        return error_handle("company_id is empty.")


@app.route('/update_firmware', methods=['POST'])
@login_required
@user_is("superuser")
def update_firmware():
    output = json.dumps({"success": True})
    cam_id =  request.form['id']
    cam = Cameras.query.filter_by(id=cam_id).first()
    if cam:
        version = Versions.query.order_by(Versions.id.desc()).first()
        if version:
            room = session.get(str(cam.company_id))
            data = {}
            data['file'] = version.file
            data['id'] = version.id
            data['camera_id'] = cam.udid
            socketio.emit('update_firmware', { 'data' :  json.dumps(data) }, namespace='/camera', room=room )

        return success_handle(output)
    else:
        return error_handle("cam is not found.")

@app.route('/del_cam', methods=['POST'])
@login_required
@user_is("superuser")
def del_cam():
    output = json.dumps({"success": True})
    cam_id =  request.form['id']

    ret = Cameras.query.filter_by(id=cam_id).delete()
    if ret:
        db.session.commit()
        return success_handle(output)
    else:
        return error_handle("An error delete camera.")

@app.route('/edit_cam', methods=['POST'])
@login_required
@user_is("superuser")
def edit_cam():
    output = json.dumps({"success": True})
    #print(request.form['name'])
    cam_udid =  request.form['editCameraUdid']
    cam_id =  request.form['editID']
    company_id =  request.form['editCompany']

    if cam_id:
        cam = Cameras.query.filter_by(id=cam_id)
        if cam:
            db.session.query(Cameras).filter_by(id=cam_id).update({"udid": cam_udid, "company_id": company_id}, synchronize_session='fetch')
            db.session.commit()
            room = session.get(str(company_id))
            data = {}
            socketio.emit('restart', { 'data' :  json.dumps(data) }, namespace='/camera', room=room )
            return success_handle(output)
        else:
            print("An error edit camera.")
            return error_handle("An error edit camera.")
    else:
        return error_handle("Name is empty.")

@app.route('/edit_ccam', methods=['POST'])
@login_required
@user_is("admin")
def edit_ccam():
    output = json.dumps({"success": True})
    #print(request.form['name'])    
    cam_id =  request.form['editID']
    address_id =  request.form['editAddress']
    cam_name =  request.form['editName']
    type_cam = request.form['editType']
    link_stream = request.form['editLink']
    if cam_id:
        cam = Cameras.query.filter_by(id=cam_id).first()

        if cam:
            if not is_same_company(cam.company_id):
                return error_handle("An error edit camera.")
            db.session.query(Cameras).filter_by(id=cam_id).update({"address_id": address_id, "name": cam_name, "type": type_cam, "link_stream": link_stream }, synchronize_session='fetch')
            db.session.commit()
            return success_handle(output)
        else:
            print("An error edit camera.")
            return error_handle("An error edit camera.")
    else:
        return error_handle("Name is empty.")

@app.route('/toado.html')
@login_required
@user_is("admin")
def toado():
    data = {}
    cameras = []
    if (current_user.has_roles("admin")):
        cameras = db.session.query(Cameras, Addresses).join(Addresses).filter(Cameras.company_id == current_user.company_id).all()
    elif current_user.has_roles("superuser"):
        cameras = db.session.query(Cameras, Addresses).join(Addresses).all()
    for camera in cameras:
        cam = (camera[1].to_dict())
        str2hash = str(cam['latitude']) + str(cam['longitude'])
        result = hashlib.md5(str2hash.encode())
        key = result.hexdigest()
        if key in data.keys():
            data[key].append(cam)
        else:
            data[key] = []
            data[key].append(cam)

    return render_template( 'pages/toado.html', data=data)
