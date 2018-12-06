from flask import Flask, render_template, request
from validate_email import validate_email
import MySQLdb
import hashlib


app = Flask(__name__)

#Initialize MySQL connection information
config = {
    'host' : "localhost",
    'user' : "root",
    'passwd' : "",
    'db' : "XXXX"
}

@app.route('/', methods=['GET','POST'])
def login_page():
  
    cnx = MySQLdb.connect(**config)
    cur = cnx.cursor()

    #Comparing input and items in MySQL
    if request.method == 'POST':

        #Stores input email address into String
        inp_usrn = request.form['email address'].lower()

        #Comparing email addresses
        if db_has(inp_usrn):

            #Stores input password into String
            inp_pswd = request.form['password']

            #Hashes input password using SHA224
            hash_obj = hashlib.sha224(inp_pswd).hexdigest()

            #Extract the password from MySQL
            cur.execute("SELECT pswd FROM users WHERE email = '%s'" %(inp_usrn))
            cnx.close()
            get_pswd = ""
            for row in cur:
                get_pswd += row[0]

            #Hexdigest the has object and compares it to database's password
            if hash_obj == get_pswd:
                return render_template("main.html", user = inp_usrn, admin = ("example@example.com"==inp_usrn))
    return render_template("login.html")

@app.route('/signup',methods=['GET','POST'])
def sign_up():
    
    cnx = MySQLdb.connect(**config)
    cur = cnx.cursor()
    
    if request.method == 'POST':
        
        #Get password from the forms in createaccount.html using Flask request
        create_usr = request.form['email address'].lower()
        create_pswd = request.form['password']
        
        #Creating account and checking if email address is valid and has a SMTP Server
        if not db_has(create_usr) and validate_email(create_usr,verify=True):
            cur.execute("INSERT INTO `users` (`email`,`pswd`) VALUES ('%s', SHA2('%s',224));" %(create_usr,create_pswd))
            cnx.commit()
            cnx.close()
            return render_template("createaccount.html", text = "Account Created!")

    return render_template("createaccount.html")

#Checks if input emailaddress is in the database
def db_has(ea.cur):
    #Extracts the username from MySQL (if applicable)
    cur.execute("SELECT email FROM users WHERE email = '%s'" %(ea))
    get_usrn = ""
    for row in cur:
        get_usrn += row[0]
    if get_usrn == ea:
        return True
    return False
