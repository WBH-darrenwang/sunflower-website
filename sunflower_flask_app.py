from flask import Flask, render_template, request, redirect, url_for, session
from validate_email import validate_email
import MySQLdb
import hashlib
import smtplib
from random import randint, choice
import string

'''
Cookies
Write an option for admin to make others admin, or demote
Write different page for users vs admin vs etc.
When someone's authority is changed, how do make the person know that automatically and make them refresh for updated content?
jQuery
Have a previous email variable so you don't need to keep going into the database
'''

app = Flask(__name__)

#Login information for pythonanywhere MySQL
config = {
    'host' : "localhost",
    'user' : "root",
    'passwd' : "",
    'db' : "XXXX"
}

#Forgotten password email account
bot_user = "example@gmail.com"
bot_pwd = "XXXX"

#Session secret key
app.secret_key = 'XXXX'

#Login Page
@app.route('/', methods=['GET','POST'])
def login_page():

    #Allows the user to enter their account after they have changed their password through /new_password link
    if session.get('pass'):

        #Extracts the email address and account type from session
        curr_email = session['email_address']
        curr_type = session['type']

        #Pops the loophole from /new_password and logs the user into his/her account
        session.pop('pass',None)
        return render_template("main.html", user = curr_email, admin = (curr_type == "admin"))
    
    #Connects to MySQL server
    cnx = MySQLdb.connect(**config)
    cur = cnx.cursor()
    
    #Variable for /login template rendering
    invalid_inp = False

    #Comparing input and items in MySQL
    if request.method == 'POST':

        #Stores input lowercase email address from html form
        inp_usrn = request.form['email address'].lower()

        #Checks if the inputted username is present in MySQL
        if (db_has(inp_usrn,cur,"email",inp_usrn)):
            
            #Stores input password into String
            inp_pswd = request.form['password']

            #Hashes input password using SHA224
            hash_obj = hashlib.sha224(inp_pswd).hexdigest()

            #Extract the password from MySQL
            get_pswd = db_get(inp_usrn,cur,"pswd")

            #Compares the two encrypted passwords (one from database, one from form input) and compares the other pair (temp password,input password)
            if (hash_obj == get_pswd) or (db_get(inp_usrn,cur,"temp_pwd") == hash_obj):
                
                #Extract the account type: Admin or User
                get_type = db_get(inp_usrn,cur,"type")
                
                #If the database has a temp password (created in /forgot), store info into session and redirect to /new_password
                if not db_has(inp_usrn,cur,"temp_pwd",'NULL'):
                    
                    #Destroy temp password if user logs in with the original password after requesting for a temp password
                    if (hash_obj == get_pswd):
                        session['new_pwd_pass'] = False
                        db_set(curr_email,cur,'temp_pwd','NULL')
                        return render_template("main.html", user = inp_usrn, admin = (get_type == "admin"))
                        
                    cnx.close()
                    
                    #Stores email address and account type info into sessions
                    session['email_address'] = inp_usrn
                    session['type'] = get_type
                    
                    #This session makes sure that there's only way entering the /new_password link
                    session['new_pwd_pass'] = True
                    
                    return redirect(url_for('new_password'))
                
                #Enter the account normally through the login page
                return render_template("main.html", user = inp_usrn, admin = (get_type == "admin"))
        
        #If the inputs fails enterance, this variable is changed and raises warning in a new html page
        invalid_inp = True
        
    cnx.close()
    return render_template("login.html",invalid_inp = invalid_inp)

#Sign up page
@app.route('/signup',methods=['GET','POST'])
def sign_up():
    
    #Connect to MySQL server
    cnx = MySQLdb.connect(**config)
    cur = cnx.cursor()

    if request.method == 'POST':
        
        #Extract the email address and password from html form inputs
        create_usr = request.form['email address'].lower()
        create_pswd = request.form['password']
        
        #Checks if there are no duplicates in email address and checks if 
        if not db_has(create_usr,cur,"email",create_usr):
            
            #Checks if the email is a REAL email address using validate_email API
            if validate_email(create_usr,verify=True):
                
                #Creates account and adds it into users table in MySQL
                cur.execute("INSERT INTO `users` (`email`,`pswd`,`type`,`temp_pwd`) VALUES ('%s', SHA2('%s',224), 'user', 'NULL');" %(create_usr,create_pswd))
                cnx.commit()
                cnx.close()
                
                return render_template("createaccount.html", text = "Account Created!")
    
    cnx.close()
    return render_template("createaccount.html")

#Forgotten password page
@app.route('/forgot', methods=['GET','POST'])
def forgot_login():
    
    if request.method =='POST':
        
        #Connect to MySQL server
        cnx = MySQLdb.connect(**config)
        cur = cnx.cursor()
        
        #Stores input lowercase email address from html form
        ea = request.form['email address'].lower()
        
        #Makes sure that no two emails for temp password is sent at the same time
        if (db_has(ea,cur,"email",ea)):
            if not db_has(ea,cur,"temp_pwd", 'NULL'):
                return render_template("forgotlogin.html",message = "An email was already sent.")

            #Connect into gmail server using the gmail account's email address and password
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(bot_user, bot_pwd)

            #Generate random key/temp_password
            temp_key = random_key()

            #Creating the message and sending the email with the randomly generated code
            message = """From: %s
                       \nTo: %s
                       \nSubject: %s
                       \n
                       \n%s""" % (bot_user, ea, "Sunflower24 Password Reset", "Here is your temporary password: \n%s" %(temp_key))
            server.sendmail(bot_user, ea, message)
            server.close()

            #Updating MySQL with the temp password
            cur.execute("UPDATE users SET temp_pwd = SHA2('%s',224) WHERE email = '%s';" %(temp_key, ea))
            cnx.commit()
            cur.close()
            
            return render_template("forgotlogin.html",message = "Email sent! Please check your spam box as well.")
            
        return render_template("forgotlogin.html",message = "Invalid input.")

    return render_template("forgotlogin.html")
    
#New password page, after you have logged in with the temp password
@app.route('/new_password', methods=['GET','POST'])
def new_password():
    
    #Does not allow users to access this password change unless they are redirected login page
    if not session.get('new_pwd_pass'):
        return "Error 404! Forbidden enterance."
        
    if request.method == 'POST':
        
        #Stores input passwords from html form
        pwd1 = request.form['password']
        pwd2 = request.form['password2']
        
        #Makes sure the two passwords are entered in the same
        if not (pwd1 == pwd2):
            return render_template("newpassword.html",text = "The passwords don't match!")
        
        #Checks if the password contains more than 6 characters, has letter, number, and symbol
        letter = False
        number = False
        symbol = False
        count = 0
        
        #Text for user to know which requirements their password did not fill out 
        message = ""

        for value in pwd1:
            if value in string.ascii_letters:
                letter = True
            elif value in string.digits:
                number = True
            elif value in string.punctuation:
                symbol = True
            count += 1

        if not (count > 6):
            message += "Password needs to be more than 6 items."
        if not letter:
            message += " Need letter "
        if not number:
            message += " Need number "
        if not symbol:
            message += " Need symbol "
        
        #Retrieves the current email address from session
        curr_email = session.get('email_address')
        
        #Allows user to create the new password and redirect the user to the login page and automatically log in
        if(letter and number and symbol and count > 6):
            
            #This session allows users to log into the account right after they change their password instead of retyping everything again in the login page
            session['pass'] = True
            
            #Connects to MySQL server
            cnx = MySQLdb.connect(**config)
            cur = cnx.cursor()
            
            #Creates the new password and makes temp password  equals to NULL
            cur.execute("UPDATE users SET pswd = SHA2('%s',224) WHERE email = '%s';" %(pwd1, curr_email))
            db_set(curr_email,cur,'temp_pwd','NULL')
            cnx.commit()
            cnx.close()
            
            #Prevents the user from changing password again unless the user requests for another password change
            session.pop('new_pwd_pass',None)
            return redirect(url_for("login_page"))
        else:
            return render_template("newpassword.html",text = message)

    return render_template("newpassword.html")

#Get info from MySQL
def db_get(ea,cur,category):
    
    #Extracts the username from MySQL (if applicable)
    cur.execute("SELECT %s FROM users WHERE email = '%s';" %(category,ea))
    item = str(cur.fetchone())[2:-3]
    return item

#Checks if input value in a category for that email address is in the database
def db_has(ea,cur,category,compare):
    return db_get(ea,cur,category) == compare

#Sets a input value in a category for that email address
def db_set(ea,cur,category,value):
    cur.execute("UPDATE users SET %s = '%s' WHERE email = '%s';" %(category,value,ea))

#Generates a random string for key
def random_key():
    char = string.ascii_letters + string.punctuation  + string.digits
    pwd =  "".join(choice(char) for x in range(randint(8, 16)))
    return pwd
