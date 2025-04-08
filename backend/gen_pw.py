import bcrypt
pw = "WtF.?4ggWP2ez"
hashed = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
print(hashed)
print(len(hashed))
print("$2b$12$3L8NvWNw9z71AJ2fZxkxb0akXVOL8c0y6jt/ofcqMmDDwS3zirl7u")
print(len("$2b$12$3L8NvWNw9z71AJ2fZxkxb0akXVOL8c0y6jt/ofcqMmDDwS3zirl7u"))