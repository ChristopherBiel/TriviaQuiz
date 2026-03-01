import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def is_password_hashed(password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password.encode('utf-8')) or \
           bcrypt.checkpw(password.encode('utf-8'), password.encode('utf-8').decode('utf-8').encode('utf-8'))