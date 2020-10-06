# import Base Controller
from BaseController import *

@app.route('/staff_management.html')
@login_required
@user_is("admin")
def staff_management():
    addresses = []
    data = db.session.query(Addresses).filter(Addresses.company_id == current_user.company_id)
    for address in data:
        addresses.append({'id': address.id, 'address': address.name})
    return render_template( 'pages/staff_management.html', addresses=addresses)

@app.route('/staff_data')
@login_required
@user_is("admin")
def staff_data():
    """Return server side data."""
    cameras = db.session.query(Cameras).filter(Cameras.company_id == current_user.company_id)
    cameraIds = []
    for camera in cameras:
        cameraIds.append(camera.id)
    # defining columns
    columns = [
        ColumnDT(User.id),
        ColumnDT(User.id),
        ColumnDT(User.full_name),
        ColumnDT(User.birthday),
        ColumnDT(User.code),
        ColumnDT(User.guest_company),
        ColumnDT(Faces.file_name),
        ColumnDT(User.id),
        ColumnDT(User.permissions),
    ]

    query = (db.session.query().select_from(User).outerjoin(Faces)
             .join(User.roles)
             .filter(User.company_id == current_user.company_id)
             .filter(Role.name == "staff")
             .group_by(Faces.user_id))

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    return jsonify(rowTable.output_result())