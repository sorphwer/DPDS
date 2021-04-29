from flask_restful_swagger_2 import Schema
class AuthorModel(Schema):
    type = 'object'
    properties = {
        'id':{
            'type': 'string',
        },
        'username':{
            'type': 'string',
        },
        'name':{
            'type': 'string',
        }
    }
def serialize_author(author):
    return {
        'id': author['id'],
        'username': author['username'],
        'name': author['name'],
    }