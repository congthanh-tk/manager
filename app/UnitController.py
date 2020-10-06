# import Base Controller
from BaseController import *

@app.route('/add_unit', methods=['POST'])
@login_required
@user_is("superuser")
def add_unit():
    output = json.dumps({"success": True})
    name = request.form['name']
    description = request.form['description']
    unit = Units.query.filter_by(name=name).first()
    if not unit:
        unit_ = Units(name=name,description=description)
        db.session.add(unit_)
        db.session.commit()

        if unit_.id:
            return success_handle(output)
        else:
            print("An error saving unit.")
            return error_handle("An error saving unit.")
    else:
        return error_handle("Name unit used.")

@app.route('/edit_unit', methods=['POST'])
@login_required
@user_is("superuser")
def edit_unit():
    output = json.dumps({"success": True})
    
    unit_id =  request.form['editID']
    name =  request.form['editName']
    description = request.form['editDescription']

    if unit_id:
        unit = Units.query.filter_by(id=unit_id)
        if unit:
            db.session.query(Units).filter_by(id=unit_id).update({"name": name, "description": description}, synchronize_session='fetch')
            db.session.commit()
            return success_handle(output)
        else:
            print("An error edit unit.")
            return error_handle("An error edit unit.")
    else:
        return error_handle("Event Id is empty.")
    
@app.route('/unit_data')
@login_required
@user_is("superuser")
def unit_data():
    """Return server side data."""
    # defining columns
    columns = [
        ColumnDT(Units.id),
        ColumnDT(Units.name),
        ColumnDT(Units.description)
    ]

    query = db.session.query().select_from(Units)

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    return jsonify(rowTable.output_result())

@app.route('/del_unit', methods=['POST'])
@login_required
@user_is("superuser")
def del_unit():
    output = json.dumps({"success": True})
    unit_id =  request.form['id']

    ret = Units.query.filter_by(id=unit_id).delete()
    if ret:
        db.session.commit()
        return success_handle(output)
    else:
        return error_handle("An error delete unit.")