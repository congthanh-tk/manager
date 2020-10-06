# Python modules
import os, logging 
from os import path, getcwd
import sqlite3
import shutil, sys
import requests
# Flask modules
from flask               import render_template, request, url_for, redirect, send_from_directory, jsonify, json, Response, session
from flask_login         import login_user, logout_user, current_user
from flask_socketio   import SocketIO, emit, join_room, leave_room
from werkzeug.exceptions import HTTPException, NotFound, abort, Forbidden
from werkzeug.utils import secure_filename
from functools import wraps
import base64
from sqlalchemy import func, text
from sqlalchemy.sql import label
from sqlalchemy.exc import SQLAlchemyError
from configuration import Config
from flask_babel import Babel
from vnpay import vnpay

# App modules
from app        import app, lm, db, bc, mail, socketio, babel
from models import User, Role, Companies, Addresses, Cameras, Plans, Faces, Histories,Versions, Events, EventLogs, Units
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

import face_preprocess
import numpy as np
import cv2
import mxnet as mx
import sklearn
from sklearn.decomposition import PCA
from mtcnn.mtcnn import MTCNN
# import faiss
import hashlib 
from bs4 import BeautifulSoup

detector = MTCNN()
basedir = os.path.abspath(os.path.dirname(__file__))
company_image_path = 'static/assets/img/company'
face_image_path = 'static/assets/img/face'
event_image_path = 'static/assets/img/event'
feature_db_path = os.path.join(basedir, 'static/db/')
version_path = 'static/assets/version'
DATASET_INDEX = 'index.bin'
DATASET_LABELS = 'labels.pkl'
DATASET_DIR = os.path.join(basedir, 'dataset')
SCHEME="http"

ctx = mx.cpu(0)
VERSION_ALLOWED_EXTENSIONS = set(['zip', 'tar'])

image_size = (112,112)
model_path = "models/model-y1-test2/model,0"
ga_model_path = "models/gender-age/model,0"

def get_ga(model, aligned):
    input_blob = np.expand_dims(aligned, axis=0)
    data = mx.nd.array(input_blob)
    db = mx.io.DataBatch(data=(data,))
    model.forward(db, is_train=False)
    ret = model.get_outputs()[0].asnumpy()
    g = ret[:,0:2].flatten()
    gender = np.argmax(g)
    a = ret[:,2:202].reshape( (100,2) )
    a = np.argmax(a, axis=1)
    age = int(sum(a))
    return gender, age

def get_model(ctx, image_size, model_str, layer):
    _vec = model_str.split(',')
    assert len(_vec)==2
    prefix = _vec[0]
    epoch = int(_vec[1])
    print('loading',prefix, epoch)
    sym, arg_params, aux_params = mx.model.load_checkpoint(prefix, epoch)
    all_layers = sym.get_internals()
    sym = all_layers[layer+'_output']
    model = mx.mod.Module(symbol=sym, context=ctx, label_names = None)
    #model.bind(data_shapes=[('data', (args.batch_size, 3, image_size[0], image_size[1]))], label_shapes=[('softmax_label', (args.batch_size,))])
    model.bind(data_shapes=[('data', (1, 3, image_size[0], image_size[1]))])
    model.set_params(arg_params, aux_params)
    return model

def get_feature(model, aligned):
    input_blob = np.expand_dims(aligned, axis=0)
    data = mx.nd.array(input_blob)
    db = mx.io.DataBatch(data=(data,))
    model.forward(db, is_train=False)
    embedding = model.get_outputs()[0].asnumpy()
    embedding = sklearn.preprocessing.normalize(embedding).flatten()
    return embedding


def success_handle(output, status=200, mimetype='application/json'):
    return Response(output, status=status, mimetype=mimetype)


def error_handle(error_message, status=500, mimetype='application/json'):
    return Response(json.dumps({"error": {"message": error_message}}), status=status, mimetype=mimetype)

def is_same_company(company_id):
    if (current_user.has_roles("superuser")):
        return True

    if (current_user.company_id == company_id):
        return True

    return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_active or not current_user.is_authenticated:
            return redirect(url_for('login',_external=True,_scheme=request.scheme))

        return f(*args, **kwargs)
    return decorated_function

def user_is(role):
    """
    Takes an role (a string name of either a role or an ability) and returns the function if the user has that role
    """
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if (current_user.has_roles("superuser")):
                return func(*args, **kwargs)

            if role in [r.name for r in current_user.roles]:
                if current_user.company_id:
                    return func(*args, **kwargs)
            raise Forbidden("You do not have access")
        return inner
    return wrapper


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in VERSION_ALLOWED_EXTENSIONS


@app.cli.command()
def initdb():
    """
    Populate a small db with some example entries.
    """
    print("build_sample_db")

    db.drop_all()
    db.create_all()

    with app.app_context():
        user_role = Role(name='user')
        staf_role = Role(name='staff')
        admin_role = Role(name='admin')
        super_user_role = Role(name='superuser')
        db.session.add(user_role)
        db.session.add(admin_role)
        db.session.add(super_user_role)
        db.session.commit()

        admin_user = User(
            user='admin',
            email='ams@mqsolutions.vn',
            password=bc.generate_password_hash('MQ1234')
            
        )
        admin_user.roles.append(super_user_role)
        cadmin_user = User(
            user='cadmin',
            email='admin1@gmail.com',
            password=bc.generate_password_hash('MQ1234')
        )
        cadmin_user.roles.append(admin_role)
        staff_user = User(
            user='staff',
            email='staff@gmail.com',
            password=bc.generate_password_hash('MQ1234'),
        )
        staff_user.roles.append(staf_role)

        db.session.add(admin_user)
        db.session.add(cadmin_user)
        db.session.add(staff_user)

        db.session.commit()

        plan1 = Plans(name=u"Free");
        plan2 = Plans(name=u"Standard");
        plan3 = Plans(name=u"Advance");
        db.session.add(plan1)
        db.session.add(plan2)
        db.session.add(plan3)
        db.session.commit()

        company1 = Companies(name="Company 1", email="a1@gmail.com", phone="123456789", address="address", plan_id=plan1.id);
        company2 = Companies(name="Company 2", email="a1@gmail.com", phone="123456789", address="address", plan_id=plan2.id);
        company1.plan_id = plan1.id
        company2.plan_id = plan2.id
        db.session.add(company1)
        db.session.add(company2)
        db.session.commit()

        address1 = Addresses(name="address 1", address=" 12 Khuat duy tien");
        address2 = Addresses(name="address 2", address=" 12 Khuat duy tien 2");
        db.session.add(address1)
        db.session.add(address2)
        db.session.commit()

        camera1 = Cameras(udid="id 1", company_id=1, address_id = 1, time=datetime.now(), version = 0);
        camera2 = Cameras(udid="id 2", company_id=1, address_id = 1, time=datetime.now(), version = 0);
        db.session.add(camera1)
        db.session.add(camera2)
        db.session.commit()

    print("build_sample_db done")
    return

# provide login manager with load_user callback
@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def align_face(img, landmarks, crop_size=112):
    """Align face on the photo
    
    Arguments:
        img {PIL.Image} -- Image with face
        landmarks {np.array} -- Key points
    
    Keyword Arguments:
        crop_size {int} -- Size of face (default: {112})
    
    Returns:
        PIL.Image -- Aligned face
    """
    facial5points = [[landmarks[j], landmarks[j + 5]] for j in range(5)]
    warped_face = warp_and_crop_face(np.array(img), facial5points, reference, crop_size=(crop_size, crop_size))
    img_warped = Image.fromarray(warped_face)
    return img_warped

# App main route + generic routing
@app.route('/', defaults={'path': 'index.html'})
@login_required
@user_is("admin")
def index(path):

    date = datetime.now().date()
    absent = Events.query.filter_by(name="Vắng mặt").first()

    absent_count = db.session.query(EventLogs).filter(EventLogs.event_id == absent.id).filter(EventLogs.time <= date + timedelta(days=1)).filter(EventLogs.time >= date).count()

    users = db.session.query(User).join(User.roles).filter(User.company_id == current_user.company_id).filter(User.is_unknown == False).filter(Role.name == "staff").all()

    in_late_count = 0
    out_early_count = 0
    escape_count = 0

    for user in users:
        address_start, h_start, start = db.session.query(Addresses, Histories, func.min(Histories.time)).join(Cameras, Cameras.id==Histories.camera).join(Addresses, Cameras.address_id==Addresses.id).filter(Histories.user_id == user.id).filter(Histories.time <= date + timedelta(days=1)).filter(Histories.time >= date).first()
        
        address_end, h_end, end = db.session.query(Addresses, Histories, func.max(Histories.time)).join(Cameras, Cameras.id==Histories.camera).join(Addresses, Cameras.address_id==Addresses.id).filter(Histories.user_id == user.id).filter(Histories.time <= date + timedelta(days=1)).filter(Histories.time >= date).first()
        if address_start and start and address_start.start and address_start.start < start.time():
            in_late_count = in_late_count + 1
           
        if address_start and end and address_start.end and address_start.end > end.time():
            out_early_count = out_early_count + 1

        if not start:
            escape_count = escape_count + 1

    if current_user.has_roles("superuser"):
        camera_num = db.session.query(Cameras).count()
        history_num = db.session.query(Histories).join(Cameras, Cameras.id == Histories.camera).count()
        user_num = db.session.query(User).filter(User.is_unknown == False).count()
        company_num = db.session.query(Companies).count()
        return render_template( 'pages/index.html', camera_num=camera_num, history_num=history_num, user_num=user_num, company_num=company_num, escape_count=escape_count, in_late_count=in_late_count, out_early_count=out_early_count, absent_count=absent_count )
    elif current_user.has_roles("admin"):
        camera_num = db.session.query(Cameras).filter(Cameras.company_id == current_user.company_id).count()
        history_num = db.session.query(Histories).join(Cameras, Cameras.id == Histories.camera).join(User, Histories.user_id == User.id).filter(User.company_id == current_user.company_id).count()
        user_num = db.session.query(User).join(User.roles).filter(User.company_id == current_user.company_id).filter(Role.name == "user").filter(User.is_unknown == False).count()
        staff_num = db.session.query(User).join(User.roles).filter(User.company_id == current_user.company_id).filter(Role.name == "staff").filter(User.is_unknown == False).count()
        return render_template( 'pages/index.html', camera_num=camera_num, history_num=history_num, user_num=user_num, staff_num=staff_num, escape_count=escape_count, in_late_count=in_late_count, out_early_count=out_early_count, absent_count=absent_count )
    else:
        return render_template( 'pages/permission_denied.html')

@app.route('/<path>')
@login_required
@user_is("admin")
def custom(path):
    try:
        # try to match the pages defined in -> pages/<input file>
        return render_template( 'pages/'+path )
    except:
        return render_template( 'pages/error-404.html' )

# Return sitemap 
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'sitemap.xml')

language = 'vi_VN'

@babel.localeselector
def get_locale():
	if language != '':
		return language
	# will return language code (en/es/etc).
	return request.accept_languages.best_match(Config.LANGUAGES.keys())
	
@app.route('/translate', methods=['POST'])
def translate():
	lang = request.get_json()
	globals()['language'] = lang['lang']
	get_locale()
	return ''