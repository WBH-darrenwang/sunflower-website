from flask import Flask, render_template, request
from validate_email import validate_email
import MySQLdb
import hashlib
import smtplib
from random import randint, choice
import string


app = Flask(__name__)

#Initialize MySQL connection information
config = {
    'host' : "localhost",
    'user' : "root",
    'passwd' : "",
    'db' : "XXXX"
}

bot_user = "example@gmail.com"
bot_pwd = "XXXX"

@app.route('/', methods=['GET','POST'])
def login_page():

    cnx = MySQLdb.connect(**config)
    cur = cnx.cursor()
    invalid_inp = False

    #Comparing input and items in MySQL
    if request.method == 'POST':

        #Stores input email address into String
        inp_usrn = request.form['email address'].lower()

        #Comparing email addresses
        if (db_has(inp_usrn,cur,"email",inp_usrn)):

            #Stores input password into String
            inp_pswd = request.form['password']

            #Hashes input password using SHA224
            hash_obj = hashlib.sha224(inp_pswd).hexdigest()

            #Extract the password from MySQL
            get_pswd = db_get(inp_usrn,cur,"pswd")

            #Hexdigest the has object and compares it to database's password
            if (hash_obj == get_pswd) or (db_get(inp_usrn,cur,"temp_pwd") == hash_obj):
                if not db_has(inp_usrn,cur,"temp_pwd",None):
                    cur.execute("UPDATE users SET temp_pwd = NULL WHERE email = '%s';" %(inp_usrn))
                    cnx.commit()
                    #reset_pwd = True
                #Extract the account type from MySQL
                get_type = db_get(inp_usrn,cur,"type")
                cnx.close()
                return render_template("main.html", user = inp_usrn, admin = (get_type == "admin"));
        invalid_inp = True
    cnx.close()
    return render_template("login.html",invalid_inp = invalid_inp)

@app.route('/signup',methods=['GET','POST'])
def sign_up():

    cnx = MySQLdb.connect(**config)
    cur = cnx.cursor()

    if request.method == 'POST':
        create_usr = request.form['email address'].lower()
        create_pswd = request.form['password']

        if not db_has(create_usr,cur,"email",create_usr) and validate_email(create_usr,verify=True):
            cur.execute("INSERT INTO `users` (`email`,`pswd`,`type`,`temp_pwd`) VALUES ('%s', SHA2('%s',224), 'user', NULL);" %(create_usr,create_pswd))
            cnx.commit()
            cnx.close()
            return render_template("createaccount.html", text = "Account Created!")
    cnx.close()
    return render_template("createaccount.html")

@app.route('/forgot', methods=['GET','POST'])
def forgot_login():
    if request.method =='POST':
        cnx = MySQLdb.connect(**config)
        cur = cnx.cursor()
        ea = request.form['email address'].lower()

        if (db_has(ea,cur,"email",ea)):
            if not db_has(ea,cur,"temp_pwd",None):
                return render_template("forgotlogin.html",message = "An email was already sent.")

            #Connect into gmail server
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(bot_user, bot_pwd)

            #Generate random key/temp_password
            temp_key = random_key()

            #Sending email
            message = """From: %s
                       \nTo: %s
                       \nSubject: %s
                       \n
                       \n%s""" % (bot_user, ea, "Sunflower24 Password Reset", "Here is your temporary password: \n%s" %(temp_key))
            server.sendmail(bot_user, ea, message)
            server.close()

            #Updating MySQL to incorporate the temp password
            cur.execute("UPDATE users SET temp_pwd = SHA2('%s',224) WHERE email = '%s';" %(temp_key, ea))
            cnx.commit()
            cur.close()

            return render_template("forgotlogin.html",message = "Email sent! Please check your spam box as well.")
        return render_template("forgotlogin.html",message = "Invalid input.")

    return render_template("forgotlogin.html")

def db_get(ea,cur,category):
    #Extracts the username from MySQL (if applicable)
    cur.execute("SELECT %s FROM users WHERE email = '%s';" %(category,ea))
    item = str(cur.fetchone())[2:-3]
    return item

#Checks if input is in the database
def db_has(ea,cur,category,compare):
    return db_get(ea,cur,category) == compare

def random_key():
    char = string.ascii_letters + string.punctuation  + string.digits
    pwd =  "".join(choice(char) for x in range(randint(8, 16)))
    return pwd
