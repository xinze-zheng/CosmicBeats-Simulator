class FileObject():

    def __init__(self, fileID, filename = "", size=1) -> None:
        self.__filename = filename 
        self.__size = size
        self.__fileID = fileID

    @property
    def filename(self):
        return self.__filename
    
    @property
    def size(self):
        return self.size
    
    @property
    def fileID(self):
        return self.fileID