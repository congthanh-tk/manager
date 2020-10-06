# import Base Controller
from BaseController import *

@app.route('/version_data')
@login_required
@user_is("superuser")
def version_data():
    """Return server side data."""
    # defining columns
    columns = [
        ColumnDT(Versions.id),
        ColumnDT(Versions.name),
        ColumnDT(Versions.file),
        ColumnDT(func.strftime("%Y-%m-%d %H:%M:%S", Versions.confirmed_at))
    ]
 
    # defining the initial query depending on your purpose
    query = db.session.query().select_from(Versions)

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    #print(rowTable.output_result())

    return jsonify(rowTable.output_result())

@app.route('/del_version', methods=['POST'])
@login_required
@user_is("superuser")
def del_version():
    output = json.dumps({"success": True})
    version_id =  request.form['id']

    ret = Versions.query.filter_by(id=version_id).delete()
    if ret:
        db.session.commit()
        return success_handle(output)
    else:
        return error_handle("An error delete camera.")

@app.route('/manager_version_camera.html')
@login_required
@user_is("superuser")
def manager_version_camera():
    return render_template( 'pages/manager_version_camera.html')

@app.route('/add_version', methods=['POST'])
@login_required
@user_is("superuser")
def add_version():
    output = json.dumps({"success": True})
    filename = request.form['name']
    file_path = ""
    if filename:
        file = request.files['inputFile']
        if file and allowed_file(file.filename):
            urlSafeEncodedStr =file.filename
            file_path = path.join(version_path, urlSafeEncodedStr);
            file.save(path.join(basedir, file_path))
            version = Versions(name=filename, file=file_path)
            db.session.add(version)
            db.session.commit()
            if version:
                return redirect("manager_version_camera.html")
            else:
                print("An error saving version.")
                return error_handle("An error saving version.")
        else:
            return error_handle("File not allowed.")
    else:
        return error_handle("file is empty.")