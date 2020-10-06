# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

# Python modules
import os, logging 
from os import path, getcwd
# Flask modules
from flask               import render_template, request, url_for, redirect, send_from_directory, jsonify, json, Response, session
from flask_login         import login_user, logout_user, current_user
from flask_socketio   import SocketIO, emit, join_room, leave_room
from werkzeug.exceptions import HTTPException, NotFound, abort, Forbidden
from werkzeug.utils import secure_filename
from functools import wraps
import base64
import shutil, sys
import requests
from sqlalchemy import func, text

# App modules
from app        import app, lm, db, bc, mail, socketio, q
from models import User, Role, Companies, Addresses, Cameras, Plans, Faces, Histories, Events, EventLogs
from forms  import LoginForm, RegisterForm
from datatables import ColumnDT, DataTables
from datetime import date, timedelta, datetime
import base64
import time
from flask_mail import Message
import random
import string
from PIL import Image
from pprint import pprint
import numpy as np
import cv2
import sqlite3
from flask_jwt import JWT, jwt_required, current_identity
from werkzeug.security import safe_str_cmp
from tasks import sent_event_webhook
import enum


basedir = os.path.abspath(os.path.dirname(__file__))
company_image_path = 'static/assets/img/company'
face_image_path = 'static/assets/img/face'
event_image_path = 'static/assets/img/event'
feature_db_path = 'static/db/'

def success_handle(output, status=200, mimetype='application/json'):
    return Response(output, status=status, mimetype=mimetype)


def error_handle(error_message, status=500, mimetype='application/json'):
    return Response(json.dumps({"error": {"message": error_message}}), status=status, mimetype=mimetype)

@app.route('/api/launch', methods=['POST'])
def launch():
    output = json.dumps({"success": True})

    udid = request.form['udid']

    cam = db.session.query(Cameras).filter(Cameras.udid == udid).first()
    if  cam != None and cam.company_id:       
        if cam.company_id:
            db_path = os.path.join(basedir, feature_db_path + str(cam.company_id) + ".db")
            if not os.path.isfile(db_path):
                db_o_path = os.path.join(basedir, feature_db_path + "mq_feature_empty.db")
                shutil.copy2(db_o_path, db_path)

            company_face_dir = path.join(basedir, path.join(face_image_path + "/" + str(cam.company_id)))
            if not os.path.isdir(company_face_dir):
                os.mkdir(company_face_dir)

            return_output = json.dumps({"company_id": cam.company_id, "feature_path": "/" + feature_db_path + str(cam.company_id) + ".db"})   
            return success_handle(return_output)
        else:
             return error_handle("The camera is not assigned")
    else:
        print("Something happend")
        return error_handle("Cannot find the camera")
    
    return success_handle(output)


@app.route('/api/create_unknown', methods=['POST'])
def create_unknown():
    output = json.dumps({"success": True})

    udid = request.form['udid']
    filename = request.form['filename']
    feature = request.form['feature']
    #name = 'Unknown_' + time.strftime("%Y%m%d-%H%M%S")
    now = datetime.now()

    # print("Feature", feature);
    # print("Feature64", base64.b64decode(feature));
    print("Information of that face", filename)

    cam = db.session.query(Cameras).filter(Cameras.udid == udid).first()
    if  cam != None and cam.company_id:
        user = User(user=filename + "_" + str(cam.company_id), is_unknown=True, company_id=cam.company_id, full_name=filename + "_" + str(cam.company_id))
        user_role = db.session.query(Role).filter_by(name="user").first()
        print(user_role)
        user.roles = []
        user.roles.append(user_role)
        db.session.add(user)
        db.session.commit()

        if user:    
            image = path.join(face_image_path + "/" + str(cam.company_id),  filename + ".jpg")
            face = Faces(user_id=user.id, user_id_o = user.id, file_name=image);
            db.session.add(face)
            db.session.commit()

            for i in range(20):
                tmp = path.join(face_image_path + "/" + str(cam.company_id), filename + "_" + str(i) + ".jpg")
                if os.path.isfile(path.join(basedir, tmp)):
                    face = Faces(user_id=user.id, user_id_o = user.id, file_name=tmp);
                    db.session.add(face)
            db.session.commit()
            if face:
                print("cool face has been saved")
                history = Histories(user_id=face.user_id, user_id_o = user.id, image=image, time=now, camera=cam.id);
                db.session.add(history)
                db.session.commit()

                if history:
                    
                    data = {
                        "cam_id": cam.id,
                        "image"  : filename,
                        "time"       : now.timestamp(),
                        "user_data"   : user.to_dict()
                    }
                    company = Companies.query.filter_by(id=cam.company_id).first()
                    job = q.enqueue_call(
                        func=sent_event_webhook, args=(company.secret, 4, data,), result_ttl=5000
                    )
                    print(job.get_id())

                    full_name = user.full_name
                    return_output = json.dumps({"id": history.id, "time": history.time, "user_name": full_name}) 

                    return success_handle(return_output)
                else:
                    print("An error saving history.")
                    return error_handle("An error saving history.")
            else:

                print("An error saving face image.")

                return error_handle("An error saving face image.")
        else:
             return error_handle("Cannot create a user")
    else:
        print("Something happend")
        return error_handle("Cannot find the camera")
    
    return success_handle(output)


@app.route('/api/image_camera', methods=['POST'])
def image_camera():
    output = json.dumps({"success": True})
    print("==========================================>")
    udid = request.form['udid']
    cam = db.session.query(Cameras).filter(Cameras.udid == udid).first()
    if cam != None and cam.company_id:
        if 'file' not in request.form:
            print ("image is required")
            return error_handle("image is required.")
        else:
            # get name in form data
            filename = request.form['filename']
            file = base64.b64decode(request.form['file'])
            nparr = np.fromstring(file, np.uint8)
            print("File name:", filename)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            cv2.imwrite(path.join(basedir, path.join(event_image_path + "/" + str(cam.company_id), filename)), img)
            return_output = json.dumps({"file_path": path.join(event_image_path + "/" + str(cam.company_id), filename)})   
            return success_handle(return_output)
    
    else:
        print("Cannot find the camera")
        return error_handle("Cannot find the camera")

    return success_handle(output)


@app.route('/api/image', methods=['POST'])
def image():
    output = json.dumps({"success": True})
    udid = request.form['udid']
    cam = db.session.query(Cameras).filter(Cameras.udid == udid).first()
    if  cam != None and cam.company_id:
        if 'file' not in request.files:

            print ("image is required")
            return error_handle("image is required.")
        else:

            file = request.files['file']
            print(file)
            print("File request type: ", file.mimetype)
            if file.mimetype not in app.config['file_allowed']:

                print("File extension is not allowed")

                return error_handle("We are only allow upload file with *.png , *.jpg")
            else:
                print("File is allowed and will be saved in ", face_image_path + "/" + str(cam.company_id))
                # get name in form data
                filename = request.form['filename']

                print("File name:", filename)
                img = cv2.imdecode(np.asarray(bytearray(file.read()), dtype="uint8"), cv2.IMREAD_COLOR)
                cv2.imwrite(path.join(basedir, path.join(face_image_path + "/" + str(cam.company_id), filename)), img)
                return_output = json.dumps({"file_path": path.join(face_image_path + "/" + str(cam.company_id), filename)})   
                return success_handle(return_output)
    
    else:
        print("Something happend")
        return error_handle("Cannot find the camera")

    return success_handle(output)

@app.route('/api/image_event', methods=['POST'])
def image_event():
    output = json.dumps({"success": True})
    udid = request.form['udid']
    cam = db.session.query(Cameras).filter(Cameras.udid == udid).first()
    if  cam != None and cam.company_id:
        if 'file' not in request.files:

            print ("image is required")
            return error_handle("image is required.")
        else:

            file = request.files['file']
            print(file)
            print("File request type: ", file.mimetype)
            if file.mimetype not in app.config['file_allowed']:

                print("File extension is not allowed")

                return error_handle("We are only allow upload file with *.png , *.jpg")
            else:
                print("File is allowed and will be saved in ", event_image_path + "/" + str(cam.company_id))
                # get name in form data
                filename = request.form['filename']

                print("File name:", filename)
                img = cv2.imdecode(np.asarray(bytearray(file.read()), dtype="uint8"), cv2.IMREAD_COLOR)
                cv2.imwrite(path.join(basedir, path.join(event_image_path + "/" + str(cam.company_id), filename)), img)
                return_output = json.dumps({"file_path": path.join(event_image_path + "/" + str(cam.company_id), filename)})   
                return success_handle(return_output)
    
    else:
        print("Something happend")
        return error_handle("Cannot find the camera")

    return success_handle(output)


@app.route('/api/history', methods=['POST'])
def history():
    output = json.dumps({"success": True})

    # get name in form data
    udid = request.form['udid']
    filename = request.form['filename']
    image = request.form['image']
    feature = request.form['feature']
    now = datetime.now()
    print("Information of that face", filename)
    cam = db.session.query(Cameras).filter(Cameras.udid == udid).first()
    if  cam != None and cam.company_id:
        face = db.session.query(Faces).filter(Faces.file_name == path.join(face_image_path + "/" + str(cam.company_id),  filename + ".jpg")).first()

        if  face != None:
            history = Histories(user_id=face.user_id, user_id_o=face.user_id, image=path.join(face_image_path + "/" + str(cam.company_id),  image), time=now, camera=cam.id);
            db.session.add(history)
            db.session.commit()
            if history:
                user = User.query.filter(User.id == face.user_id).first()
                if user:
                    data = {
                        "cam_id": cam.id,
                        "image"  : filename,
                        "time"       : now.timestamp(),
                        "user_data"   : user.to_dict()
                    }
                    company = Companies.query.filter_by(id=cam.company_id).first()
                    job = q.enqueue_call(
                        func=sent_event_webhook, args=(company.secret, 5, data,), result_ttl=5000
                    )

                    # send action to the camera
                    if user.has_roles("admin") or user.has_roles("staff"):
                        room = session.get(str(cam.company_id))
                        data = {}
                        data['camera_id'] = cam.udid
                        socketio.emit('action', { 'data' :  json.dumps(data) }, namespace='/camera', room=room )

                    full_name = user.full_name
                    full_name = full_name.encode('utf8')
                    full_name = base64.b64encode(full_name)
                    return_output = json.dumps({"id": history.id, "time": history.time, "user_name": full_name.decode('utf-8')})   
                    return success_handle(return_output)
                else:
                    # Delete the face which has no user
                    db_path = feature_db_path + str(cam.company_id) + ".db"
                    if not os.path.isfile(db_path):
                        db_o_path = feature_db_path + "mq_feature_empty.db"
                        shutil.copy2(db_o_path, db_path)

                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()

                    try:
                        sql_Delete_query = """DELETE FROM Features WHERE Features.name = '{0}'""".format(filename)
                        c.execute(sql_Delete_query)
                        Faces.query.filter_by(id=face.id).delete()
                    except sqlite3.IntegrityError as e:
                        print('Remove feature errror: ', e.args[0]) # column name is not unique
                    except Exception as e:
                        conn.rollback()
                        conn.close()
                        db.session.rollback()
                        return error_handle("An error delete face.")
                    #TODO: send socket to camera to remove
                    
                    room = session.get(str(cam.company_id))
                    data = {}
                    data['name'] = filename
                    socketio.emit('feature_del', { 'data' :  json.dumps(data) }, namespace='/camera', room=room )

                    conn.commit()
                    conn.close()


                    return error_handle("Cannot find the user.")
            else:
                print("An error saving history.")

                return error_handle("An error saving history.")
        else:

            # Delete the no face
            db_path = feature_db_path + str(cam.company_id) + ".db"
            if not os.path.isfile(db_path):
                db_o_path = feature_db_path + "mq_feature_empty.db"
                shutil.copy2(db_o_path, db_path)

            conn = sqlite3.connect(db_path)
            c = conn.cursor()

            try:
                sql_Delete_query = """DELETE FROM Features WHERE Features.name = '{0}'""".format(filename)
                print(sql_Delete_query)
                c.execute(sql_Delete_query)
            except sqlite3.IntegrityError as e:
                print('Remove feature errror: ', e.args[0]) # column name is not unique
            except Exception as e:
                conn.rollback()
                conn.close()
                return error_handle("An error delete face.")
            #TODO: send socket to camera to remove
            room = session.get(str(cam.company_id))
            data = {}
            data['name'] = filename
            socketio.emit('feature_del', { 'data' :  json.dumps(data) }, namespace='/camera', room=room )

            conn.commit()
            conn.close()

            return error_handle("No face can found.")
    else:
        return error_handle("No cam can found.")
    
    return success_handle(output)

@app.route('/api/v1/eventtypes')
@jwt_required()
def eventtypes():
    output = json.dumps({"success": True})
    
    offset = request.args.get('offset') or 0
    limit = request.args.get('limit') or 20


    events = db.session.query(Events).offset(offset).limit(limit).all()
    if events:
        data = []
        for u in events:
            temp = u.to_dict()
            data.append(temp)
        return_output = json.dumps({"events": data}) 
        
        return success_handle(return_output)
    else:
        return error_handle("User list is empty")

@app.route('/api/v1/events')
@jwt_required()
def events():
    output = json.dumps({"success": True})
    cam_id = request.args.get('cam_id') or -1
    event_id = request.args.get('event_id') or -1
    offset = request.args.get('offset') or 0
    limit = request.args.get('limit') or 20

    query = db.session.query(EventLogs)

    if (int(cam_id) > 0):
        query = query.filter(cam_id == EventLogs.camera_id)

    if (int(event_id) > 0):
        query = query.filter(event_id == EventLogs.event_id)

    events = query.order_by(EventLogs.time.desc()).offset(offset).limit(limit).all()
    if events:
        data = []
        for u in events:
            event = Events.query.filter_by(id=u.event_id).first()
            address = Addresses.query.filter_by(id=u.address_id).first()
            temp = u.to_dict()
            temp['event_name'] = event.name
            temp['latitude'] = address.latitude
            temp['longitude'] = address.longitude
            data.append(temp)
        return_output = json.dumps({"events": data}) 
        
        return success_handle(return_output)
    else:
        return error_handle("Event list is empty")


@app.route('/api/v1/trigger_event', methods=['POST'])
def trigger_event():
    output = json.dumps({"success": True})

    # get name in form data
    event_id = request.form['event_id']
    udid = request.form['udid']
    image_path = request.form['image_path']
    user_data = request.form['data']
    event = Events.query.filter_by(id=event_id).first()
    now = datetime.now()
    if event:
        cam = db.session.query(Cameras).join(Addresses).filter(Cameras.udid == udid).first()
        if cam != None and cam.company_id:
            
            company = Companies.query.filter_by(id=cam.company_id).first()
            # link = "http://camera-chinhcong.test.mqsolutions.vn/api/test"
            data = {
                "cam_id": udid,
                "image"  : image_path,
                "time"       : now.timestamp(),
                "user_data"   : user_data
            }
            job = q.enqueue_call(
                func=sent_event_webhook, args=(company.secret, event_id, data), result_ttl=5000
            )
            print("=======" + str(cam.id))
            
            event_log = EventLogs(user_id=None, event_id=event.id, time=now, camera_id=cam.id, image=path.join(event_image_path + "/" + str(cam.company_id), image_path), data=user_data)
            db.session.add(event_log)
            db.session.commit()
        else:
            return error_handle("No camare can found.")
    else:
        return error_handle("No event can found.")

    return success_handle(output)

# @app.route('/api/event', methods=['POST'])
# def event():
#     output = json.dumps({"success": True})

#     # get name in form data
#     print(request.form)
#     name = request.form['name']
#     udid = request.form['udid']
#     file_name = request.form['filename']
#     time = request.form['time']
#     distance = request.form['distance']
#     video = request.form['link_video']
#     if name == "socialdistancing":
#         name = "Giãn cách xã hội"
#     print("Information of that event", file_name, name)
#     event = Events.query.filter_by(name=name).first()
#     if event:
#         cam = db.session.query(Cameras).join(Addresses).filter(Cameras.udid == udid).first()
#         if cam != None and cam.company_id:
#             time = datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')
            
#             company = Companies.query.filter_by(id=cam.company_id).first()
#             link = company.secret
#             # link = "http://camera-chinhcong.test.mqsolutions.vn/api/test"
#             data = {
#                 "event_name" : name,
#                 "camera_udid": udid,
#                 "file_name"  : file_name,
#                 "time"       : time.strftime('%H:%M:%S ngày %d-%m-%Y'),
#                 "distance"   : distance,
#                 "link_video" : video
#             }
#             job = q.enqueue_call(
#                 func=sent_event_webhook, args=(link, name, data), result_ttl=5000
#             )
            
#             socketio.emit('send event', {"name": name, "link" : video, "address": cam.name})
            
#             event_log = EventLogs(user_id=None, event_id=event.id, address=cam.name, start=time, end=time, company_id=cam.company_id, camera_id=cam.id, image=path.join(face_image_path + "/" + str(cam.company_id), file_name), distance=distance, link_video=video)
#             db.session.add(event_log)
#             db.session.commit()
#             if not time:
#                 return error_handle("Can not save event.")
#         else:
#             return error_handle("No camare can found.")
#     else:
#         return error_handle("No event can found.")

#     return success_handle(output)


@app.route('/api/v1/add_webhook', methods=['POST'])
@jwt_required()
def add_webhook():
    #pprint(vars(current_identity))
    output = json.dumps({"success": True})
    link = request.json.get('link', None)
    
    if link:
        db.session.query(Companies).filter_by(id=current_identity.company_id).update({"secret": link}, synchronize_session='fetch')
        db.session.commit()
        return success_handle(output)
    else:
        return error_handle("No link error")

@app.route('/api/v1/company')
@jwt_required()
def company():
    output = json.dumps({"success": True})
 
    company = db.session.query(Companies).filter(Companies.id == current_identity.company_id).first()
    if company:
        result = company.to_dict()
        return_output = json.dumps({"company": result}) 
        return success_handle(return_output)
    else:
        return error_handle("The company does not exist")

@app.route('/api/v1/cameras')
@jwt_required()
def cameras():
    output = json.dumps({"success": True})
    
    offset = request.args.get('offset') or 0
    limit = request.args.get('limit') or 20

    cameras = db.session.query(Cameras, Addresses).join(Addresses).filter(Cameras.company_id == current_identity.company_id).offset(offset).limit(limit).all()
    print(cameras)
    if cameras:
        data = []
        for c, a in cameras:
            temp = c.to_dict()
            temp["address"] = a.to_dict()
            del temp["address"]["camera"]
            data.append(temp)
        return_output = json.dumps({"cameras": data}) 
        return success_handle(return_output)
    else:
        return error_handle("Camera list is empty")

@app.route('/api/v1/info_event')
@jwt_required()
def info_event():
    output = json.dumps({"success": True})
    try:
        cameras = db.session.query(Cameras).filter(Cameras.company_id == current_identity.company_id)
        num_events = db.session.query(EventLogs).filter(Cameras.company_id == current_identity.company_id).count()
        now = datetime.now()
        num_inactive_cameras = 0
        num_cameras_for_office = 0
        num_cameras_for_traffic = 0
        num_cameras_for_event = 0
        for camera in cameras:
            num_inactive_cameras += int((now - camera.time).total_seconds()) > 360
            num_cameras_for_office += camera.type == 0 
            num_cameras_for_traffic += camera.type == 1
            num_cameras_for_event += camera.type == 2 
        return_output = json.dumps({"total_cameras": cameras.count(), "num_inactive_cameras": num_inactive_cameras, "num_events": num_events, "num_cameras_for_office": num_cameras_for_office, "num_cameras_for_traffic": num_cameras_for_traffic, "num_cameras_for_event": num_cameras_for_event}) 

        return success_handle(return_output)
    except:
        return error_handle({"error"})

@app.route('/api/v1/addresses')
@jwt_required()
def addresses():
    output = json.dumps({"success": True})
    
    offset = request.args.get('offset') or 0
    limit = request.args.get('limit') or 20

    addresses = db.session.query(Addresses).filter(Addresses.company_id == current_identity.company_id).offset(offset).limit(limit).all()
    if addresses:
        data = []
        for a in addresses:
            temp = a.to_dict()
            data.append(temp)
        return_output = json.dumps({"addresses": data}) 
        return success_handle(return_output)
    else:
        return error_handle("Address list is empty")

@app.route('/api/v1/user/<user_id>')
@jwt_required()
def user(user_id):
    output = json.dumps({"success": True})
    
    user = db.session.query(User).filter(User.id == user_id).filter(User.company_id == current_identity.company_id).first()

    if user:
        return_output = json.dumps({"user": user.to_dict()}) 
        return success_handle(return_output)
    else:
        return error_handle("User does not exist or you have no permission to access")


@app.route('/api/v1/address/<address_id>')
@jwt_required()
def address(address_id):
    output = json.dumps({"success": True})
    
    address_ = db.session.query(Addresses).filter(Addresses.id == address_id).filter(Addresses.company_id == current_identity.company_id).first()
    if address_:
        return_output = json.dumps({"address": address_.to_dict()}) 
        return success_handle(return_output)
    else:
        return error_handle("Address does not exist or you have no permission to access")

@app.route('/api/v1/camera/<camera_id>')
@jwt_required()
def camera(camera_id):
    output = json.dumps({"success": True})
    
    camera = db.session.query(Cameras).filter(Cameras.id == camera_id).filter(Cameras.company_id == current_identity.company_id).first()
    if camera:
        return_output = json.dumps({"camera": camera.to_dict()}) 
        return success_handle(return_output)
    else:
        return error_handle("Camera does not exist or you have no permission to access")


@app.route('/api/v1/users')
@jwt_required()
def user_list():
    output = json.dumps({"success": True})
    
    offset = request.args.get('offset') or 0
    limit = request.args.get('limit') or 20


    users = db.session.query(User).filter(User.company_id == current_identity.company_id).offset(offset).limit(limit).all()
    if users:
        data = []
        for u in users:
            temp = u.to_dict()
            data.append(temp)
        return_output = json.dumps({"users": data}) 
        
        return success_handle(return_output)
    else:
        return error_handle("User list is empty")

@app.route('/api/v1/histories')
@jwt_required()
def histories():
    output = json.dumps({"success": True})
    
    offset = request.args.get('offset') or 0
    limit = request.args.get('limit') or 20
    camera_id = request.args.get('camera_id') or -1
    camera_id = int(camera_id)

    if camera_id > 0:
        histories = db.session.query(Histories).join(Cameras).filter(Cameras.id == camera_id).offset(offset).limit(limit).all()
    else:  
        histories = db.session.query(Histories).join(Cameras).filter(Cameras.company_id == current_identity.company_id).offset(offset).limit(limit).all()
    if histories:
        data = []
        for h in histories:
            temp = h.to_dict()
            data.append(temp)
        return_output = json.dumps({"histories": data}) 
        return success_handle(return_output)
    else:
        return error_handle("History list is empty")


@app.route('/api/v1/histories_detail')
@jwt_required()
def histories_detail():
    output = json.dumps({"success": True})
    
    offset = request.args.get('offset') or 0
    limit = request.args.get('limit') or 20

    camera_id = request.args.get('camera_id') or -1
    camera_id = int(camera_id)
    if camera_id > 0:
        histories = db.session.query(Histories).join(Cameras).filter(Cameras.id == camera_id).offset(offset).limit(limit).all()
    else:  
        histories = db.session.query(Histories).join(Cameras).filter(Cameras.company_id == current_identity.company_id).offset(offset).limit(limit).all()

    if histories:
        data = []
        for h in histories:
            temp = h.to_dict()
            
            if (temp["camera"]):
                camera = db.session.query(Cameras).filter(Cameras.id == temp["camera"]).first()
                if camera:
                     temp["camera"] = camera.to_dict()
            user = db.session.query(User).filter(User.id == temp["user_id"]).first()
            if user:
                 temp["user"] = user.to_dict()
                 del temp['user_id']
            data.append(temp)
        return_output = json.dumps({"histories_detail": data}) 
        return success_handle(return_output)
    else:
        return error_handle("History list is empty")

@app.route('/api/test', methods=['POST'])
def test():
    output = json.dumps({"success": True})
    
    event = request.json
    if event:
        print(event);
        data = request.json.get('data', None)
        if data:
            print("WEBHOOK receive data =========")
            print(data);
            return_output = json.dumps({"data": data}) 
            return success_handle(return_output)
        return success_handle(output)
    else:
        return error_handle("Invalid request")

@app.route('/api/v1/reports')
@jwt_required()
def reports():
    output = json.dumps({"success": True})
    
    unit = request.args.get('unit') 
    date = request.args.get('date') or datetime.now().strftime("%d-%m-%Y")

    selected_datetime = datetime.strptime(date,"%d-%m-%Y").date()
    print("==================")
    print(selected_datetime)
    print("==================")
    absent = Events.query.filter_by(name="Vắng mặt").first()
    if unit:
        absent_count = db.session.query(EventLogs).join(User).filter(EventLogs.event_id == absent.id).filter(EventLogs.time <= selected_datetime + timedelta(days=1)).filter(EventLogs.time >= selected_datetime).filter(User.unit_id == unit).count()

        users = db.session.query(User).join(User.roles).filter(User.company_id == current_identity.company_id).filter(User.unit_id == unit).filter(User.is_unknown == False).filter(Role.name == "staff").all()
    else:
        absent_count = db.session.query(EventLogs).filter(EventLogs.event_id == absent.id).filter(EventLogs.time <= selected_datetime + timedelta(days=1)).filter(EventLogs.time >= selected_datetime).count()

        users = db.session.query(User).join(User.roles).filter(User.company_id == current_identity.company_id).filter(User.is_unknown == False).filter(Role.name == "staff").all()

    in_late_count = 0
    out_early_count = 0
    escape_count = 0
    for user in users:
        address_start, h_start, start = db.session.query(Addresses, Histories, func.min(Histories.time)).join(Cameras, Cameras.id==Histories.camera).join(Addresses, Cameras.address_id==Addresses.id).filter(Histories.user_id == user.id).filter(Histories.time <= selected_datetime + timedelta(days=1)).filter(Histories.time >= selected_datetime).first()
        
        address_end, h_end, end = db.session.query(Addresses, Histories, func.max(Histories.time)).join(Cameras, Cameras.id==Histories.camera).join(Addresses, Cameras.address_id==Addresses.id).filter(Histories.user_id == user.id).filter(Histories.time <= selected_datetime + timedelta(days=1)).filter(Histories.time >= selected_datetime).first()
        if address_start and start and address_start.start and address_start.start < start.time():
            in_late_count = in_late_count + 1
           
        if address_start and end and address_start.end and address_start.end > end.time():
            out_early_count = out_early_count + 1

        if not start:
            escape_count = escape_count + 1

    return_output = json.dumps({"escape_count": escape_count ,"in_late_count": in_late_count, "out_early_count": out_early_count, "absent_count": absent_count }) 

    return success_handle(return_output)

@app.route('/api/v1/public_security')
@jwt_required()
def public_security():
    output = json.dumps({"success": True})
    
    address = request.args.get('address') 
    date = request.args.get('date') or datetime.now().strftime("%d-%m-%Y")

    selected_datetime = datetime.strptime(date,"%d-%m-%Y").date()
    date = datetime.strptime(date,"%d-%m-%Y")
    print("==================")
    print(selected_datetime)
    print("==================")

    social_distancing_event = Events.query.filter_by(name="Giãn cách xã hội").first()
    traffic_flow_event = Events.query.filter_by(name="Mật độ giao thông").first()
    traffic_flow_count = {}
    if address:
        social_distancing_count = db.session.query(EventLogs).filter(EventLogs.event_id == social_distancing_event.id).filter(EventLogs.address_id == address).filter(EventLogs.time <= selected_datetime + timedelta(days=1)).filter(EventLogs.time >= selected_datetime).count()
        while date.date() == selected_datetime:
            car_num = 0
            bike_num = 0
            traffic_flow_eventlogs = db.session.query(EventLogs).filter(EventLogs.event_id == traffic_flow_event.id).filter(EventLogs.address_id == address).filter(EventLogs.time <= date + timedelta(hours=1)).filter(EventLogs.time >= date).all()
            for traffic_flow_eventlog in traffic_flow_eventlogs:
                data = eval(traffic_flow_eventlog.data)
                car_num = car_num + data['car']
                bike_num = bike_num + data['bike']
            key = '{}-{}'.format(date.hour, (date + timedelta(hours=1)).hour )
            traffic_flow_count[key] = { "car_num": car_num, "bike_num": bike_num, "total": car_num + bike_num }
            date = date + timedelta(hours=1)
    else:
        social_distancing_count = db.session.query(EventLogs).filter(EventLogs.event_id == social_distancing_event.id).filter(EventLogs.time <= selected_datetime + timedelta(days=1)).filter(EventLogs.time >= selected_datetime).count()
        while date.date() == selected_datetime:
            car_num = 0
            bike_num = 0
            traffic_flow_eventlogs = db.session.query(EventLogs).filter(EventLogs.event_id == traffic_flow_event.id).filter(EventLogs.time <= date + timedelta(hours=1)).filter(EventLogs.time >= date).all()
            for traffic_flow_eventlog in traffic_flow_eventlogs:
                data = eval(traffic_flow_eventlog.data)
                car_num = car_num + data['car']
                bike_num = bike_num + data['bike']
            key = '{}-{}'.format(date.hour, (date + timedelta(hours=1)).hour)
            traffic_flow_count[key] = { "car_num": car_num, "bike_num": bike_num, "total": car_num + bike_num }
            date = date + timedelta(hours=1)

    
    return_output = json.dumps({"social_distancing_count": social_distancing_count, "traffic_flow_count": traffic_flow_count}) 
    return success_handle(return_output)