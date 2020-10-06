# import Base Controller
from BaseController import *

@app.route('/managercompany.html')
@login_required
@user_is("superuser")
def managercompany():
    plans = db.session.query(Plans).all()
    return render_template( 'pages/managercompany.html', plans=plans)


@app.route('/companies_data')
@login_required
@user_is("superuser")
def companies_data():
    """Return server side data."""
    # defining columns

    columns = [
        ColumnDT(Companies.id),
        ColumnDT(Companies.name),
        ColumnDT(Plans.name),
        ColumnDT(Companies.email),
        ColumnDT(Companies.phone),
        ColumnDT(Companies.address),
        ColumnDT(Companies.secret)
    ]

    # defining the initial query depending on your purpose
    query = db.session.query().select_from(Companies).outerjoin(Plans).filter()

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    # print(rowTable.output_result())
    return jsonify(rowTable.output_result())


@app.route('/add_company', methods=['POST'])
@login_required
@user_is("superuser")
def add_company():
    output = json.dumps({"success": True})
    addName =  request.form['addName']
    addEmail =  request.form['addEmail']
    addPhone =  request.form['addPhone']
    addPlan =  request.form['addPlan']
    addAddress =  request.form['addAddress']
    file = None
    file_image_path = ""

    if addName:
        if 'file' in request.files:
            file = request.files['file']

        if file:
            if file.mimetype not in ['image/png', 'image/jpeg', 'application/octet-stream']:
                print("File extension is not allowed")
                return error_handle("We are only allow upload file with *.png , *.jpg")
            else:
                name = str(int(time.time())) + secure_filename(file.filename)
                urlSafeEncodedBytes = base64.urlsafe_b64encode(name.encode("utf-8"))[:20]
                urlSafeEncodedStr = str(urlSafeEncodedBytes) + ".jpg"

                file_image_path = path.join(company_image_path, urlSafeEncodedStr);
                file.save(path.join(basedir, file_image_path))
        company = Companies(name= addName, email=addEmail, phone=addPhone, address=addAddress, plan_id = addPlan, logo_image = file_image_path, secret = randomString(20))
        db.session.add(company)
        db.session.commit()
        if company:
            company_face_dir = path.join(basedir, path.join(face_image_path + "/" + str(company.id)))
            company_event_dir = path.join(basedir, path.join(event_image_path + "/" + str(company.id)))
            if not os.path.isdir(company_face_dir):
                os.mkdir(company_face_dir)

            if not os.path.isdir(company_event_dir):
                os.mkdir(company_event_dir)

            return success_handle(output)
        else:
            print("An error saving company.")
            return error_handle("An error saving company.")
    else:
        return error_handle("company name is empty.")

@app.route('/del_company', methods=['POST'])
@login_required
@user_is("superuser")
def del_company():
    output = json.dumps({"success": True})
    company_id =  request.form['id']

    ret = Companies.query.filter_by(id=company_id).delete()
    if ret:
        db.session.commit()
        return success_handle(output)
    else:
        return error_handle("An error delete camera.")

@app.route('/detail-company.html')
@login_required
@user_is("superuser")
def detailcompany():
    plans = db.session.query(Plans).all()
    company_id = request.args.get('id')
    company = db.session.query(Companies).filter(Companies.id == company_id).outerjoin(Plans).first()
    if company:
        return render_template( 'pages/detail-company.html', company=company, plans = plans)
    else:
        return redirect(url_for('managercamera',_external=True,_scheme=request.scheme))


@app.route('/edit_company', methods=['POST'])
@login_required
@user_is("superuser")
def edit_company():
    output = json.dumps({"success": True})
    company_id =  request.form['id']
    name =  request.form['name']
    email =  request.form['email']
    phone =  request.form['phone']
    plan =  request.form['plan']
    address =  request.form['address']
    secret =  request.form['secret']
    file = None
    file_image_path = ""
    if company_id:
        if 'file' in request.files:
            file = request.files['file']

        if file:
            if file.mimetype not in ['image/png', 'image/jpeg', 'application/octet-stream']:
                print("File extension is not allowed")
                return error_handle("We are only allow upload file with *.png , *.jpg")
            else:
                filename = str(int(time.time())) + secure_filename(file.filename)
                urlSafeEncodedBytes = base64.urlsafe_b64encode(name.encode("utf-8"))[:20]
                urlSafeEncodedStr = str(urlSafeEncodedBytes) + ".jpg"

                file_image_path = path.join(company_image_path, urlSafeEncodedStr);
                file.save(path.join(basedir, file_image_path))
        company = Companies.query.filter_by(id=company_id)
        if company:
            if file_image_path:
                db.session.query(Companies).filter_by(id=company_id).update({"name": name, "email": email, "phone": phone, "plan_id": plan, "secret": secret, "address": address, "logo_image": file_image_path}, synchronize_session='fetch')
            else:
                db.session.query(Companies).filter_by(id=company_id).update({"name": name, "email": email, "phone": phone, "plan_id": plan, "secret": secret, "address": address}, synchronize_session='fetch')
            db.session.commit()

            company_face_dir = path.join(basedir, path.join(face_image_path + "/" + str(company_id)))
            if not os.path.isdir(company_face_dir):
                os.mkdir(company_face_dir)

            return success_handle(output)
        else:
            print("An error edit company.")
            return error_handle("An error edit company.")
    else:
        return error_handle("company id is empty.")