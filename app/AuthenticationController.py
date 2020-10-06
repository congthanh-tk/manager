# import Base Controller
from BaseController import *

# Register a new user
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    
    # declare the Registration Form
    form = RegisterForm(request.form)
    msg = None
    if request.method == 'GET': 

        return render_template( 'pages/register.html', form=form, msg=msg )

    # check if both http method is POST and form is valid on submit
    if form.validate_on_submit():

        # assign form data to variables
        username = request.form.get('username', '', type=str)
        password = request.form.get('password', '', type=str) 
        email    = request.form.get('email'   , '', type=str) 

        # filter User out of database through username
        user = User.query.filter_by(user=username).first()

        # filter User out of database through username
        user_by_email = User.query.filter_by(email=email).first()

        if user or user_by_email:
            msg = 'Error: User exists!'
        
        else:         

            pw_hash = bc.generate_password_hash(password)

            user = User(username, email, pw_hash)

            user.save()

            msg = 'User created, please <a href="' + url_for('login',_external=True,_scheme=request.scheme) + '">login</a>'     

    else:
        msg = 'Input error'     

    return render_template( 'pages/register.html', form=form, msg=msg )

# Logout user
@app.route('/logout.html')
def logout():
    logout_user()
    return redirect(url_for('index',_external=True,_scheme=request.scheme))

# Authenticate user
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    
    # Declare the login form
    form = LoginForm(request.form)
    data = (request.form).to_dict(flat=False)
    # Flask message injected into the page, in case of any errors
    msg = None

    # check if both http method is POST and form is valid on submit
    if data:

        # assign form data to variables
        username = request.form.get('user', '', type=str)
        print(username)
        password = request.form.get('pass', '', type=str)
        print(password)

        # filter User out of database through username
        user = User.query.filter_by(user=username).first()
        if user:
            
            if user.password and bc.check_password_hash(user.password, password):
                print(type(user))
                login_user(user)
                print("=========>>>>>")
                pprint(vars(current_user))
                if (current_user.has_roles("staff")):
                    return redirect(url_for('profile',_external=True,_scheme=request.scheme))
                return redirect(url_for('index',_external=True,_scheme=request.scheme))
            else:
                msg = u"Mật khẩu sai! hãy thử lại."
        else:
            msg = u"Người dùng không tồn tại"

    return render_template( 'pages/login.html', form=form, msg=msg )

@app.route('/login-sso')
def login_sso():
    print(request.args)
    ticket = request.args.get('ticket')
    url = 'https://dangnhap.hanhchinhcong.com.vn/p3/serviceValidate?ticket={}&service=https://camera-chinhcong.test.mqsolutions.vn/login-sso'.format(ticket)
    test = requests.get(url)
    print(test)
    soup = BeautifulSoup(test.content)
    print(soup)
    if soup.find('cas:authenticationsuccess')!=None:
        print("login ok")
        username = soup.find('cas:user').string
        user = User.query.filter_by(user=username).first()
        if not user:
            pw_hash = bc.generate_password_hash("123456")
            user = User(user=username, is_unknown=False, company_id=6, password=pw_hash, confirmed_at=datetime.now())
            user_role = db.session.query(Role).filter_by(name="admin").first()
            user.roles = []
            user.roles.append(user_role)
            db.session.add(user)
            db.session.commit()

        login_user(user)
    else:
        print("login nok")
    return redirect(url_for('index',_external=True,_scheme=request.scheme))