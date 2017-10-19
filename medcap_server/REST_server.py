#!flask/bin/python
import thread
from flask import Flask, jsonify, abort, request, make_response, url_for
from flask.ext.httpauth import HTTPBasicAuth
from flask.ext.cors import CORS
import sqlite3
import json
import random  
from random import randint
import string
import datetime
import boto.dynamodb
import boto.sqs
from boto.sqs.message import Message
import cPickle as pickle
from time import sleep
import time
import datetime
import jwt
import numpy
import pandas
from pandas.tools.plotting import scatter_matrix
import matplotlib.pyplot as plt
from sklearn import model_selection
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC

THRESH_DIA_LOW = int(50)
THRESH_CORE_HIGH = float(104)
THRESH_HEAT_HIGH = float(115)
BP_CALC_WEIGHT = float(0.4)
CORE_CALC_WEIGHT = float(0.4)
HEAT_CALC_WEIGHT = float(0.2)

# Spot Check Algorithms
models = []
models.append(('LR', LogisticRegression()))
models.append(('KNN', KNeighborsClassifier()))
models.append(('CART', DecisionTreeClassifier()))
models.append(('NB', GaussianNB()))
models.append(('SVM', SVC()))
# evaluate each model in turn

# Load dataset
url = "mimic.csv"
names = ['PEAKTIME','TROUGHTIME','PLETH','ABP']
dataset = pandas.read_csv(url, names=names, usecols=['PEAKTIME','TROUGHTIME','PLETH','ABP'])

# Split-out validation dataset
array = dataset.values
X = array[:,0:len(names)-1]
Y = array[:,len(names)-1]
validation_size = 0.30
seed = 7
X_train, X_validation, Y_train, Y_validation = model_selection.train_test_split(X, Y, test_size=validation_size, random_state=seed)

# Test options and evaluation metric
seed = 7
scoring = 'accuracy'

# Make predictions on validation dataset
decision_tree = DecisionTreeClassifier()
decision_tree.fit(X_train, Y_train)
predictions = decision_tree.predict(X_validation)

app = Flask(__name__, static_url_path="")
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
auth = HTTPBasicAuth()

ACCESS_KEY=""
SECRET_KEY=""
JWT_KEY=""
REGION = ""

invalid_credentials = 'Invalid credentials'
queue_not_created = 'Server error: Queue not created, contact MedCap Support'
queue_not_deleted = 'Server error: Queue not deleted, contact MedCap Support'
precondition_failed = 'Input requirements not satisfied: precondiion failed'
user_nonexistent = 'User does not exist'
user_exists = 'User already exists'
user_logged_in = 'User already logged in'
user_not_logged_in = 'User not logged in'
queue_exists = 'Queue already exists. Contact MedCap Support'
queue_nonexistent = 'Queue not found. Contact MedCap Support'
message_not_deleted = 'Message not deleted. Contact MedCap Support'
wait_for_queue = 'Please wait 60 seconds before logging in again'

no_new_data = 'No new data'

conn_sqs = boto.sqs.connect_to_region(REGION,aws_access_key_id=ACCESS_KEY,aws_secret_access_key=SECRET_KEY)

sessions = {}

conn_dynamo = boto.dynamodb.connect_to_region(REGION,aws_access_key_id=ACCESS_KEY,aws_secret_access_key=SECRET_KEY)
userinfo_table = conn_dynamo.get_table('userinfo')

users = {"<user>":"<pass>"}


def eval_diastolic(data):
    #data should be [systolic_upstroke,diastolic_time,ppg_voltage]
    test_data = numpy.array([data])
    prediction = decision_tree.predict(test_data)
    return prediction[0]


@auth.get_password
def get_password(username):
    if username in users:
        return users.get(username)
    return None

@auth.error_handler
def unauthorized():
    #print "Need api access"
    return make_response('Unauthorized access', 401)
  
  
@app.errorhandler(400)
def bad_request(error):
    return make_response('Bad request', 400)


@app.errorhandler(404)
def not_found(error):
    return make_response('Not found', 404)

@app.route('/api/testaccess', methods=['GET','POST'])
#@auth.login_required
def testaccess():

	request_headers = request.headers;
	#print request_headers
	return make_response('OK', 200)

@app.route('/api/adduser', methods=['GET','POST'])
@auth.login_required
def add_user():
    request_data = request.get_json();

    try:
        request_data = jwt.decode(request_data,JWT_KEY)
    except:
        return make_response(precondition_failed, 412)

    if 'username' in request_data and 'firstname' in request_data and 'lastname' in request_data and 'email' in request_data and 'password' in request_data and 'age' in request_data and 'weight' in request_data and 'jwt_seq' in request_data:

        '''Add user to database
           Return username in jwt and sequence number (convention for session is  {username,sequence_num}
           Sequence_num initiated by app at 0. Returns 1 when user created and session is created.
           Active sessions kept track in global list. Used for after user creation and user login.
           Need to make login and logout handles'''

        if request_data['jwt_seq'] == 0:

            result = userinfo_table.scan()

            found = False

            for item in result:
                if item['username'] == request_data['username']:
                    found = True

            if found:
                return make_response(user_exists, 400)

            item_data = {
                    'username': str(request_data['username']),
                    'firstname': str(request_data['firstname']),
                    'lastname': str(request_data['lastname']),
                    'email': str(request_data['email']),
                    'password': str(request_data['password']),
                    'age': int(request_data['age']),
                    'weight': int(request_data['weight'])
            }
            item = userinfo_table.new_item(attrs=item_data)
            item.put()
            sessions[request_data['username']] = 1
            data = jwt.encode({"username":request_data['username'],"jwt_seq":1},JWT_KEY, algorithm='HS256')
            client_send_queue = conn_sqs.create_queue('%s_send' % request_data['username'])
            client_recv_queue = conn_sqs.create_queue('%s_recv' % request_data['username'])

	    table_schema = conn_dynamo.create_schema(hash_key_name='timestamp',hash_key_proto_value=str,range_key_name='core_temp',range_key_proto_value=int)
	    table = conn_dynamo.create_table(name='%s_data' % request_data['username'],schema=table_schema,read_units=1,write_units=1)

            if client_send_queue and client_recv_queue:
	            return make_response(data, 201)
	    else:
		    return make_response(queue_not_created, 500)
        else:
            return make_response(invalid_credentials, 401)
    else:
        return make_response(precondition_failed, 412)


@app.route('/api/login', methods=['GET','POST'])
@auth.login_required
def login():
    request_data = request.get_json();

    #print request_data

    try:
        request_data = jwt.decode(request_data,JWT_KEY)
    except:
        return make_response(precondition_failed, 412)

    if 'username' in request_data and 'password' in request_data and 'jwt_seq' in request_data:

        '''See if user is in db and get password
           Return username in jwt and sequence number (convention for session is  {username,sequence_num}
           Sequence_num initiated by app at 0. Returns 1 when user created and session is created.
           
           '''
        # IF user exists and password is correct and jwt_seq is 0

	users = userinfo_table.scan()
	user_found = False
	for user in users:
	    if user['username'] == request_data['username']:
		user_found = True
		userpass = user['password']

	if not user_found:
	    return make_response(user_nonexistent, 404)

	if request_data['username'] in sessions:
	    return make_response(user_logged_in, 400)

	if userpass != request_data['password']:
	    return make_response(invalid_credentials, 401)

        sessions[request_data['username']] = 1
        data = jwt.encode({"username":request_data['username'],"jwt_seq":1},JWT_KEY, algorithm='HS256')

	if conn_sqs.get_queue('%s_send' % request_data['username']) != None or conn_sqs.get_queue('%s_recv' % request_data['username']) != None:
	    return make_response(queue_exists, 500)
        
	try:

            client_send_queue = conn_sqs.create_queue('%s_send' % request_data['username'])
            client_recv_queue = conn_sqs.create_queue('%s_recv' % request_data['username'])

	except:
	    del sessions[request_data['username']]
	    return make_response(wait_for_queue, 400)

        if client_send_queue and client_recv_queue:
            #return make_response(jsonify({'message': 'Login OK.','data':data}), 200)
	    return make_response(data, 200)
        else:
            return make_response(queue_not_created, 500)

    else:
        return make_response(precondition_failed, 412)



@app.route('/api/logout', methods=['GET','POST'])
@auth.login_required
def logout():
    request_data = request.get_json();

    try:
        request_data = jwt.decode(request_data,JWT_KEY)
    except:
        return make_response(precondition_failed, 412)

    #print request_data

    if 'username' in request_data and 'jwt_seq' in request_data:

        '''See if user is in db and get password
           Return username in jwt and sequence number (convention for session is  {username,sequence_num}
           Sequence_num initiated by app at 0. Returns 1 when user created and session is created.

           '''
        # IF user exists and password is correct and jwt_seq is 0

        if request_data['username'] in sessions and request_data['jwt_seq'] == (sessions[request_data['username']] + 1):

            del sessions[request_data['username']]

	    client_send_queue = conn_sqs.get_queue('%s_send' % request_data['username'])
            client_recv_queue = conn_sqs.get_queue('%s_recv' % request_data['username'])

	    if client_send_queue == None or client_recv_queue == None:
		return make_response(queue_nonexistent, 500)
	    deleted_send = conn_sqs.delete_queue(client_send_queue)
            deleted_recv = conn_sqs.delete_queue(client_recv_queue)

	    if deleted_send and deleted_recv:
	        return make_response(jsonify({'message': 'Logout OK.'}), 200)
            else:
		return make_response(queue_not_deleted, 500)

        else:

            return make_response(user_not_logged_in, 401)

    else:
        return make_response(precondition_failed, 412)


@app.route('/api/send', methods=['GET','POST'])
@auth.login_required
def send():
    request_data = request.get_json();

    try:
        request_data = jwt.decode(request_data,JWT_KEY)
    except:
        return make_response(precondition_failed, 412)

    print request_data

    if 'username' in request_data and 'jwt_seq' in request_data and 'data' in request_data and 'heatIdx' in request_data and 'temperature' in request_data and 'humidity' in request_data:

	if request_data['username'] not in sessions:
	    return make_response(user_not_logged_in, 401)

	if request_data['jwt_seq'] == (sessions[request_data['username']] + 1):
	    sessions[request_data['username']] = sessions[request_data['username']] + 2

	    client_send_queue = conn_sqs.get_queue('%s_send' % request_data['username'])

            if client_send_queue == None:
                return make_response(queue_nonexistent, 500)

	    #print request_data

	    sut_arr = []
	    dia_arr = []
	    peak_volt = []
	    core_temp = []

	    if len(request_data['data']) == 0:
		data = jwt.encode({"username":request_data['username'],"jwt_seq":sessions[request_data['username']]},JWT_KEY, algorithm='HS256')
		return make_response(data, 200)
		sut_arr.append(0)
		dia_arr.append(0)
		peak_volt.append(0)
		core_temp.append(0)
	    else:
		for i in range(0,len(request_data['data'])-1):
		    arr_data = request_data['data'][i].split(',')
		    if len(arr_data) < 4:
			continue
		    else:
			if int(arr_data[0])==999 or int(arr_data[1])==999 or int(arr_data[2])==999:
			    continue
			sut_arr.append(int(arr_data[0]))
			dia_arr.append(int(arr_data[1]))
			peak_volt.append(int(arr_data[2]))
			if arr_data[3][0] == "1":
			    core_temp.append(float(arr_data[3]))
			else:
			    core_temp.append(float(arr_data[3])/float(10))

	    if len(sut_arr)==0 or len(dia_arr)==0 or len(peak_volt)==0 or len(core_temp)==0:
		data = jwt.encode({"username":request_data['username'],"jwt_seq":sessions[request_data['username']]},JWT_KEY, algorithm='HS256')
                return make_response(data, 200)

	    tmp_send = {}
	    ts = time.time()
	    tmp_send["timestamp"] = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') 
	    tmp_send["systolic_time"] = float(sum(sut_arr))/float(len(sut_arr))
	    tmp_send["diastolic_time"] = float(sum(dia_arr))/float(len(dia_arr))
	    tmp_send["peak_voltage"] = float(sum(peak_volt))/float(len(peak_volt))
	    tmp_send["core_temp"] = float(sum(core_temp))/float(len(core_temp))
	    tmp_send["heatIdx"] = float(request_data['heatIdx'])
	    tmp_send["temperature"] = float(request_data['temperature'])
	    tmp_send["humidity"] = float(request_data['humidity'])

	    conn_sqs.send_message(client_send_queue,json.dumps(tmp_send))
	
	    data = jwt.encode({"username":request_data['username'],"jwt_seq":sessions[request_data['username']]},JWT_KEY, algorithm='HS256')
	    return make_response(data, 200)
	    
	else:
	    return make_response(user_not_logged_in, 401)

    else:
        return make_response(precondition_failed, 412)


@app.route('/api/receive', methods=['GET','POST'])
@auth.login_required
def receive():
    request_data = request.get_json();

    try:
        request_data = jwt.decode(request_data,JWT_KEY)
    except:
        return make_response(precondition_failed, 412)

    print request_data

    if 'username' in request_data and 'jwt_seq' in request_data:

        if request_data['username'] not in sessions:
            return make_response(user_not_logged_in, 401)

        if request_data['jwt_seq'] == (sessions[request_data['username']] + 1):
            sessions[request_data['username']] = sessions[request_data['username']] + 2

            client_recv_queue = conn_sqs.get_queue('%s_recv' % request_data['username'])

            if client_recv_queue == None:
                return make_response(queue_nonexistent, 500)

            rcvd_message = conn_sqs.receive_message(client_recv_queue,1)
	    if len(rcvd_message) > 0:
                data = jwt.encode({"username":request_data['username'],"jwt_seq":sessions[request_data['username']],"processed_data":rcvd_message[0].get_body()},JWT_KEY, algorithm='HS256')
		message_deleted = conn_sqs.delete_message(client_recv_queue,rcvd_message[0])

                if message_deleted:
                    return make_response(data, 200)
                else:
                    return make_response(message_not_deleted, 500)

	    else:
		data = jwt.encode({"username":request_data['username'],"jwt_seq":sessions[request_data['username']],"processed_data":"None"},JWT_KEY, algorithm='HS256')
                return make_response(data, 200)

        else:
            return make_response(user_not_logged_in, 401)

    else:
        return make_response(precondition_failed, 412)

def run_analytics():
    global THRESH_DIA_LOW
    global THRESH_CORE_HIGH
    global THRESH_HEAT_HIGH
    global BP_CALC_WEIGHT
    global CORE_CALC_WEIGHT
    global HEAT_CALC_WEIGHT
    while (True):
	try:
            for username,seq in sessions.iteritems():
                client_send_queue = conn_sqs.get_queue('%s_send' % username) 
           	client_recv_queue = conn_sqs.get_queue('%s_recv' % username)
           	if client_recv_queue == None or client_send_queue == None:
           	    print "%s has no send or receive queue!" % username
           	    continue
           	else:
           	    data_message = conn_sqs.receive_message(client_send_queue,1)
           	    if len(data_message) > 0:
           	        message_deleted = conn_sqs.delete_message(client_send_queue,data_message[0])
           		if not message_deleted:
           		    print "%s send queue traffic!"
           		    continue
           		else:
           		    ###Storage here
           		    input_metrics = json.loads(data_message[0].get_body())
           		    #print input_metrics
           		    data_table = conn_dynamo.get_table('%s_data' % username)
           		    item = data_table.new_item(attrs=input_metrics)
           		    retval = item.put()
			
			    ###Analytics here
			    sys_time = float(input_metrics['systolic_time'])
			    dia_time = float(input_metrics['diastolic_time'])
			    peak_volt = float(input_metrics['peak_voltage'])
			    core_temp = float(input_metrics['core_temp'])
			    heat_idx = float(input_metrics['heatIdx'])
			    ext_temp = float(input_metrics['temperature'])
			    humidity = float(input_metrics['humidity'])

			    dia_bp = eval_diastolic([sys_time,dia_time,peak_volt])
			    save_dia_bp = dia_bp

			    if (core_temp >= THRESH_CORE_HIGH):
				health_score = 10
			    else:
				dia_bp = dia_bp - THRESH_DIA_LOW
				if dia_bp <= 0:
				    dia_bp_factor = 10
				elif dia_bp <= 5:
				    dia_bp_factor = 7
				elif dia_bp <= 10:
				    dia_bp_factor = 5
				elif dia_bp <= 15:
				    dia_bp_factor = 3
				else:
				    dia_bp_factor = 1
				
				core_temp = THRESH_CORE_HIGH - core_temp

				if core_temp <= 0:
				    core_temp_factor = 10
				elif core_temp <= 0.25:
				    core_temp_factor = 10
				elif core_temp <= 1:
				    core_temp_factor = 9
				elif core_temp <= 2:
				    core_temp_factor = 7
				elif core_temp <= 3:
				    core_temp_factor = 6
				elif core_temp <= 4:
				    core_temp_factor = 4
				elif core_temp <= 5:
				    core_temp_factor = 3
				else:
				    core_temp_factor = 2
			   
				heat_idx = THRESH_HEAT_HIGH - heat_idx

				if heat_idx <= 0:
				    heat_idx_factor = 10
				elif heat_idx < 5:
				    heat_idx_factor = 8
				elif heat_idx < 10:
				    heat_idx_factor = 6
				elif heat_idx < 20:
				    heat_idx_factor = 4
				else:
				    heat_idx_factor = 1

				health_score = float(dia_bp_factor)*BP_CALC_WEIGHT + float(core_temp_factor)*CORE_CALC_WEIGHT + float(heat_idx_factor)*HEAT_CALC_WEIGHT
           		conn_sqs.send_message(client_recv_queue,str(health_score) + ',' + str(float(input_metrics['core_temp'])) + ',' + str(save_dia_bp))
	    sleep(1)
	except:
	    print "Caught change in session state."

if __name__ == '__main__':
    thread.start_new_thread(run_analytics,())
    app.run(host='0.0.0.0',threaded=True,port=5000,debug=False)
