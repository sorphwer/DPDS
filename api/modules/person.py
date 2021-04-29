from flask_restful_swagger_2 import Schema
class PersonModel(Schema):
    type = 'object'
    properties = {
        'id': {
            'type': 'integer',
        },
        'name': {
            'type': 'string',
        },
        'poster_image': {
            'type': 'string',
        }
    }


def serialize_person(person):
    return {
        'id': person['tmdbId'],
        'name': person['name'],
        'poster_image': person['poster'],
    }