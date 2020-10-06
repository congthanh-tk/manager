from flask import jsonify, json
from pprint import pprint
import requests
from datetime import datetime, timedelta
from configuration import Config

def sent_event_webhook(link, event_id, data):
    # print(link, event_name, data)
    r = requests.post(link, json={"event_id":event_id, "data": json.dumps(data)})
    # pprint(vars(r)) 
    return 1

def send_message(phone, message):
    r = requests.post('https://zalo.ngochip.net/api/v1/zalo', json={
        "phone": phone,
        "message": message,
        "uuid": "9aab0a03-5d83-41d3-8c37-cc8f179ccf1a-16c70872199c554dad8b417b7ce8f355",
        "cookie": "_ga=GA1.3.1994378991.1584963689;_gid=GA1.3.584409619.1594695644;zpw_sek=lHWX.261329837.a0.fO_BWQnUyGW1pM87ZLxn2DTyb6EEPDDSoccmIjzkks3SEyPzposWUFmymatjOymgqL0Psgya9IvBNnmeeG7Hs0;zpw_sekm=c_Uu.261329837.1.8jJGA0fhLo6d-CGk1sjN8NyOCbCuNMOIE59l4Zrbl_C94OC7xMgw0GSqLo4;__zi=3000.SSZzejyD6zOgdh2mtnLQWYQN_RAG01ICFjIXe9fEM8uucEwWbKTOYtsHwAxTG5I7S9Rfh3aq.1;__zi-legacy=3000.SSZzejyD6zOgdh2mtnLQWYQN_RAG01ICFjIXe9fEM8uucEwWbKTOYtsHwAxTG5I7S9Rfh3aq.1;_ga=GA1.2.1994378991.1584963689;_gid=GA1.2.584409619.1594695644;_zlang=vn;app.event.zalo.me=1237256340829804450;fpsend=147657;zpsid=ceEU.261329837.1.NXwBiZ-qOlwI9_7nCxHY_ah74Cm9XL7C1enHoJ5SiFrBWmwsFbb2ys2qOlu;zpsidleg=ceEU.261329837.1.NXwBiZ-qOlwI9_7nCxHY_ah74Cm9XL7C1enHoJ5SiFrBWmwsFbb2ys2qOlu;"
    })
    return r

def send_notification(user, address, time):
    message = "Nhân viên {} vắng mặt trong buổi tiếp dân tại {} trong khoảng thời gian từ {} đến {}".format(user["full_name"], address, (time - timedelta(minutes=10)).strftime('%H:%M:%S ngày %d-%m-%Y'), time.strftime('%H:%M:%S ngày %d-%m-%Y'))
    print(message)
    send_message(Config.company_phone, message)
    return 1
