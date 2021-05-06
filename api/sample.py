#To import modules class and  import 'void' functions
from modules import *

#direct import
from void import *
#import with name
import void as _

#import db script
import db 
import db.read as dbr
# print(_.helloworld())
# print(helloworld())
# print(TagModel)
# print(TagModel.type)
print(dbr.description_read())
# print(db.__description_write())
print(db.description_read())