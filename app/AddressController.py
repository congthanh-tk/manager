# import Base Controller
from BaseController import *

@app.route('/address_data')
@login_required
@user_is("admin")
def address_data():
    """Return server side data."""
    # defining columns
    columns = [
        ColumnDT(Addresses.id),
        ColumnDT(Addresses.name),
        ColumnDT(Addresses.address),
        ColumnDT(Addresses.start),
        ColumnDT(Addresses.end),
        ColumnDT(Addresses.latitude),
        ColumnDT(Addresses.longitude),
    ]
 
    # defining the initial query depending on your purpose
    query = db.session.query().select_from(Addresses).filter(Addresses.company_id == current_user.company_id)

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    for i in range(len(rowTable.output_result()["data"])):
        if rowTable.output_result()["data"][i]['3']:
            rowTable.output_result()["data"][i]['3'] = rowTable.output_result()["data"][i]['3'].strftime("%I:%M %p")
        if rowTable.output_result()["data"][i]['4']:
            rowTable.output_result()["data"][i]['4'] = rowTable.output_result()["data"][i]['4'].strftime("%I:%M %p")

    #print(rowTable.output_result())

    return jsonify(rowTable.output_result())

@app.route('/edit_address', methods=['POST'])
@login_required
@user_is("admin")
def edit_address():
    output = json.dumps({"success": True})
    #print(request.form['name'])
    address_id =  request.form['editID']
    name =  request.form['editName']
    address =  request.form['editAddress']
    start =  request.form['editStart']
    end =  request.form['editEnd']
    latitude = request.form['latEdit']
    longitude = request.form['lngEdit']
    if address_id and name and address:
        address_ = Addresses.query.filter_by(id=address_id).first()

        if address_:
            if not is_same_company(address_.company_id):
                return error_handle("An error edit address.")

            db.session.query(Addresses).filter_by(id=address_id).update({"name": name, "address": address, "latitude": latitude, "longitude": longitude }, synchronize_session='fetch')
            db.session.commit()

            if (start):
                start_time = datetime.strptime(start,"%I:%M %p").time()
                db.session.query(Addresses).filter_by(id=address_id).update({"start": start_time}, synchronize_session='fetch')
            if (end):
                end_time = datetime.strptime(end,"%I:%M %p").time()
                db.session.query(Addresses).filter_by(id=address_id).update({"end": end_time}, synchronize_session='fetch')
            db.session.commit()

            return success_handle(output)
        else:
            print("An error edit address.")
            return error_handle("An error edit address.")
    else:
        return error_handle("Name is empty.")

@app.route('/add_address', methods=['POST'])
@login_required
@user_is("admin")
def add_address():
    output = json.dumps({"success": True})
    #print(request.form['name'])
    name =  request.form['name']
    address =  request.form['address']
    start =  request.form['start']
    end =  request.form['end']
    lat = request.form['lat']
    lng = request.form['lng']

    if name or address:
        address_ = Addresses(name=name, address=address, company_id=current_user.company_id, latitude=lat, longitude=lng)
        db.session.add(address_)
        db.session.commit()
        if address_:
            if (start):
                start_time = datetime.strptime(start,"%I:%M %p").time()
                db.session.query(Addresses).filter_by(id=address_.id).update({"start": start_time}, synchronize_session='fetch')
            if (end):
                end_time = datetime.strptime(end,"%I:%M %p").time()
                db.session.query(Addresses).filter_by(id=address_.id).update({"end": end_time}, synchronize_session='fetch')
            db.session.commit()
            return success_handle(output)
        else:
            print("An error saving address.")
            return error_handle("An error saving address.")
    else:
        return error_handle("Name or address is empty.")
    
@app.route('/del_address', methods=['POST'])
@login_required
@user_is("admin")
def del_address():
    output = json.dumps({"success": True})
    address_id =  request.form['id']
    address = Addresses.query.filter_by(id=address_id).first()
   
    if address:  
        if not is_same_company(address.company_id):
            return error_handle("An error delete address.")
        Addresses.query.filter_by(id=address_id).delete()
        db.session.commit()
        return success_handle(output)
    else:
        return error_handle("An error delete address.")