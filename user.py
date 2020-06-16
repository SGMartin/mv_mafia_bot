'''
Needed workaround until robobrowser import bug is fixed
'''
import werkzeug
werkzeug.cached_property  = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

class User:

    def  __init__(self, user_id, password):
        
        # Attempt to log into MV with these credentials.
        self.login(user_id, password)


    def login(self, user, password):
        browser = RoboBrowser(parser="html.parser")
        browser.open('http://m.mediavida.com/login')
        login = browser.get_form(id='login_form')
        login['name'].value = user
        login['password'].value = password
        browser.submit_form(login)
        return browser


    def post(self, message, tid, browser):
        browser.open('http://www.mediavida.com/foro/post.php?tid={}'.format(tid))
        mssg = browser.get_form(class_='single')
        mssg['cuerpo'].value = message
        browser.submit_form(mssg)
        return browser.url

