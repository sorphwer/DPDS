from flask_restful_swagger_2 import Schema
class GenreModel(Schema):
    type = 'object'
    properties = {
        'id': {
            'type': 'integer',
        },
        'name': {
            'type': 'string',
        }
    }
def serialize_genre(genre):
    return {
        'id': genre['id'],
        'name': genre['name'],
    }