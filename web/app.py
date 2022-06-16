from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import json, bcrypt1

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.BankApi
users = db["Users"]

class Root(Resource):
    def post(self):
        # postedData = request.get_json()
        postedData = json.loads( str(request.data).replace('"',"'").replace('\\n','').replace("\\'","'").replace("'",'"')[2:-1] )
        return jsonify(postedData)

def UserExists(username):
    return users.count_documents({'Username': username}) > 0

class Register(Resource):
    def post(self):
        # postedData = request.get_json()
        postedData = json.loads( str(request.data).replace('"',"'").replace('\\n','').replace("\\'","'").replace("'",'"')[2:-1] )

        username = postedData['username']
        password = postedData['password']

        if UserExists(username):
            return jsonify({ 'status': 301, 'msg': "Invalid Username" })
        if len(password) < 3:
            return jsonify({ 'status': 302, 'msg': "Invalid Password" })

        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        users.insert_one({ 'Username': username, 'Password': hashed_pw, 'Own': 0, 'Debt': 0 })

        # return jsonify({ 'username': username, 'password': password, 'hashed_pw': str(hashed_pw)[2:-1] })
        return jsonify({ 'status': 200, 'msg': "You successfully signed up for this API" })

def cashWithUser(username):
    return users.find({'Username': username})[0]['Own']
def debtWithUser(username):
    return users.find({'Username': username})[0]['Debt']

def generateReturnDict(status, msg):
    return {'status': status, 'msg': msg}

def verify_password(username, password):
    if not UserExists(username): return False
    hashed = users.find({'Username': username})[0]['Password']
    return bcrypt.hashpw(password.encode('utf8'), hashed) == hashed
# ErrorDictionary, True/False
def verify_credentials(username, password):
    if not UserExists(username):
        return generateReturnDict(301, "Invalid Username"), True
    if not verify_password(username, password):
        return generateReturnDict(302, "Incorrect Password"), True
    return None, False

def updateAccount(username, balance):
    users.update_one({'Username': username}, {"$set": {'Own': balance}})
def updateDebt(username, balance):
    users.update_one({'Username': username}, {"$set": {'Debt': balance}})

class Add(Resource):
    def post(self):
        # postedData = request.get_json()
        postedData = json.loads( str(request.data).replace('"',"'").replace('\\n','').replace("\\'","'").replace("'",'"')[2:-1] )

        username = postedData['username']
        password = postedData['password']
        money = postedData['amount']
        if money <= 1:
            return jsonify(generateReturnDict(304, "The money entered must be > 1"))

        retJson, error = verify_credentials(username, password)
        if error: return jsonify(retJson)

        cash = cashWithUser(username)
        bank_cash = cashWithUser("BANK")
        updateAccount("BANK", bank_cash + 1)
        updateAccount(username, cash + money - 1)

        return jsonify(generateReturnDict(200, "Amount added successfully to account"))

class Transfer(Resource):
    def post(self):
        # postedData = request.get_json()
        postedData = json.loads( str(request.data).replace('"',"'").replace('\\n','').replace("\\'","'").replace("'",'"')[2:-1] )

        username = postedData['username']
        password = postedData['password']
        to       = postedData['to']
        money    = postedData['amount']
        if money <= 1:
            return jsonify(generateReturnDict(304, "The money entered must be > 1"))

        retJson, error = verify_credentials(username, password)
        if error: return jsonify(retJson)

        cash = cashWithUser(username)
        if cash <= money:
            return jsonify(generateReturnDict(304, "You don't have enough money, please add or take a loan"))
        if not UserExists(to):
            return jsonify(generateReturnDict(301, "Receiver username is invalid"))
        cash_to = cashWithUser(to)
        cash_bank = cashWithUser("BANK")
        updateAccount("BANK", cash_bank + 1)
        updateAccount(to, cash_to + money - 1)
        updateAccount(username, cash - money)

        return jsonify(generateReturnDict(200, "Amount transferred successfully"))

class Balance(Resource):
    def post(self):
        # postedData = request.get_json()
        postedData = json.loads( str(request.data).replace('"',"'").replace('\\n','').replace("\\'","'").replace("'",'"')[2:-1] )

        username = postedData['username']
        password = postedData['password']

        retJson, error = verify_credentials(username, password)
        if error: return jsonify(retJson)

        retJson = users.find_one({'Username': username}, {'_id': 0, 'Password': 0})
        return jsonify(retJson)
        # return jsonify(generateReturnDict(200, str(type(retJson))))

class TakeLoan(Resource):
    def post(self):
        # postedData = request.get_json()
        postedData = json.loads( str(request.data).replace('"',"'").replace('\\n','').replace("\\'","'").replace("'",'"')[2:-1] )

        username = postedData['username']
        password = postedData['password']
        money    = postedData['amount']
        if money < 0:
            return jsonify(generateReturnDict(304, "The money entered must be > 0"))

        retJson, error = verify_credentials(username, password)
        if error: return jsonify(retJson)

        cash = cashWithUser(username)
        debt = debtWithUser(username)

        updateAccount(username, cash + money)
        updateDebt(username, debt + money)

        return jsonify(generateReturnDict(200, "Loan added to your account"))

class PayLoan(Resource):
    def post(self):
        # postedData = request.get_json()
        postedData = json.loads( str(request.data).replace('"',"'").replace('\\n','').replace("\\'","'").replace("'",'"')[2:-1] )

        username = postedData['username']
        password = postedData['password']
        money    = postedData['amount']
        if money < 0:
            return jsonify(generateReturnDict(304, "The money entered must be > 0"))

        retJson, error = verify_credentials(username, password)
        if error: return jsonify(retJson)

        cash = cashWithUser(username)
        if cash <= money:
            return jsonify(generateReturnDict(303, "Not enough cash in your account"))
        debt = debtWithUser(username)

        updateAccount(username, cash - money)
        updateDebt(username, debt - money)

        return jsonify(generateReturnDict(200, "You've successfully paid your loan"))

api.add_resource(Root, '/')
api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(TakeLoan, '/takeloan')
api.add_resource(PayLoan, '/payloan')

print("__name__:", __name__)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
