#!/usr/bin/env python
import os
import json as js
import sqlite3
import os.path
import shutil, sys
from datetime import timedelta
import calendar

from flask            import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login      import LoginManager
from flask_bcrypt     import Bcrypt
from flask_mail 	  import Mail
from flask_cors 	  import CORS
from flask_socketio   import SocketIO, emit, join_room, leave_room
from flask_babel import Babel
from flask_migrate import Migrate
from flask_jwt import JWT
from flask_bcrypt import Bcrypt

from rq import Queue
from rq.job import Job
from worker import conn

# import cronjob
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
from tasks import send_notification, sent_event_webhook

# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))
feature_db_path = os.path.join(basedir, 'static/db/')

class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        scheme = environ.get('HTTP_X_FORWARDED_PROTO')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


app = Flask(__name__)
app.wsgi_app = ReverseProxied(app.wsgi_app)

app.config.from_object('configuration.Config')
app.config['file_allowed'] = ['image/png', 'image/jpeg', 'application/octet-stream']
app.config['JWT_EXPIRATION_DELTA'] = timedelta(days=365)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
mail_settings = {
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": 'mq.dev1@mqsolutions.com.vn',
    "MAIL_PASSWORD": '123456789'
}

app.config.update(mail_settings)
db = SQLAlchemy(app) # flask-sqlalchemy
bc = Bcrypt(app) # flask-bcrypt
mail = Mail(app)
lm = LoginManager(   ) # flask-loginmanager
lm.init_app(app) # init the login manager
babel = Babel(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
q = Queue(connection=conn)
# create schedule for printing time
scheduler = BackgroundScheduler()

socketio = SocketIO(app)


CORS(app, supports_credentials=True, allow_headers=['Content-Type', 'X-ACCESS_TOKEN', 'Authorization'])

# Setup database
@app.before_first_request
def initialize_database():
    db.create_all()

# Import routing, models and Start the App
from views import *
from models import *
from api import *

def authenticate(username, password):
    user = User.query.filter(User.user == username).first()

    if user:
        if (user.has_roles("admin") or user.has_roles("superuser")):
            if user.company_id and bcrypt.check_password_hash(user.password, password):
                return user

def identify(payload):
    return User.query.filter(User.id == payload['identity']).scalar()


jwt = JWT(app, authenticate, identify)



def insertFeatureToDB(name, feature, company_id):
    #print("insertFeatureToDB")
    db_path = feature_db_path + company_id + ".db"
    if not os.path.isfile(db_path):
    	db_o_path = feature_db_path + "mq_feature_empty.db"
    	shutil.copy2(db_o_path, db_path)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
      c.execute('''INSERT INTO Features (name, data) VALUES (?, ?)''', (name, feature,))
    except sqlite3.IntegrityError as e:
      print('Insert feature errror: ', e.args[0]) # column name is not unique
    conn.commit()

    conn.close()


# When the client emits 'connection', this listens and executes
@socketio.on('status', namespace='/camera')
def camera_connected(data):
    print ('Camera connected:', data)
    status = js.loads(data)
    if not 'version' in status:
        status['version'] = 0
    cam = db.session.query(Cameras).filter(Cameras.udid == status['udid']).first()
    if cam != None:
        db.session.query(Cameras).filter(Cameras.udid == status['udid']).update({"ipaddr": status['ip_address'], "time": datetime.now(), "version": status['version']}, synchronize_session='fetch')
    else:
        cam = Cameras(udid=status['udid'], version= status['version'], ipaddr=status['ip_address'], time=datetime.now());
        db.session.add(cam)

    db.session.commit()
    print("===============camera joined: " + status['ip_address'])
    if cam.company_id:
        room = session.get(str(cam.company_id))
        join_room(room)
    else:
        room = session.get("camera_global")
        join_room(room)

# When the client emits 'new message', this listens and executes
@socketio.on('new face', namespace='/camera')
def new_face(data):
    #print ('New face:', data)
    feature_data = js.loads(data)
    if feature_data and feature_data['udid']:
        cam = db.session.query(Cameras).filter(Cameras.udid == feature_data['udid']).first()
        if cam and cam.company_id:
            insertFeatureToDB(feature_data['name'], feature_data['feature'], str(cam.company_id))
            room = session.get(str(cam.company_id))
            emit('feature', { 'data' :  data }, room=room )

def coordinates(time):
    timeLists = ["08:00:00-10:00:00","10:00:00-12:00:00","12:00:00-14:00:00","14:00:00-16:00:00","16:00:00-18:00:00"]
    for item in timeLists:
        start, end = item.split("-")
        start = datetime.strptime(start,'%H:%M:%S').time()
        end = datetime.strptime(end,'%H:%M:%S').time()
        if start <= time.time() and time.time() <= end: 
            return timeLists.index(item), time.weekday()

def cron_job():
    startSchudule = datetime.strptime("8:00:00",'%H:%M:%S').time()
    endSchudule = datetime.strptime("18:00:00",'%H:%M:%S').time()
    date = datetime.now()
    if startSchudule <= date.time() and date.time() <= endSchudule: 
        print("BẮT ĐẦU KIỂM TRA HÀNH CHÍNH CÔNG ====")
        now = date.strftime('%H:%M:%S')
        users = db.session.query(User).join(User.roles).filter(Role.name == "staff")
        last_time = date - timedelta(minutes=10)
        absent = Events.query.filter_by(id=1).first()
        for user in users:
            if user.permissions:
                permissionsUser = eval(user.permissions)
                if permissionsUser:
                    x, y = coordinates(date)
                    for address_id in permissionsUser:
                        permission = permissionsUser[address_id]
                        schedule = permission['schedule']
                        if schedule[x][y]:
                            address = Addresses.query.filter_by(id=address_id).first()
                            cameras = Cameras.query.filter_by(address_id=address_id).all()
                            listCameras = []
                            for camera in cameras:
                                listCameras.append(camera.id)
                            if listCameras == []:
                                print("There is no camera in the room {}".format(address.name))
                            else:
                                history = db.session.query(Histories).filter(Histories.user_id == user.id).filter(Histories.time >= last_time).filter(Histories.camera.in_(listCameras)).count()
                                if not history:
                                    company = Companies.query.filter_by(id=user.company_id).first()
                                    link = company.secret
                                    userdata = {}
                                    userdata['user_name'] = user.full_name
                                    data = {
                                        "address_id": address_id,
                                        "event_name": absent.name,
                                        "file_name" : "static/assets/img/escape.jpeg",
                                        "time"      : date.timestamp(),
                                        "data"      : userdata
                                    }
                                    job = q.enqueue_call(
                                        func=sent_event_webhook, args=(link, absent.id, data), result_ttl=5000
                                    )
                                    job = q.enqueue_call(
                                        func=send_notification, args=(user.to_dict(), permission['addressName'], date), result_ttl=5000
                                    )
                                    event_log = EventLogs(user_id=user.id, event_id=absent.id, time=date, camera_id=listCameras[0], address_id=address_id, image="static/assets/img/escape.jpeg")
                                    db.session.add(event_log)
                                    db.session.commit()
                    

if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=3456, debug=True)
    print("STARTING =====")
    scheduler.start()
    scheduler.add_job(
        func=cron_job,
        trigger=IntervalTrigger(minutes=10),
        # trigger=IntervalTrigger(seconds=10),
        id='cron_job',
        replace_existing=True
    )
    atexit.register(lambda: scheduler.shutdown())
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
