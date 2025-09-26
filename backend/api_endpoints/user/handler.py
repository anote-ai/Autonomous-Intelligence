from database.db import view_user

def ViewUserHandler(request, user_email):
    return view_user(user_email)