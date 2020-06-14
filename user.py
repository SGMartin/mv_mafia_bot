from robobrowser import RoboBrowser

def login(user, password):
    browser = RoboBrowser(parser="lxml")
    browser.open('https://www.mediavida.com/login')
    login = browser.get_form(class_='full')
    login['name'].value = user
    login['password'].value = password
    browser.submit_form(login)
    return browser


def post(message, tid, browser):
    browser.open('http://www.mediavida.com/foro/post.php?tid={}'.format(tid))
    mssg = browser.get_form(class_='single')
    mssg['cuerpo'].value = message
    browser.submit_form(mssg)
    return browser.url