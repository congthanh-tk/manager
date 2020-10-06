# import Base Controller
from BaseController import *

@app.route('/role_data')
@login_required
@user_is("superuser")
def role_data():
    """Return server side data."""
    # defining columns
    columns = [
        ColumnDT(Role.id),
        ColumnDT(Role.name),
    ]

    # defining the initial query depending on your purpose
    query = db.session.query().select_from(Role).filter()

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    # print(rowTable.output_result())
    return jsonify(rowTable.output_result())

@app.route('/edit_roles', methods=['POST'])
@login_required
@user_is("superuser")
def edit_roles():
    output = json.dumps({"success": True})
    #print(request.form['name'])
    name =  request.form['name']
    role_id =  request.form['id']

    if name and id:
        role = Role.query.filter_by(id=role_id)
        if role:
            db.session.query(Role).filter_by(id=role_id).update({"name": name}, synchronize_session='fetch')
            db.session.commit()
            return success_handle(output)
        else:
            print("An error edit role.")
            return error_handle("An error edit role.")
    else:
        return error_handle("Name is empty.")

@app.route('/add_roles', methods=['POST'])
@login_required
@user_is("superuser")
def add_roles():
    output = json.dumps({"success": True})
    #print(request.form['name'])
    name =  request.form['name']

    if name:
        role = Role(name=name)
        db.session.add(role)
        db.session.commit()
        if role:
            return success_handle(output)
        else:
            print("An error saving role.")
            return error_handle("An error saving role.")
    else:
        return error_handle("Name is empty.")
    
@app.route('/del_roles', methods=['POST'])
@login_required
@user_is("superuser")
def del_roles():
    output = json.dumps({"success": True})
    role_id =  request.form['id']

    ret = Role.query.filter_by(id=role_id).delete()
    if ret:
        db.session.commit()
        return success_handle(output)
    else:
        return error_handle("An error delete role.")