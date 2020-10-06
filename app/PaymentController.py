# import Base Controller
from BaseController import *

@app.route('/payment', methods=['GET','POST'])
def payment():
    if request.method == 'POST':
        # Process input data and build url payment
        order_type = request.form['order_type']
        order_id = request.form['order_id']+ ":" + order_type + ":" + str(datetime.now())
        amount = request.form['amount']
        order_desc = request.form['order_desc']
        bank_code = request.form['bank_code']
        language = request.form['language']
        ipaddr = get_client_ip(request)

        vnp = vnpay()
        vnp.requestData['vnp_Version'] = '2.0.0'
        vnp.requestData['vnp_Command'] = 'pay'
        vnp.requestData['vnp_TmnCode'] = Config.VNPAY_TMN_CODE
        vnp.requestData['vnp_Amount'] = str(100 * int(amount))
        vnp.requestData['vnp_CurrCode'] = 'VND'
        vnp.requestData['vnp_TxnRef'] = order_id
        vnp.requestData['vnp_OrderInfo'] = order_desc
        vnp.requestData['vnp_OrderType'] = order_type
            # Check language, default: vn
        if language and language != '':
            vnp.requestData['vnp_Locale'] = language
        else:
            vnp.requestData['vnp_Locale'] = 'vn'
                # Check bank_code, if bank_code is empty, customer will be selected bank on VNPAY
        if bank_code and bank_code != "":
            vnp.requestData['vnp_BankCode'] = bank_code

        vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')  # 20150410063022
        vnp.requestData['vnp_IpAddr'] = ipaddr
        vnp.requestData['vnp_ReturnUrl'] = Config.VNPAY_RETURN_URL
        vnpay_payment_url = vnp.get_payment_url(Config.VNPAY_PAYMENT_URL, Config.VNPAY_HASH_SECRET_KEY)
        if request.is_xhr:
            # Show VNPAY Popup
            result = jsonify({'code': '00', 'Message': 'Init Success', 'data': vnpay_payment_url})
            return result
        else:
            # Redirect to VNPAY
            return redirect(vnpay_payment_url)

@app.route('/payment_return', methods=['GET','POST'])
def payment_return():
    inputData = request.args
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.to_dict()
        order_id = inputData['vnp_TxnRef']
        amount = int(inputData['vnp_Amount']) / 100
        order_desc = inputData['vnp_OrderInfo']
        vnp_TransactionNo = inputData['vnp_TransactionNo']
        vnp_ResponseCode = inputData['vnp_ResponseCode']
        vnp_TmnCode = inputData['vnp_TmnCode']
        vnp_PayDate = inputData['vnp_PayDate']
        vnp_BankCode = inputData['vnp_BankCode']
        vnp_CardType = inputData['vnp_CardType']
        if vnp.validate_response(Config.VNPAY_HASH_SECRET_KEY):
            if vnp_ResponseCode == '00':
                com = Companies.query.filter_by(id=current_user.company_id).first()
                if 'Basic package' in order_desc or 'Gói tiêu chuẩn' in order_desc:
                    com.plan_id = 2
                    db.session.commit()
                if 'Advanced package' in order_desc or 'Gói nâng cao' in order_desc:
                    com.plan_id = 3
                    db.session.commit()
                return render_template( 'pages/payment_return.html', title="Kết quả thanh toán",
                                                               result= "Thành công", order_id= order_id,
                                                               amount= amount,
                                                               order_desc= order_desc,
                                                               vnp_TransactionNo= vnp_TransactionNo,
                                                               vnp_ResponseCode= vnp_ResponseCode)
            else: 
                return render_template( 'pages/payment_return.html', title= "Kết quả thanh toán",
                                                               result= "Lỗi", order_id= order_id,
                                                               amount= amount,
                                                               order_desc= order_desc,
                                                               vnp_TransactionNo= vnp_TransactionNo,
                                                               vnp_ResponseCode= vnp_ResponseCode)
        else:
            return render_template('pages/payment_return.html',
                          title= "Kết quả thanh toán", result= "Lỗi", order_id= order_id, amount= amount,
                           order_desc= order_desc, vnp_TransactionNo= vnp_TransactionNo,
                           vnp_ResponseCode= vnp_ResponseCode, msg= "Sai checksum")
    else:
        return render_template(request, "payment_return.html", {"title": "Kết quả thanh toán", "result": ""})

@app.route('/get_client_ip', methods=['GET','POST'])
def get_client_ip(self):
    if 'HTTP_X_FORWARDED_FOR' in self.environ:
        ip = self.environ['HTTP_X_FORWARDED_FOR'].split(',')
    elif 'REMOTE_ADDR' in self.environ:
        ip = self.environ['REMOTE_ADDR']
    return ip

@app.route('/update-package.html', methods=['GET','POST'])
def update_package():
    com = Companies.query.filter_by(id=current_user.company_id).first()
    return render_template( 'pages/update-package.html', com=com)