from flask_restful_swagger_2 import Schema
class MovieModel(Schema):
    type = 'object'
    properties = {
        'id': {
            'type': 'string',
        },
        'title': {
            'type': 'string',
        },
        'summary': {
            'type': 'string',
        },
        'released': {
            'type': 'string',
        },
        'duration': {
            'type': 'integer',
        },
        'rated': {
            'type': 'string',
        },
        'tagline': {
            'type': 'string',
        },
        'poster_image': {
            'type': 'string',
        },
        'my_rating': {
            'type': 'integer',
        }
    }

def serialize_movie(movie, my_rating=None):
    return {
        'id': movie['tmdbId'],
        'title': movie['title'],
        'summary': movie['plot'],
        'released': movie['released'],
        'duration': movie['runtime'],
        'rated': movie['imdbRating'],
        'tagline': movie['plot'],
        'poster_image': movie['poster'],
        'my_rating': my_rating,
    }