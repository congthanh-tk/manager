# import Base Controller
from BaseController import *

@app.route('/add_event', methods=['POST'])
@login_required
@user_is("superuser")
def add_event():
    output = json.dumps({"success": True})
    name = request.form['name']
    description = request.form['description']
    event = Events.query.filter_by(name=name).first()
    if not event:
        event_ = Events(name=name,description=description)
        db.session.add(event_)
        db.session.commit()

        if event_.id:
            return success_handle(output)
        else:
            print("An error saving event.")
            return error_handle("An error saving event.")
    else:
        return error_handle("Name event used.")

@app.route('/edit_event', methods=['POST'])
@login_required
@user_is("superuser")
def edit_event():
    output = json.dumps({"success": True})
    
    event_id =  request.form['editID']
    name =  request.form['editName']
    description = request.form['editDescription']

    if event_id:
        event = Events.query.filter_by(id=event_id)
        if event:
            db.session.query(Events).filter_by(id=event_id).update({"name": name, "description": description}, synchronize_session='fetch')
            db.session.commit()
            return success_handle(output)
        else:
            print("An error edit event.")
            return error_handle("An error edit event.")
    else:
        return error_handle("Event Id is empty.")
    
@app.route('/event_data')
@login_required
@user_is("superuser")
def event_data():
    """Return server side data."""
    # defining columns
    columns = [
        ColumnDT(Events.id),
        ColumnDT(Events.name),
        ColumnDT(Events.description)
    ]

    query = db.session.query().select_from(Events)

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    return jsonify(rowTable.output_result())

@app.route('/del_event', methods=['POST'])
@login_required
@user_is("superuser")
def del_event():
    output = json.dumps({"success": True})
    event_id =  request.form['id']

    ret = Events.query.filter_by(id=event_id).delete()
    if ret:
        db.session.commit()
        return success_handle(output)
    else:
        return error_handle("An error delete event.")

@app.route('/event_logs_data')
@login_required
@user_is("admin")
def event_logs_data():
    """Return server side data."""
    columns = [
        ColumnDT(EventLogs.id),
        ColumnDT(User.full_name),
        ColumnDT(Addresses.name),
        ColumnDT(Events.name),
        ColumnDT(EventLogs.time),
        ColumnDT(EventLogs.image),
        ColumnDT(EventLogs.data),
        ColumnDT(User.id),
        ColumnDT(Cameras.ipaddr),
        ColumnDT(EventLogs.event_id),
        ColumnDT(Cameras.udid),
    ]
    
    query = db.session.query().select_from(EventLogs).outerjoin(User).join(Events).join(Cameras).filter(Cameras.company_id == current_user.company_id).join(Addresses, Cameras.address_id==Addresses.id).order_by(EventLogs.time.desc())

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    print(rowTable.output_result())
    return jsonify(rowTable.output_result())