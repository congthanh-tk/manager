# import Base Controller
from BaseController import *

@app.route('/history_data_list', methods=['GET'])
@login_required
@user_is("admin")
def history_data_list():
    """Return server side data."""
    # defining columns
    page = int(request.args.get('page'))
    size = int(request.args.get('size'))
    type = int(request.args.get('type'))
    startTime = request.args.get('startTime')
    endTime = request.args.get('endTime')
    query = (db.session.query(Histories, Cameras, User, Faces)
            .join(Cameras).join(User).outerjoin(Faces).outerjoin(User.roles)
            .filter(Cameras.company_id == current_user.company_id)
            .filter(User.company_id == current_user.company_id))
    
    if type == 1:
        query = query.filter(User.is_unknown == False)
    elif type == 2:
        query = query.filter(User.is_unknown == True)

    if  startTime:
        query = query.filter(Histories.time >= datetime.strptime(startTime, "%Y-%m-%d %H:%M" ))
    if endTime:
        query = query.filter(Histories.time <= datetime.strptime(endTime, "%Y-%m-%d %H:%M"))

    histories = (query.group_by(Histories.time)
                .order_by(Histories.time.desc())
                .offset(page*size).limit(size).all())
    return render_template('pages/history_list.html', histories=histories)


@app.route('/history.html')
@login_required
@user_is("admin")
def history_data():
    return render_template( 'pages/history.html')