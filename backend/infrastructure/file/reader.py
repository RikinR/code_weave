def read_file(path:str)->bytes:
    with open(path,"rb") as f:
        return f.read()