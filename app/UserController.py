# import Base Controller
from BaseController import *

@app.route('/del_face', methods=['POST'])
@login_required
@user_is("admin")
def del_face():
    output = json.dumps({"success": True})
    face_id =  request.form['id']
    
    if face_id:
        face_array = face_id.split(",")
        db_path = feature_db_path + str(current_user.company_id) + ".db"
        if not os.path.isfile(db_path):
            db_o_path = feature_db_path + "mq_feature_empty.db"
            shutil.copy2(db_o_path, db_path)

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        for id_ in face_array:
            face = Faces.query.filter_by(id=id_).first()

            user = db.session.query(User).filter(User.id == face.user_id).first() 

            if not is_same_company(user.company_id):
                return error_handle("No permission to delete face.")

            if face:
                file_name = face.file_name.replace(face_image_path, "")
                file_name = file_name.replace("/" + str(current_user.company_id), "")
                file_name = file_name.replace("/", "")
                file_name = file_name.replace(".jpg", "")
                print(file_name)

                try:
                    sql_Delete_query = """DELETE FROM Features WHERE Features.name = '{0}'""".format(file_name)
                    c.execute(sql_Delete_query)
                    Faces.query.filter_by(id=id_).delete()
                except sqlite3.IntegrityError as e:
                    print('Remove feature errror: ', e.args[0]) # column name is not unique
                except Exception as e:
                    conn.rollback()
                    conn.close()
                    db.session.rollback()
                    return error_handle("An error delete face.")

                #TODO: send socket to camera to remove
                room = session.get(str(user.company_id))
                data = {}
                data['name'] = file_name

                socketio.emit('feature_del', { 'data' :  json.dumps(data) }, namespace='/camera', room=room )
                
            else:
                return error_handle("An error delete face.")

        conn.commit()
        conn.close()

        db.session.commit()
        return success_handle(output)

    return error_handle("An error delete face.")

@app.route('/profile.html')
@login_required
def profile():
    companies = []
    roles = db.session.query(Role).all()
    refined_roles = []
    
    if (current_user.has_roles("admin")):
        for role in roles:
            if role.name != "superuser":
                refined_roles.append(role)
        companies = db.session.query(Companies).filter(Companies.id == current_user.company_id).all()
    elif (current_user.has_roles("superuser")):
        refined_roles = roles
        companies = db.session.query(Companies).all()

    user_id = request.args.get('id')
    if not user_id:
        user_id = current_user.id
    user = db.session.query(User).filter(User.id == user_id).outerjoin(Companies).first()
    data = db.session.query(User).filter(User.id == user_id).first()
    
    if user:
        permissionsUser = None
        if user.permissions :
            permissionsUser = eval(user.permissions)
        if (not current_user.has_roles("superuser") and user.company_id != current_user.company_id):
            return render_template( 'pages/permission_denied.html')

        if (current_user.has_roles("staff") or current_user.has_roles("user")):
            if (user.id != current_user.id):
                return render_template( 'pages/permission_denied.html')

        faces = db.session.query(Faces).filter(Faces.user_id == user_id).all()
        gender = -1
        age = -1
        if (len(faces) > 0):
            img = cv2.imread(os.path.join(basedir, faces[0].file_name), cv2.IMREAD_COLOR)
            if img is not None:
                nimg1 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                nimg1 = np.transpose(nimg1, (2,0,1))
                ga_model = get_model(ctx, image_size, ga_model_path, 'fc1')
                gender, age = get_ga(ga_model, nimg1)
        absent = Events.query.filter_by(name="Vắng mặt").first()
        count_absent = EventLogs.query.filter_by(user_id=user_id).filter_by(event_id=absent.id).count()
        units = db.session.query(Units).all()
        addresses = Addresses.query.filter_by(company_id=current_user.company_id).all()
        return render_template( 'pages/profile.html', user=user, companies = companies, roles=refined_roles, faces = faces, gender = gender, age = age, data=data.to_dict(), permissionsUser=permissionsUser, count_absent=count_absent, units=units, addresses=addresses)
        
    else:
        return render_template( 'pages/error-404.html')


@app.route('/profile_log_time')
@login_required
def profile_log_time():
    output = json.dumps({"success": True})

    user_id = request.args.get('id')
    if not user_id:
        user_id = current_user.id
    user = db.session.query(User).filter(User.id == user_id).first()
    if user:

        columns = [
            ColumnDT(Histories.id),
            ColumnDT(Histories.image),
            ColumnDT(func.strftime("%Y-%m-%d %H:%M:%S", Histories.time)),
            ColumnDT(Cameras.name),
            ColumnDT(Addresses.name),
            ColumnDT(Histories.licensed),
            ColumnDT(Cameras.ipaddr),
        ]
        query = (db.session.query().select_from(Histories)
                 .join(Cameras).outerjoin(Addresses)
                 .filter(Histories.user_id == user_id)
                 .group_by(Histories.id)
                 .order_by(Histories.time.desc()) )

        # GET parameters
        params = request.args.to_dict()

        # instantiating a DataTable for the query and table needed
        rowTable = DataTables(params, query, columns)

        # returns what is needed by DataTable
        return jsonify(rowTable.output_result())

        
    else:
        return error_handle("user is not existed.")

@app.route('/search_user', methods=['POST'])
@login_required
@user_is("admin")
def search_user():
    searchword =  request.form['searchword']
    search = "%{}%".format(searchword.upper())
    users = db.session.query(User, Faces).outerjoin(Faces).filter(func.upper(User.full_name).ilike(func.upper(search)) | func.upper(User.user).ilike(func.upper(search))).filter(User.is_unknown == False).filter(User.company_id == current_user.company_id).group_by(User.id).all()
    return render_template('pages/user_list.html', users=users)


@app.route('/confirm_user', methods=['POST'])
@login_required
@user_is("admin")
def confirm_user():
    output = json.dumps({"success": True})
    user_id =  request.form['id']

    user = db.session.query(User).filter(User.id == user_id).first()
    if user:
        selectedIds =  request.form['selectedIds']
        selectedHIds =  request.form['selectedHIds']
        ids = [int(n) for n in str(selectedIds).split(',')]
        hids = [int(n) for n in str(selectedHIds).split(',')]
        pprint(ids)
        pprint(hids)

        db.session.query(Histories).filter(Histories.id.in_(hids)).update({"user_id": user.id}, synchronize_session='fetch')  
        faces = db.session.query(Faces.id).join(User, Faces.user_id == User.id).filter(Faces.user_id.in_(ids)).filter(User.is_unknown == True).all()
        
        
        result_list = [row[0] for row in faces]
        print(result_list)
        db.session.query(Faces).filter(Faces.id.in_(result_list)).update({"user_id": user.id}, synchronize_session='fetch')

        db.session.query(User).filter(User.id.in_(ids)).filter(User.is_unknown == True).delete(synchronize_session='fetch')

        db.session.commit()
        return success_handle(output)

    else:
        return error_handle("user is not existed.")

@app.route('/reset_password', methods=['POST'])
@login_required
@user_is("admin")
def reset_password():
    output = json.dumps({"success": True})
    user_id =  request.form['id']

    if user_id:
        user_ = User.query.filter_by(id=user_id).first()
        
        if user_:
            if not is_same_company(user_.company_id):
                return error_handle("An error reset password.")
            newpassword = randomString()
            body = "Cảm ơn đã sử dụng dịch vụ của chúng tôi. Mật khẩu mới của bạn là " + newpassword;
            msg = Message(subject="[MQ CRM] Tạo lại mật khẩu",
              sender="crm@mqsolutions.vn",
              recipients=[user_.email], # replace with your email for testing
              body=body)
            ret = mail.send(msg)

            if not ret:
                db.session.query(User).filter_by(id=user_id).update({"password": bc.generate_password_hash(newpassword)}, synchronize_session='fetch')
                db.session.commit()
                return success_handle(output)
            else:
                print("An error reset password.")
                return error_handle("An error reset password.")
        else:
            print("An error reset password.")
            return error_handle("An error reset password.")
    else:
        return error_handle("user id is empty.")

@app.route('/edit_password', methods=['POST'])
@login_required
def edit_password():
    output = json.dumps({"success": True})
    user_id =  request.form['id']
    password =  request.form['password']
    newpassword =  request.form['newpassword']

    if user_id:
        if (int(user_id) != current_user.id):
            return error_handle("Cannot edit other user.")

        user_ = User.query.filter_by(id=user_id).first()
        if user_:
            if bc.check_password_hash(user_.password, password):
                db.session.query(User).filter_by(id=user_id).update({"password": bc.generate_password_hash(newpassword)}, synchronize_session='fetch')
                db.session.commit()
                return success_handle(output)
            else:
                print("An error edit password.")
                return error_handle("An error edit password.")
        else:
            print("An error edit password.")
            return error_handle("An error edit password.")
    else:
        return error_handle("user id is empty.")


@app.route('/edit_profile', methods=['POST'])
@login_required
@user_is("admin")
def edit_profile():
    output = json.dumps({"success": True})
    user_id =  request.form['id']
    user =  request.form['user'] 
    full_name =  request.form['name']
    email =  request.form['email']
    phone =  request.form['phone']
    birth =  request.form['birth']
    role =  request.form['role']
    gender =  request.form['gender']
    position =  request.form['position']
    company =  request.form['company']
    code =  request.form['code']
    guest_company =  request.form['guest_company']
    user_type =  request.form['user_type']
    permissions =  request.form['permissions']
    unit = request.form['unit']
    address = request.form['address']
    file_num =  request.form['file_num']
    file = None
    file_image_path = ""
    print(user_id)
    user_ = User.query.filter_by(id=user_id).first()
    if (not user_):
        return error_handle("User is not existed.")

    if not is_same_company(user_.company_id):
        return error_handle("Cannot edit other company's user.")
    if user_:
        if int(file_num) > 0:
            for i in range(int(file_num)):
                file_index = 'file' + str(i)
                if file_index in request.files:
                    file = request.files[file_index]
                    if file:
                        if file.mimetype not in ['image/png', 'image/jpeg', 'application/octet-stream']:
                            print("File extension is not allowed")
                            return error_handle("We are only allow upload file with *.png , *.jpg")
                        else:
                            filename = str(int(time.time())) + secure_filename(file.filename)
                            urlSafeEncodedBytes = base64.urlsafe_b64encode(filename.encode("utf-8"))[:20]
                            filename_str = str(urlSafeEncodedBytes)
                            filename_str = filename_str.replace("=","")
                            filename_str = filename_str.replace("'","")

                            file_image_path = path.join(face_image_path + "/" + str(user_.company_id), user_id + "_" + filename_str + ".jpg");
                            file_image_path_no_ext = path.join(face_image_path + "/" + str(user_.company_id), user_id + "_" + filename_str);
                            file.save(path.join(basedir, file_image_path))

                            img = cv2.imread(path.join(basedir, file_image_path), cv2.IMREAD_COLOR)
                        
                            bboxes = detector.detect_faces(img)

                            i = 0

                            db_path = feature_db_path + str(user_.company_id) + ".db"
                            if not os.path.isfile(db_path):
                                db_o_path = feature_db_path + "mq_feature_empty.db"
                                shutil.copy2(db_o_path, db_path)

                            conn = sqlite3.connect(db_path)
                            c = conn.cursor()
                            if len(bboxes) > 0:
                                for bboxe in bboxes:
                                    bbox = bboxe['box']
                                    bbox = np.array([bbox[0], bbox[1], bbox[0]+bbox[2], bbox[1]+bbox[3]])
                                    landmarks = bboxe['keypoints']
                                    landmarks = np.array([landmarks["left_eye"][0], landmarks["right_eye"][0], landmarks["nose"][0], landmarks["mouth_left"][0], landmarks["mouth_right"][0],
                                                        landmarks["left_eye"][1], landmarks["right_eye"][1], landmarks["nose"][1], landmarks["mouth_left"][1], landmarks["mouth_right"][1]])
                                    landmarks = landmarks.reshape((2,5)).T
                                    nimg = face_preprocess.preprocess(img, bbox, landmarks, image_size='112,112')

                                    nimg1 = cv2.cvtColor(nimg, cv2.COLOR_BGR2RGB)
                                    nimg1 = np.transpose(nimg1, (2,0,1))
                                    model = get_model(ctx, image_size, model_path, 'fc1')
                                    facenet_fingerprint = get_feature(model, nimg1).reshape(1,-1)

                                    if (len(facenet_fingerprint) > 0):
                                        feature_str = ""
                                        for value in facenet_fingerprint[0]:
                                            feature_str = feature_str + str(value) + "#"
                                        #print(feature_str) 

                                        face_img = file_image_path
                                        if (i > 0):
                                            face_img = file_image_path_no_ext + "_" + str(i) + ".jpg"
                                        
                                        cv2.imwrite(path.join(basedir, face_img),nimg)
                                        face = Faces(user_id= user_id, user_id_o=user_id, file_name = face_img)
                                        db.session.add(face)

                                        try:
                                            feature_name = user_id + "_" + filename_str
                                            if i > 0:
                                                feature_name = user_id + "_" + filename_str + "_" + str(i)
                                            c.execute('''INSERT INTO Features (name, data) VALUES (?, ?)''', (feature_name , feature_str,))
                                        except sqlite3.IntegrityError as e:
                                            print('Insert feature errror: ', e.args[0]) # column name is not unique

                                        i = i + 1

                                        room = session.get(str(current_user.company_id))
                                        data = {}
                                        data['name'] = feature_name
                                        data['feature'] = feature_str
                                        socketio.emit('feature', { 'data' :  json.dumps(data) }, namespace='/camera', room=room )


                                        #TODO: send socket to camera
                                    else:
                                        return error_handle("An error add images.")
                            else:
                                return error_handle("An error add images.")
                            conn.commit()
                            conn.close()
                            db.session.commit()
        try:
            if user and user != 'undefined' :
                db.session.query(User).filter_by(id=user_id).update({"user": user}, synchronize_session='fetch')

            if email and email != "":
                db.session.query(User).filter_by(id=user_id).update({"email": email}, synchronize_session='fetch')

            if phone and phone != "":
                db.session.query(User).filter_by(id=user_id).update({"phone": phone}, synchronize_session='fetch')
            
            if gender and gender != "null":
                db.session.query(User).filter_by(id=user_id).update({"gender": gender}, synchronize_session='fetch')
            
            if full_name and full_name != "":
                db.session.query(User).filter_by(id=user_id).update({"full_name": full_name}, synchronize_session='fetch')

            if user_.is_unknown:
                db.session.query(User).filter_by(id=user_id).update({"confirmed_at": datetime.now(), "is_unknown": False}, synchronize_session='fetch')

            if current_user.has_roles("superuser") and company and company != "null":
                db.session.query(User).filter_by(id=user_id).update({"company_id": company}, synchronize_session='fetch')

            if user_.has_roles("staff") and position and position !="":
                db.session.query(User).filter_by(id=user_id).update({"position": position}, synchronize_session='fetch')

            if (user_.has_roles("user") or user_.has_roles("staff"))  and code and code !="":
                db.session.query(User).filter_by(id=user_id).update({"code": code}, synchronize_session='fetch')
            
            if (birth):
                birth_date = datetime.strptime(birth,"%m/%d/%Y").date()
                db.session.query(User).filter_by(id=user_id).update({"birthday": birth_date}, synchronize_session='fetch')

            if not permissions == "0":
                db.session.query(User).filter_by(id=user_id).update({"permissions": permissions}, synchronize_session='fetch')

            if role and role != "null":
                role_ = db.session.query(Role).filter_by(id=role).first()
                if role_:
                    sql = text('delete from roles_users where user_id={0}'.format(user_id))
                    result = db.session.connection().execute(sql)
                    #user_.roles = []
                    user_.roles.append(role_)

            if int(user_type) == 1 and user_.user_type != 0 :
                db.session.query(User).filter_by(id=user_id).update({"user_type": user_type}, synchronize_session='fetch')
            else:
                db.session.query(User).filter_by(id=user_id).update({"user_type": 0}, synchronize_session='fetch')
            
            if guest_company:
                db.session.query(User).filter_by(id=user_id).update({"guest_company": guest_company}, synchronize_session='fetch')
            
            if unit:
                db.session.query(User).filter_by(id=user_id).update({"unit_id": unit}, synchronize_session='fetch')

            if address:
                print('update', address)
                db.session.query(User).filter_by(id=user_id).update({"address_id": address}, synchronize_session='fetch')

            db.session.commit()
        except SQLAlchemyError as e:
            print(e)
            db.session.rollback()
            return error_handle("An error edit profile.")
        except:
            print("Edit profile exception.")
            db.session.rollback()
            return error_handle("An error edit profile.")
        finally:
            db.session.close()
        
        return success_handle(output)
    else:
        print("An error edit profile.")
        return error_handle("An error edit profile.")

@app.route('/search-face.html')
@login_required
@user_is("admin")
def searchface():
    return render_template( 'pages/search-face.html')

# Authenticate user
@app.route('/lfsearch', methods=['POST'])
def fsearch():
    image = request.files['photo']
    if image.mimetype not in ['image/png', 'image/jpeg', 'application/octet-stream']:
        print("File extension is not allowed")
        return error_handle("We are only allow upload file with *.png , *.jpg")

    image_type = image.name.split('.')[-1] #png/jpg/jpeg
    now = datetime.now()
    image_path = f'{now.day}{now.month}{now.year}_{now.hour}:{now.minute}:{now.second}.{image_type}'
    full_path = os.path.join(face_image_path, image_path)
    with open(full_path, 'wb+') as destination:
        destination.write(image.read())

        img = cv2.imread(full_path, cv2.IMREAD_COLOR)
                        
        bboxes = detector.detect_faces(img)

        if len(bboxes) > 0:
            if len(bboxes) == 1:
                bbox = bboxes[0]['box']
                bbox = np.array([bbox[0], bbox[1], bbox[0]+bbox[2], bbox[1]+bbox[3]])
                landmarks = bboxes[0]['keypoints']
                landmarks = np.array([landmarks["left_eye"][0], landmarks["right_eye"][0], landmarks["nose"][0], landmarks["mouth_left"][0], landmarks["mouth_right"][0],
                                    landmarks["left_eye"][1], landmarks["right_eye"][1], landmarks["nose"][1], landmarks["mouth_left"][1], landmarks["mouth_right"][1]])
                landmarks = landmarks.reshape((2,5)).T
                nimg = face_preprocess.preprocess(img, bbox, landmarks, image_size='112,112')

                nimg1 = cv2.cvtColor(nimg, cv2.COLOR_BGR2RGB)
                nimg1 = np.transpose(nimg1, (2,0,1))
                model = get_model(ctx, image_size, model_path, 'fc1')
                facenet_fingerprint = get_feature(model, nimg1).reshape(1,-1)
                #similarity = 1 - spatial.distance.cosine(db_feature, facenet_fingerprint)

            else:
                for bboxe in bboxes:
                    bbox = bboxe['box']
                    bbox = np.array([bbox[0], bbox[1], bbox[0]+bbox[2], bbox[1]+bbox[3]])
                    landmarks = bboxe['keypoints']
                    landmarks = np.array([landmarks["left_eye"][0], landmarks["right_eye"][0], landmarks["nose"][0], landmarks["mouth_left"][0], landmarks["mouth_right"][0],
                                        landmarks["left_eye"][1], landmarks["right_eye"][1], landmarks["nose"][1], landmarks["mouth_left"][1], landmarks["mouth_right"][1]])
                    landmarks = landmarks.reshape((2,5)).T
                    nimg = face_preprocess.preprocess(img, bbox, landmarks, image_size='112,112')

                    nimg1 = cv2.cvtColor(nimg, cv2.COLOR_BGR2RGB)
                    nimg1 = np.transpose(nimg1, (2,0,1))
                    model = get_model(ctx, image_size, model_path, 'fc1')
                    facenet_fingerprint = get_feature(model, nimg1).reshape(1,-1)
                    i = 0
                    if (len(facenet_fingerprint) > 0):
                        face_img = full_path
                        if (i > 0):
                            face_img = file_image_path_no_ext + "_" + str(i) + ".jpg"
                        cv2.imwrite(path.join(basedir, face_img),nimg)
                        i = i + 1

        else:
            return redirect('search-face.html')

    



@app.route('/users.html')
@login_required
@user_is("admin")
def users():
    companies = []
    roles = db.session.query(Role).all()
    refined_roles = []
    
    if (current_user.has_roles("admin")):
        for role in roles:
            if role.name != "admin" and role.name != "superuser":
                refined_roles.append(role)
        companies = db.session.query(Companies).filter(Companies.id == current_user.company_id).all()
    elif (current_user.has_roles("superuser")):
        refined_roles = roles
        companies = db.session.query(Companies).all()
    addresses = Addresses.query.filter_by(company_id=current_user.company_id)
    return render_template( 'pages/users.html', companies=companies, roles=refined_roles, addresses=addresses)

@app.route('/users_data')
@login_required
@user_is("admin")
def users_data():
    """Return server side data."""
    # defining columns
    columns = [
        ColumnDT(User.id),
        ColumnDT(User.user),
        ColumnDT(Role.name),
        ColumnDT(User.full_name),
        ColumnDT(User.email),
        ColumnDT(Companies.name),
        ColumnDT(User.position),
        ColumnDT(User.code)
    ]


    if (current_user.has_roles("superuser")):
        query = db.session.query().select_from(User).join(User.roles).outerjoin(Companies).filter(User.is_unknown == False)
    else:
        query = db.session.query().select_from(User).join(User.roles).outerjoin(Companies).filter(User.is_unknown == False).filter(User.company_id == current_user.company_id).filter((Role.name == "staff") | (Role.name == "user")).group_by(User.id)

    # GET parameters
    params = request.args.to_dict()

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(params, query, columns)

    # returns what is needed by DataTable
    # print(rowTable.output_result())
    return jsonify(rowTable.output_result())

@app.route('/add_user', methods=['POST'])
@login_required
@user_is("admin")
def add_user():
    output = json.dumps({"success": True})
    #print(request.form['name'])
    
    if current_user.has_roles("superuser"):  
        company = request.form['company']     
        if not is_same_company(company):
            return error_handle("An error add user.")
    else:
        company = current_user.company_id

   
    account =  request.form['user']


    if account:
        user_ = User.query.filter_by(user=account).first()
        if not user_:
            user = User(user=account, password=bc.generate_password_hash(request.form['password']), email=request.form['email'], confirmed_at=datetime.now())
            # user.code = request.form['code']
            user.company_id = company
            # user.position = request.form['position']
            user.full_name = request.form['name']
            user.address_id = request.form['address']

            user_role = db.session.query(Role).filter_by(id=request.form['role']).first()
            user.roles = []
            user.roles.append(user_role)
            db.session.add(user)
            db.session.commit()

            if user.id:
                return success_handle(output)
            else:
                print("An error saving user.")
                return error_handle("An error saving user.")
        else:
            print("User is existing.")
            return error_handle("User is existing.")
    else:
        return error_handle("user is empty.")


@app.route('/del_user', methods=['POST'])
@login_required
@user_is("admin")
def del_user():
    output = json.dumps({"success": True})
    user_id =  request.form['id']
    user = User.query.filter_by(id=user_id).first()
    
    if user:
        if not is_same_company(user.company_id):
            return error_handle("An error delete user.")
        user.roles = []
        db.session.commit()

        db_path = feature_db_path + str(user.company_id) + ".db"
        if not os.path.isfile(db_path):
            db_o_path = feature_db_path + "mq_feature_empty.db"
            shutil.copy2(db_o_path, db_path)

        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        faces = Faces.query.filter_by(user_id=user.id).all()
        
        for face in faces:
            file_name = face.file_name.replace(face_image_path, "")
            file_name = file_name.replace("/" + str(current_user.company_id), "")
            file_name = file_name.replace("/", "")
            file_name = file_name.replace(".jpg", "")
            print(file_name)

            try:
                sql_Delete_query = """DELETE FROM Features WHERE Features.name = '{0}'""".format(file_name)
                c.execute(sql_Delete_query)
                conn.commit()
                Faces.query.filter_by(id=face.id).delete()
                Histories.query.filter_by(user_id=user.id).delete()
            except sqlite3.IntegrityError as e:
                print('Remove feature errror: ', e.args[0]) # column name is not unique
            except Exception as e:
                conn.rollback()

            #TODO: send socket to camera to remove

            room = session.get(str(user.company_id))
            data = {}
            data['name'] = file_name
            socketio.emit('feature_del', { 'data' :  json.dumps(data) }, namespace='/camera', room=room )


        conn.commit()
        conn.close()

        db.session.commit()

        ret = User.query.filter_by(id=user_id).delete()
        if ret:
            db.session.commit()
            return success_handle(output)
        else:
            return error_handle("An error delete user.")
    else:
        return error_handle("An error delete user.")

@app.route('/add_history_face', methods=['POST'])
@login_required
@user_is("admin")
def add_history_face():
    output = json.dumps({"success": True})
    user_id =  request.form['id']
    hid =  request.form['hid']


    user_ = User.query.filter_by(id=user_id).first()

    if (not user_):
        return error_handle("User is not existed.")

    history = Histories.query.filter_by(id=hid).first()

    if history:
        db_path = feature_db_path + str(current_user.company_id) + ".db"
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        img = cv2.imread(path.join(basedir, history.image), cv2.IMREAD_COLOR)

        nimg1 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        nimg1 = np.transpose(nimg1, (2,0,1))
        model = get_model(ctx, image_size, model_path, 'fc1')
        facenet_fingerprint = get_feature(model, nimg1).reshape(1,-1)

        if (len(facenet_fingerprint) > 0):
            feature_str = ""
            for value in facenet_fingerprint[0]:
                feature_str = feature_str + str(value) + "#" 
            
            face = Faces(user_id= user_id, user_id_o=user_id, file_name = history.image)
            db.session.add(face)

            try:
                file_name = face.file_name.replace(face_image_path, "")
                file_name = file_name.replace("/" + str(user_.company_id), "")
                file_name = file_name.replace("/", "")
                file_name = file_name.replace(".jpg", "")
                c.execute('''INSERT INTO Features (name, data) VALUES (?, ?)''', (file_name , feature_str,))

                room = session.get(str(current_user.company_id))
                data = {}
                data['name'] = file_name
                data['feature'] = feature_str
                socketio.emit('feature', { 'data' :  json.dumps(data) }, namespace='/camera', room=room )

            except sqlite3.IntegrityError as e:
                print('Insert feature errror: ', e.args[0]) # column name is not unique



        conn.commit()
        conn.close()
        db.session.commit()
        
        return success_handle(output)
    else:
        return error_handle("History is not existed.")