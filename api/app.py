import binascii
import hashlib
import os
import ast
import re
import sys
import uuid
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
from functools import wraps

from flask import Flask, g, request, send_from_directory, abort, request_started
from flask_cors import CORS
from flask_restful import Resource, reqparse
from flask_restful_swagger_2 import Api, swagger, Schema
from flask_json import FlaskJSON, json_response

from neo4j import GraphDatabase, basic_auth
from neo4j.exceptions import Neo4jError
import neo4j.time

#Custom modules👇
from api.modules import *
import api.void as _
import api.db as db

load_dotenv(find_dotenv())

app = Flask(__name__)

CORS(app)
FlaskJSON(app)

api = Api(app, title='DPDS Text Search System - API Panel', api_version='0.1.10')

GLOBAL_USER_ID = 'fdfb834b-a161-44b5-b859-b706f2a7da29'

@api.representation('application/json')
def output_json(data, code, headers=None):
    return json_response(data_=data, headers_=headers, status_=code)




DATABASE_USERNAME = _.env('DATABASE_USERNAME')
DATABASE_PASSWORD = _.env('DATABASE_PASSWORD')
DATABASE_URL = _.env('DATABASE_URL')

driver = GraphDatabase.driver(DATABASE_URL, auth=basic_auth(DATABASE_USERNAME, str(DATABASE_PASSWORD)))

app.config['SECRET_KEY'] = _.env('SECRET_KEY')


def get_db():
    """
    get a db session
    """
    if not hasattr(g, 'neo4j_db'):
        g.neo4j_db = driver.session()
    print('Connected to DB :',DATABASE_URL)
    return g.neo4j_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'neo4j_db'):
        g.neo4j_db.close()


def set_user(sender, **extra):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        g.user = {'id': None}
        return
    match = re.match(r'^Token (\S+)', auth_header)
    if not match:
        abort(401, 'invalid authorization format. Follow `Token <token>`')
        return
    token = match.group(1)

    def get_user_by_token(tx, token):
        return tx.run(
            '''
            MATCH (user:User {api_key: $api_key}) RETURN user
            ''', {'api_key': token}
        ).single()

    db = get_db()
    result = db.read_transaction(get_user_by_token, token)
    try:
        g.user = result['user']
    except (KeyError, TypeError):
        abort(401, 'invalid authorization key')
    return
request_started.connect(set_user, app)


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return {'message': 'no authorization provided'}, 401
        return f(*args, **kwargs)
    return wrapped

def hash_password(username, password):
    if sys.version[0] == 2:
        s = '{}:{}'.format(username, password)
    else:
        s = '{}:{}'.format(username, password).encode('utf-8')
    return hashlib.sha256(s).hexdigest()

class ApiDocs(Resource):
    def get(self, path=None):
        if not path:
            path = 'index.html'
        return send_from_directory('swaggerui', path)

#NOT IN USE
class GenreList(Resource):
    @swagger.doc({
        'tags': ['genres'],
        'summary': 'Find all genres',
        'description': 'Returns all genres',
        'responses': {
            '200': {
                'description': 'A list of genres',
                'schema': GenreModel,
            }
        }
    })
    def get(self):
        def get_genres(tx):
            return list(tx.run('MATCH (genre:Genre) SET genre.id=id(genre) RETURN genre'))
        db = get_db()
        result = db.write_transaction(get_genres)
        return [serialize_genre(record['genre']) for record in result]
#CHECK API
class TestSwagger(Resource):
    @swagger.doc({
        'tags': ['Check'],
        'summary': 'Check if api service is available',
        'description': 'Return api info,if status code is not 200, API is not available',
        'responses': {
            '200': {
                'description': 'Success',
            },
            '404':{
                'description': 'API is not available',
            }
        }
    })
    def get(self):
        return 'ok'
#NOT IN USE     
class Movie(Resource):
    @swagger.doc({
        'tags': ['movies'],
        'summary': 'Find movie by ID',
        'description': 'Returns a movie',
        'parameters': [
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'default': 'Token <token goes here>',
                'required': False
            },
            {
                'name': 'id',
                'description': 'movie tmdbId, a string',
                'in': 'path',
                'type': 'string',
                'required': True,
            }
        ],
        'responses': {
            '200': {
                'description': 'A movie',
                'schema': MovieModel,
            },
            '404': {
                'description': 'movie not found'
            },
        }
    })
    def get(self,id):
        def get_movie(tx, user_id, id):
            return list(tx.run(
                '''
                MATCH (movie:Movie {tmdbId: $id})
                OPTIONAL MATCH (movie)<-[my_rated:RATED]-(me:User {id: $user_id})
                OPTIONAL MATCH (movie)<-[r:ACTED_IN]-(a:Person)
                OPTIONAL MATCH (related:Movie)<--(a:Person) WHERE related <> movie
                OPTIONAL MATCH (movie)-[:IN_GENRE]->(genre:Genre)
                OPTIONAL MATCH (movie)<-[:DIRECTED]-(d:Person)
                OPTIONAL MATCH (movie)<-[:PRODUCED]-(p:Person)
                OPTIONAL MATCH (movie)<-[:WRITER_OF]-(w:Person)
                WITH DISTINCT movie,
                my_rated,
                genre, d, p, w, a, r, related, count(related) AS countRelated
                ORDER BY countRelated DESC
                RETURN DISTINCT movie,
                my_rated.rating AS my_rating,
                collect(DISTINCT d) AS directors,
                collect(DISTINCT p) AS producers,
                collect(DISTINCT w) AS writers,
                collect(DISTINCT{ name:a.name, id:a.tmdbId, poster_image:a.poster, role:r.role}) AS actors,
                collect(DISTINCT related) AS related,
                collect(DISTINCT genre) AS genres
                ''', {'user_id': user_id , 'id': id}
            ))
        db = get_db()

        result = db.read_transaction(get_movie, g.user['id'], id)
        for record in result:
            return {
                'id': record['movie']['tmdbId'],
                'title': record['movie']['title'],
                'summary': record['movie']['plot'],
                'released': record['movie']['released'],
                'duration': record['movie']['runtime'],
                'rated': record['movie']['rated'],
                'tagline': record['movie']['plot'],
                'poster_image': record['movie']['poster'],
                'my_rating': record['my_rating'],
                'genres': [serialize_genre(genre) for genre in record['genres']],
                'directors': [serialize_person(director)for director in record['directors']],
                'producers': [serialize_person(producer) for producer in record['producers']],
                'writers': [serialize_person(writer) for writer in record['writers']],
                'actors': [
                    {
                        'id': actor['id'],
                        'name': actor['name'],
                        'role': actor['role'],
                        'poster_image': actor['poster_image'],
                    } for actor in record['actors']
                ],
                'related': [serialize_movie(related) for related in record['related']],
            }
        return {'message': 'movie not found'}, 404


#NOT IN USE
class MovieListByGenre(Resource):
    @swagger.doc({
        'tags': ['movies'],
        'summary': 'Find movie by genre id',
        'description': 'Returns a list of movies by genre',
        'parameters': [
            {
                'name': 'genre_id',
                'description': 'The name of the genre.',
                'in': 'path',
                'type': 'string',
                'required': 'true'
            }
        ],
        'responses': {
            '200': {
                'description': 'A list of movies with the specified genre',
                'schema': {
                    'type': 'array',
                    'items': MovieModel,
                }
            }
        }
    })
    def get(self, genre_id):
        def get_movies_by_genre(tx, genre_id):
            return list(tx.run(
                '''
                MATCH (movie:Movie)-[:IN_GENRE]->(genre:Genre)
                WHERE toLower(genre.name) = toLower($genre_id)
                    // while transitioning to the sandbox data
                    OR id(genre) = toInteger($genre_id)
                RETURN movie
                ''', {'genre_id': genre_id}
            ))
        db = get_db()
        result = db.read_transaction(get_movies_by_genre, genre_id)
        return [serialize_movie(record['movie']) for record in result]

# Not sure this is useful anymore
class MovieListByDateRange(Resource):
    @swagger.doc({
        'tags': ['movies'],
        'summary': 'Find movie by year range',
        'description': 'Returns a list of movies released between a range of years',
        'parameters': [
            {
                'name': 'start',
                'description': 'start year',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            },
            {
                'name': 'end',
                'description': 'end year',
                'in': 'path',
                'type': 'integer',
                'required': 'true'
            }
        ],
        'responses': {
            '200': {
                'description': 'A list of movies released between the specified years',
                'schema': {
                    'type': 'array',
                    'items': MovieModel,
                }
            }
        }
    })
    def get(self, start, end):
        try:
            params = {'start': start, 'end': end}
        except ValueError:
            return {'description': 'invalid year format'}, 400

        def get_movies_list_by_date_range(tx, params):
            return list(tx.run(
                '''
                MATCH (movie:Movie)
                WHERE movie.year > $start AND movie.year < $end
                RETURN movie
                ''', params
            ))

        db = get_db()
        result = db.read_transaction(get_movies_list_by_date_range, params)
        return [serialize_movie(record['movie']) for record in result]

#NOT IN USE
class MovieListByPersonActedIn(Resource):
    @swagger.doc({
        'tags': ['movies'],
        'summary': 'Find movies by actor',
        'description': 'Returns a list of movies that a person has acted in.',
        'parameters': [
            {
                'name': 'person_id',
                'description': 'person id',
                'in': 'path',
                'type': 'string',
                'required': 'true'
            },
        ],
        'responses': {
            '200': {
                'description': 'A list of movies the specified person has acted in',
                'schema': {
                    'type': 'array',
                    'items': MovieModel,
                }
            }
        }
    })
    def get(self, person_id):
        def get_movies_by_acted_in(tx, person_id):
            return list(tx.run(
                '''
                MATCH (actor:Actor {tmdbId: $person_id})-[:ACTED_IN]->(movie:Movie)
                RETURN DISTINCT movie
                ''', {'person_id': person_id}
            ))
        db = get_db()
        result = db.read_transaction(get_movies_by_acted_in, person_id)
        return [serialize_movie(record['movie']) for record in result]

#NOT IN USE
class MovieListByWrittenBy(Resource):
    @swagger.doc({
        'tags': ['movies'],
        'summary': 'Find movies by writer',
        'description': 'Returns a list of movies writen by a person',
        'parameters': [
            {
                'name': 'person_id',
                'description': 'person id',
                'in': 'path',
                'type': 'string',
                'required': 'true'
            },
        ],
        'responses': {
            '200': {
                'description': 'A list of movies the specified person has written',
                'schema': {
                    'type': 'array',
                    'items': MovieModel,
                }
            }
        }
    })
    def get(self, person_id):
        def get_movies_list_written_by(tx, person_id):
            return list(tx.run(
                '''
                MATCH (actor:Writer {tmdbId: $person_id})-[:WRITER_OF]->(movie:Movie)
                RETURN DISTINCT movie
                ''', {'person_id': person_id}
            ))
        db = get_db()
        result = db.read_transaction(get_movies_list_written_by, person_id)
        return [serialize_movie(record['movie']) for record in result]

#NOT IN USE
class MovieListByDirectedBy(Resource):
    @swagger.doc({
        'tags': ['movies'],
        'summary': 'Find movies by director',
        'description': 'Returns a list of movies directed by a person',
        'parameters': [
            {
                'name': 'person_id',
                'description': 'person id',
                'in': 'path',
                'type': 'string',
                'required': 'true'
            },
        ],
        'responses': {
            '200': {
                'description': 'A list of movies the specified person has directed',
                'schema': {
                    'type': 'array',
                    'items': MovieModel,
                }
            }
        }
    })
    def get(self, person_id):
        def get_mmovies_list_directed_by(tx, person_id):
            return list(tx.run(
                '''
                MATCH (actor:Director {tmdbId: $person_id})-[:DIRECTED]->(movie:Movie)
                RETURN DISTINCT movie
                ''', {'person_id': person_id}
            ))
        db = get_db()
        result = db.read_transaction(get_mmovies_list_directed_by, person_id)
        return [serialize_movie(record['movie']) for record in result]

#NOT IN USE
class MovieListRatedByMe(Resource):
    @swagger.doc({
        'tags': ['movies'],
        'summary': 'A list of movies the authorized user has rated.',
        'description': 'A list of movies the authorized user has rated.',
        'parameters': [
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'default': 'Token <token goes here>',
                'required': True
            },
        ],
        'responses': {
            '200': {
                'description': 'A list of movies the authorized user has rated',
                'schema': {
                    'type': 'array',
                    'items': MovieModel,
                }
            }
        }
    })
    @login_required
    def get(self):
        def get_movies_rated_by_me(tx, user_id):
            return list(tx.run(
                '''
                MATCH (:User {id: $user_id})-[rated:RATED]->(movie:Movie)
                RETURN DISTINCT movie, rated.rating as my_rating
                ''', {'user_id': user_id}
            ))
        db = get_db()
        result = db.read_transaction(get_movies_rated_by_me, g.user['id'])
        return [serialize_movie(record['movie'], record['my_rating']) for record in result]

#NOT IN USE
class MovieListRecommended(Resource):
    @swagger.doc({
        'tags': ['movies'],
        'summary': 'A list of recommended movies for the authorized user.',
        'description': 'A list of recommended movies for the authorized user.',
        'parameters': [
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'default': 'Token <token goes here>',
                'required': True
            },
        ],
        'responses': {
            '200': {
                'description': 'A list of recommended movies for the authorized user',
                'schema': {
                    'type': 'array',
                    'items': MovieModel,
                }
            }
        }
    })
    @login_required
    def get(self):
        def get_movies_list_recommended(tx, user_id):
            return list(tx.run(
                '''
                MATCH (me:User {id: $user_id})-[my:RATED]->(m:Movie)
                MATCH (other:User)-[their:RATED]->(m)
                WHERE me <> other
                AND abs(my.rating - their.rating) < 2
                WITH other,m
                MATCH (other)-[otherRating:RATED]->(movie:Movie)
                WHERE movie <> m 
                WITH avg(otherRating.rating) AS avgRating, movie
                RETURN movie
                ORDER BY avgRating desc
                LIMIT 25
                ''', {'user_id': user_id}
            ))
        db = get_db()
        result = db.read_transaction(get_movies_list_recommended, g.user['id'])
        return [serialize_movie(record['movie']) for record in result]
#NOT IN USE
class Person(Resource):
    @swagger.doc({
        'tags': ['people'],
        'summary': 'Find person by id',
        'description': 'Returns a person',
        'parameters': [
            {
                'name': 'id',
                'description': 'person id',
                'in': 'path',
                'type': 'integer',
                'required': True
            }
        ],
        'responses': {
            '200': {
                'description': 'A person',
                'schema': PersonModel,
            },
            '404': {
                'description': 'person not found'
            },
        }
    })
    def get(self, id):
        def get_person_by_id(tx, user_id):
            return list(tx.run(
                '''
                MATCH (person:Person {tmdbId: $id})
                OPTIONAL MATCH (person)-[:DIRECTED]->(d:Movie)
                OPTIONAL MATCH (person)<-[:PRODUCED]->(p:Movie)
                OPTIONAL MATCH (person)<-[:WRITER_OF]->(w:Movie)
                OPTIONAL MATCH (person)<-[r:ACTED_IN]->(a:Movie)
                OPTIONAL MATCH (person)-->(movies)<-[relatedRole:ACTED_IN]-(relatedPerson)
                RETURN DISTINCT person,
                collect(DISTINCT { name:d.title, id:d.tmdbId, poster_image:d.poster}) AS directed,
                collect(DISTINCT { name:p.title, id:p.tmdbId, poster_image:p.poster}) AS produced,
                collect(DISTINCT { name:w.title, id:w.tmdbId, poster_image:w.poster}) AS wrote,
                collect(DISTINCT{ name:a.title, id:a.tmdbId, poster_image:a.poster, role:r.role}) AS actedIn,
                collect(DISTINCT{ name:relatedPerson.name, id:relatedPerson.tmdbId, poster_image:relatedPerson.poster, role:relatedRole.role}) AS related
                ''', {'id': user_id}
            ))
        db = get_db()
        results = db.read_transaction(get_person_by_id, id)
        for record in results:
            return {
                'id': record['person']['id'],
                'name': record['person']['name'],
                'poster_image': record['person']['poster'],
                'directed': [
                    {
                        'id': movie['id'],
                        'name': movie['name'],
                        'poster_image': movie['poster_image'],
                    } for movie in record['directed']
                ],
                'produced': [
                    {
                        'id': movie['id'],
                        'name': movie['name'],
                        'poster_image': movie['poster_image'],
                    } for movie in record['produced']
                ],
                'wrote': [
                    {
                        'id': movie['id'],
                        'name': movie['name'],
                        'poster_image': movie['poster_image'],
                    } for movie in record['wrote']
                ],
                'actedIn': [
                    {
                        'id': movie['id'],
                        'name': movie['name'],
                        'poster_image': movie['poster_image'],
                        'role': movie['role'],
                    } for movie in record['actedIn']
                ],
                'related': [
                    {
                        'id': person['id'],
                        'name': person['name'],
                        'poster_image': person['poster_image'],
                        'role': person['role'],
                    } for person in record['related']
                ],
            }
        return {'message': 'person not found'}, 404

#NOT IN USE
class PersonList(Resource):
    @swagger.doc({
        'tags': ['people'],
        'summary': 'Find all people',
        'description': 'Returns a list of people',
        'responses': {
            '200': {
                'description': 'A list of people',
                'schema': {
                    'type': 'array',
                    'items': PersonModel,
                }
            }
        }
    })
    def get(self):
        def get_persons_list(tx):
            return list(tx.run(
                '''
                MATCH (person:Person) RETURN person
                '''
            ))
        db = get_db()
        results = db.read_transaction(get_persons_list)
        return [serialize_person(record['person']) for record in results]

#NOT IN USE
class PersonBacon(Resource):
    @swagger.doc({
        'tags': ['people'],
        'summary': 'Find all Bacon paths',
        'description': 'Returns all bacon paths from person 1 to person 2',
        'parameters': [
            {
                'name': 'name1',
                'description': 'Name of the origin user',
                'in': 'query',
                'type': 'string',
                'required': True,
            },
            {
                'name': 'name2',
                'description': 'Name of the target user',
                'in': 'query',
                'type': 'string',
                'required': True,
            }
        ],
        'responses': {
            '200': {
                'description': 'A list of people',
                'schema': {
                    'type': 'array',
                    'items': PersonModel,
                }
            }
        }
    })
    def get(self):
        name1 = request.args['name1']
        name2 = request.args['name2']
        def get_bacon(tx, name1, name2):
            return list(tx.run(
                '''
                MATCH p = shortestPath( (p1:Person {name: $name1})-[:ACTED_IN*]-(target:Person {name: $name2}) )
                WITH [n IN nodes(p) WHERE n:Person | n] as bacon
                UNWIND(bacon) AS person
                RETURN DISTINCT person
                ''', {'name1': name1, 'name2': name2}
            ))
        db = get_db()
        results = db.read_transaction(get_bacon, name1, name2)
        return [serialize_person(record['person']) for record in results]


class Register(Resource):
    @swagger.doc({
        'tags': ['Users'],
        'summary': 'Register a new user',
        'description': 'Register a new user',
        'parameters': [
            {
                'name': 'body',
                'in': 'body',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'username': {
                            'type': 'string',
                        },
                        'password': {
                            'type': 'string',
                        }
                    }
                }
            },
        ],
        'responses': {
            '201': {
                'description': 'Your new user',
                'schema': UserModel,
            },
            '400': {
                'description': 'Error message(s)',
            },
        }
    })
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if not username:
            return {'username': 'This field is required.'}, 400
        if not password:
            return {'password': 'This field is required.'}, 400

        def get_user_by_username(tx, username):
            return tx.run(
                '''
                MATCH (user:User {username: $username}) RETURN user
                ''', {'username': username}
            ).single()

        db = get_db()
        result = db.read_transaction(get_user_by_username, username)
        if result and result.get('user'):
            return {'username': 'username already in use'}, 400

        def create_user(tx, username, password):
            return tx.run(
                '''
                CREATE (user:User {id: $id, username: $username, password: $password, api_key: $api_key}) RETURN user
                ''',
                {
                    'id': str(uuid.uuid4()),
                    'username': username,
                    'password': hash_password(username, password),
                    'api_key': binascii.hexlify(os.urandom(20)).decode()
                }
            ).single()

        results = db.write_transaction(create_user, username, password)
        user = results['user']
        return serialize_user(user), 201


class Login(Resource):
    @swagger.doc({
        'tags': ['Users'],
        'summary': 'Login',
        'description': 'Login',
        'parameters': [
            {
                'name': 'body',
                'in': 'body',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'username': {
                            'type': 'string',
                        },
                        'password': {
                            'type': 'string',
                        }
                    }
                }
            },
        ],
        'responses': {
            '200': {
                'description': 'succesful login'
            },
            '400': {
                'description': 'invalid credentials'
            }
        }
    })
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if not username:
            return {'username': 'This field is required.'}, 400
        if not password:
            return {'password': 'This field is required.'}, 400

        def get_user_by_username(tx, username):
            return tx.run(
                '''
                MATCH (user:User {username: $username}) RETURN user
                ''', {'username': username}
            ).single()

        db = get_db()
        result = db.read_transaction(get_user_by_username, username)
        try:
            user = result['user']
        except KeyError:
            return {'username': 'username does not exist'}, 400
        except TypeError:
            return {'username': 'username does not exist'}, 400

        expected_password = hash_password(user['username'], password)
        if user['password'] != expected_password:
            return {'password': 'wrong password'}, 400
        return {
            'token': user['api_key']
        }


class UserMe(Resource):
    @swagger.doc({
        'tags': ['Users'],
        'summary': 'Get your user',
        'description': 'Get your user',
        'parameters': [{
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'default': 'Token <token goes here>',
        }],
        'responses': {
            '200': {
                'description': 'the user',
                'schema': UserModel,
            },
            '401': {
                'description': 'invalid / missing authentication',
            },
        }
    })
    @login_required
    def get(self):
        return serialize_user(g.user)

#NOT IN USE
class RateMovie(Resource):
    @swagger.doc({
        'tags': ['movies'],
        'summary': 'Rate a movie from',
        'description': 'Rate a movie from 0-5 inclusive',
        'parameters': [
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'required': True,
                'default': 'Token <token goes here>',
            },
            {
                'name': 'id',
                'description': 'movie tmdbId',
                'in': 'path',
                'type': 'string',
            },
            {
                'name': 'body',
                'in': 'body',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'rating': {
                            'type': 'integer',
                        },
                    }
                }
            },
        ],
        'responses': {
            '200': {
                'description': 'movie rating saved'
            },
            '401': {
                'description': 'invalid / missing authentication'
            }
        }
    })
    @login_required
    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('rating', choices=list(range(0, 6)), type=int, required=True, help='A rating from 0 - 5 inclusive (integers)')
        args = parser.parse_args()
        rating = args['rating']

        def rate_movie(tx, user_id, movie_id, rating):
            return tx.run(
                '''
                MATCH (u:User {id: $user_id}),(m:Movie {tmdbId: $movie_id})
                MERGE (u)-[r:RATED]->(m)
                SET r.rating = $rating
                RETURN m
                ''', {'user_id': user_id, 'movie_id': movie_id, 'rating': rating}
            )

        db = get_db()
        results = db.write_transaction(rate_movie, g.user['id'], id, rating)
        return {}

    @swagger.doc({
        'tags': ['movies'],
        'summary': 'Delete your rating for a movie',
        'description': 'Delete your rating for a movie',
        'parameters': [
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'required': True,
                'default': 'Token <token goes here>',
            },
            {
                'name': 'id',
                'description': 'movie tmdbId',
                'in': 'path',
                'type': 'string',
            },
        ],
        'responses': {
            '204': {
                'description': 'movie rating deleted'
            },
            '401': {
                'description': 'invalid / missing authentication'
            }
        }
    })
    @login_required
    def delete(self, id):
        def delete_rating(tx, user_id, movie_id):
            return tx.run(
                '''
                MATCH (u:User {id: $user_id})-[r:RATED]->(m:Movie {tmdbId: $movie_id}) DELETE r
                ''', {'movie_id': movie_id, 'user_id': user_id}
            )
        db = get_db()
        db.write_transaction(delete_rating, g.user['id'], id)
        return {}, 204


class ArticleList(Resource):
    @swagger.doc({
        'tags':['Archive'],
        'summary':'Return all articles',
        'description':'Return a list of articles',
        'parameters': [
            {
                'name': 'page',
                'description': 'page number',
                'in': 'path',
                'type': 'string',
                'required': True,
                'default' : 1
            }
        ],
        'responses':{
            '200':{
                'description':'a list of articles',
                'schema':{
                    'type':'array',
                    'items': ArticleModel,
                }
            }
        }
    })
    def get(self,page):
        def get_articles(tx,page):
            return list(tx.run(
                '''
                MATCH (article:Article) RETURN article SKIP $page LIMIT 15
                ''',{'page':(int(page)-1)*15}
            ))
        db = get_db()
        result = db.read_transaction(get_articles,page)
        return [serialize_article(record['article']) for record in result]

class AuthorList(Resource):
    @swagger.doc({
        'tags':['GetResource'],
        'summary':'return all author',
        'description':'return a list of author',
        'responses':{
            '200':{
                'description':'a list of authors',
                'schema':{
                    'type':'array',
                    'items': AuthorModel,
                }
            }
        }
    })
    def get(self):
        def _cypher(tx):
            return list(tx.run(
                '''
                MATCH (n:Author) RETURN n LIMIT 100
                '''
            ))
        db = get_db()
        result = db.read_transaction(_cypher)
        return [serialize_author(record['n']) for record in result]

class TagList(Resource):
    @swagger.doc({
        'tags':['GetResource'],
        'summary':'Return all tags',
        'description':'Return a list of tags',
        'responses':{
            '200':{
                'description':'a list of tags',
                'schema':{
                    'type':'array',
                    'items': TagModel,
                }
            }
        }
    })
    def get(self):
        def _cypher(tx):
            return list(tx.run(
                '''
                MATCH (n:Tag) RETURN n LIMIT 180
                
                '''
            ))
        db = get_db()
        result = db.read_transaction(_cypher)
        return [serialize_tag(record['n']) for record in result]

class ArticleByAuthor(Resource):
    @swagger.doc({
        'tags':['GetResource'],
        'summary':'find articles by author',
        'description':'return all articles by this author',
        'parameters': [
            {
                'name': 'name',
                'description': 'author name',
                'in': 'path',
                'type': 'string',
                'required': True
            }
        ],
        'responses':{
            '200':{
                'description':'target article',
                'schema': {
                    'type':'array',
                    'items':ArticleModel
                }
            },
            '404':{
                'description': 'article not found'
            }
        }
    })
    def get(self,name):
        def _cypher(tx,name):
            return list(tx.run(
                '''
                MATCH (author:Author) WHERE author.name CONTAINS $name
                UNWIND author as authors
                MATCH (authors)<-[:WRITTEN_BY]-(article:Article)
                Return DISTINCT article
                ''',{'name':name}
            ))
        db = get_db()
        result = db.read_transaction(_cypher,name)
        return [serialize_article(record['article']) for record in result]



#HOME ARTICLE LIST (IF LOGGED IN)
class RankedArticles(Resource):
    @swagger.doc({
        'tags':['HomePage'],
        'summary':'HOME ARTICLE LIST (IF LOGGED IN)',
        'description':'Return a list of most popular articles',
        'parameters': [
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'default': 'Token 1a6221b3d04651b09ee96373d1a179c4cb958037',
                'required': False
            },
        ],
        'responses':{
            '200':{
                'description':'a list of articles',
                'schema':{
                    'type':'array',
                    'items':ArticleModel,
                }
            }
        }
    })
    @login_required
    def get(self):
        def get_ranked_articles(tx,id):
                return list(tx.run(
                '''
                MATCH (me:User {id: $user_id})-[my:RATED]->(m:Article)
                MATCH (other:User)-[their:RATED]->(m)
                WHERE me <> other
                AND abs(my.rating - their.rating) < 2
                WITH other,m
                MATCH (other)-[otherRating:RATED]->(article:Article)
                WHERE article <> m 
                WITH avg(otherRating.rating) AS avgRating, article
                RETURN article
                ORDER BY avgRating desc
                LIMIT 10
                ''',{'user_id':id}
            ))
        db = get_db()
        result = db.read_transaction(get_ranked_articles,g.user['id'])
        return [serialize_article(record['article']) for record in result]

class ArticleByTag(Resource):
    @swagger.doc({
        'tags':['GetResource'],
        'summary':'find articles by tag',
        'description':'return all articles with this tag',
        'parameters': [
            {
                'name': 'tag',
                'description': 'tag name',
                'in': 'path',
                'type': 'string',
                'required': True
            }
        ],
        'responses':{
            '200':{
                'description':'a list of articles',
                'schema':{
                    'type':'array',
                    'items':ArticleModel,
                }
            }
        }
    })
    def get(self,tag):
        def get_articles_by_tag(tx,tag):
                    return list(tx.run(
                '''
                MATCH (:Tag {name: $name})<-[:HAS_TAG]-(article:Article)
                RETURN article
                ''',{'name':tag}
            ))
        db = get_db()
        result = db.read_transaction(get_articles_by_tag,tag)
        return [serialize_article(record['article']) for record in result] 

class ArticleById(Resource):
    @swagger.doc({
        'tags':['GetResource'],
        'summary':'find articles by id',
        'description':'return all articles with this id',
        'parameters': [
            {
                'name': 'id',
                'description': 'id number',
                'in': 'path',
                'type': 'string',
                'required': True
            }
        ],
        'responses':{
            '200':{
                'description':'target article',
                'schema': ArticleModel,
            },
            '404':{
                'description': 'article not found'
            }
        }
    })
    def get(self,id):
        def get_articles_by_id(tx,id):
                    return list(tx.run(
                '''
                MATCH (article:Article{id : $id })
                RETURN article
                ''',{'id':id}
            ))
        db = get_db()
        result = db.read_transaction(get_articles_by_id,id)
        if result:
             return [serialize_article(record['article']) for record in result] 
        else:
            return {'message': 'article not found'}, 404

class ArticleRelated(Resource):
    @swagger.doc({
        'tags':['GetResource'],
        'summary':'find related article',
        'description':'return all articles related with current article',
        'parameters': [
            {
                'name': 'id',
                'description': 'article id',
                'in': 'path',
                'type': 'string',
                'required': True
            }
        ],
        'responses':{
            '200':{
                'description':'a list of articles',
                'schema':{
                    'type':'array',
                    'items':ArticleModel,
                }
            }
        }
    })
    def get(self,id):
        def get_articles_by_tag(tx,id):
                    return list(tx.run(
                '''
                MATCH(article:Article {id:$id}) 
                OPTIONAL MATCH (article)-[r:HAS_TAG]-(n:Tag)
                UNWIND n as tag
                OPTIONAL MATCH (tag)-[:SUBSUME*1..2]-(p:Tag)
                OPTIONAL MATCH (p)<-[:HAS_TAG]-(res:Article)
                RETURN DISTINCT res LIMIT 5
                ''',{'id':id}
            ))
        db = get_db()
        result = db.read_transaction(get_articles_by_tag,id)
        _.cprint(str(result))
        return [serialize_article(record['res']) for record in result][1:]


class ArticleTouched(Resource):
    @swagger.doc({
        'tags':['Users'],
        'summary':'rate an article',
        'description':'create relationship between user and target',
        'parameters': [
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'required': False,
                'default': 'Token 1a6221b3d04651b09ee96373d1a179c4cb958037',
            },
            {
                'name': 'id',
                'description': 'article id',
                'in': 'path',
                'type': 'string',
            },
            {
                'name': 'body',
                'in': 'body',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'rating': {
                            'type': 'integer',
                        },
                    }
                }
            },
        ],
        'responses': {
            '200': {
                'description': 'rating saved'
            },
            '401': {
                'description': 'invalid / missing authentication'
            }
        }
    })
    @login_required
    def post(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('rating', choices=list(range(0, 6)), type=int, required=True, help='A rating from 0 - 5 inclusive (integers)')
        args = parser.parse_args()
        rating = args['rating']

        def _cypher(tx, user_id, article_id, rating):
            return tx.run(
                '''
                MATCH (u:User {id: $user_id}),(m:Article {id: $article_id})
                MERGE (u)-[r:RATED]->(m)
                SET r.rating = $rating
                RETURN m
                ''', {'user_id': user_id, 'article_id': article_id, 'rating': rating}
            )

        db = get_db()
        results = db.write_transaction(_cypher, g.user['id'], id, rating)
        return 'saved',200

class FavorateArticle(Resource):
    @swagger.doc({
        'tags':['Favorate'],
        'summary':'favorate/unfavorate an article',
        'description':'create FAVORATE relationship between user and target',
        'parameters': [
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'required': True,
                'default': 'Token 1a6221b3d04651b09ee96373d1a179c4cb958037',
            },
            {
                'name': 'id',
                'description': 'article id',
                'in': 'path',
                'type': 'string',
            }
        ],
        'responses': {
            '200': {
                'description': 'saved'
            },
            '401': {
                'description': 'invalid / missing authentication'
            }
        }
    })
    @login_required
    def post(self,id):
        if(g.user['id']==GLOBAL_USER_ID):
            return 'invalid / missing authentication',401
        def _get_favorate(tx,user_id,id):
            return list(tx.run(
                '''
                MATCH (u:User {id: $user_id}),(m:Article {id: $id})
                MATCH (u)-[r:FAVROATE]->(m)
                RETURN r
                ''',{'user_id':user_id,'id':id}
            ))
        def _favorate(tx,user_id,article_id):
            return list(tx.run(
                '''
                MATCH (u:User {id: $user_id}),(m:Article {id: $id})
                MERGE (u)-[r:FAVORATE]->(m)
                RETURN m
                ''',{'user_id':user_id,'id':id}
            ))

        def _unfavorate(tx,user_id,id):
            return list(tx.run(
                '''
                MATCH (u:User {id: $user_id}),(m:Article {id: $id})
                MATCH (u)-[r:FAVORATE]->(m)
                DELETE r
                ''',{'user_id':user_id,'id':id}
            ))
        db = get_db()
        relation = db.read_transaction(_get_favorate,g.user['id'], id)
        if(relation):
            return db.write_transaction(_favorate,g.user['id'], id),200
        else:
            return db.write_transaction(_unfavorate,g.user['id'], id),200

class FavorateArticleList(Resource):
    @swagger.doc({
        'tags':['Favorate'],
        'summary':'favorated article list',
        'description':'Return a list of articles',
        'parameters': [
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'required': True,
                'default': 'Token 1a6221b3d04651b09ee96373d1a179c4cb958037',
            }
        ],
        'responses':{
            '200':{
                'description':'a list of articles',
                'schema':{
                    'type':'array',
                    'items': ArticleModel,
                }
            }
        }
    })
    @login_required
    def get(self):
        if(g.user['id']==GLOBAL_USER_ID):
            return 'invalid / missing authentication',401
        def _cypher(tx,id):
            return list(tx.run(
                '''
                MATCH (u:User {id: $user_id})
                OPTIONAL MATCH (u)-[:FAVORATE]->(a:Article)
                RETURN a
                ''',{'user_id':id}
            ))
        db = get_db()
        result = db.read_transaction(_cypher,g.user['id'])
        return [serialize_article(record['a']) for record in result]
class QueryTitle(Resource):
    @swagger.doc({
        'tags':['Search'],
        'summary':'[INDEX-ONLY]search with title',
        'description':'Return a list of articles',
        'parameters': [
            {
                'name': 'text',
                'description': 'query text',
                'in': 'path',
                'type': 'string',
                'required': True
            },
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'required': False,
                'default': 'Token 1a6221b3d04651b09ee96373d1a179c4cb958037',
            }
        ],
        'responses':{
            '200':{
                'description':'a list of articles',
                'schema':{
                    'type':'array',
                    'items': ArticleModel,
                }
            }
        }
    })
    def get(self,text):
        def search_articles(tx,text):
            return list(tx.run(
                '''
                MATCH (n:Article) WHERE n.title CONTAINS $text RETURN n 
                ''',{'text':text}
            ))
        db = get_db()
        result = db.read_transaction(search_articles,text)
        return [serialize_article(record['n']) for record in result]

class QueryAuthor(Resource):
    @swagger.doc({
        'tags':['Search'],
        'summary':'[INDEX-ONLY]search author name',
        'description':'Return a list of author',
        'parameters': [
            {
                'name': 'text',
                'description': 'query text',
                'in': 'path',
                'type': 'string',
                'required': True
            },
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'required': False,
                'default': 'Token 1a6221b3d04651b09ee96373d1a179c4cb958037',
            }
        ],
        'responses':{
            '200':{
                'description':'a list of authors',
                'schema':{
                    'type':'array',
                    'items': AuthorModel,
                }
            }
        }
    })
    def get(self,text):
        def search_authors(tx,text):
            return list(tx.run(
                '''
                MATCH (n:Author) WHERE n.name CONTAINS $text OR n.username CONTAINS $text RETURN DISTINCT n 
                ''',{'text':text,'text':text}
            ))
        db = get_db()
        result = db.read_transaction(search_authors,text)
        return [serialize_author(record['n']) for record in result]

class QueryTitleAndTags(Resource):
    @swagger.doc({
        'tags':['Search'],
        'summary':'[INDEX-ONLY]search from all titles and tags',
        'description':'Return a list of article',
        'parameters': [
            {
                'name': 'text',
                'description': 'query text',
                'in': 'path',
                'type': 'string',
                'required': True
            },
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'required': False,
                'default': 'Token 1a6221b3d04651b09ee96373d1a179c4cb958037',
            }
        ],
        'responses':{
            '200':{
                'description':'a list of authors',
                'schema':{
                    'type':'array',
                    'items': ArticleModel,
                }
            }
        }
    })
    def get(self,text):
        def search_authors(tx,text):
            return list(tx.run(
                '''
                MATCH (n:Article) WHERE n.title CONTAINS $text OR n.tag_names CONTAINS $text RETURN DISTINCT n 
                ''',{'text':text,'text':text}
            ))
        db = get_db()
        result = db.read_transaction(search_authors,text)
        return [serialize_article(record['n']) for record in result]

class QueryTitleAndTagsAndAuthors(Resource):
    @swagger.doc({
        'tags':['Search'],
        'summary':'[INDEX-ONLY]search from all titles and tags and authors',
        'description':'Return a list of article',
        'parameters': [
            {
                'name': 'text',
                'description': 'query text',
                'in': 'path',
                'type': 'string',
                'required': True
            },
            {
                'name': 'Authorization',
                'in': 'header',
                'type': 'string',
                'required': False,
                'default': 'Token 1a6221b3d04651b09ee96373d1a179c4cb958037',
            }
        ],
        'responses':{
            '200':{
                'description':'a list of articles',
                'schema':{
                    'type':'array',
                    'items': ArticleModel,
                }
            }
        }
    })
    def get(self,text):
        def search(tx,text):
            return list(tx.run(
                '''
                MATCH (n:Article) WHERE n.title CONTAINS $text RETURN DISTINCT n
                UNION ALL
                MATCH (t:Tag) WHERE t.name CONTAINS $text
                UNWIND t as tags
                OPTIONAL MATCH (t)<-[:HAS_TAG]-(article:Article)
                RETURN DISTINCT  article AS n
                UNION ALL 
                MATCH (a:Author) WHERE a.name CONTAINS $text
                UNWIND a as authors
                OPTIONAL MATCH (authors)<-[:WRITTEN_BY]-(article:Article)
                RETURN DISTINCT  article AS n
                ''',{'text':text,'text':text}
            ))
        db = get_db()
        result = db.read_transaction(search,text)
        return [serialize_article(record['n']) for record in result]





api.add_resource(ApiDocs, '/','/docs', '/docs/<path:path>')
#For later use
api.add_resource(GenreList, '/api/v0/genres')
#DB QUERY SAMPLE
# api.add_resource(Movie, '/api/v0/movies/<string:id>')
# api.add_resource(RateMovie, '/api/v0/movies/<string:id>/rate')
# api.add_resource(MovieList, '/api/v0/movies')
# api.add_resource(MovieListByGenre, '/api/v0/movies/genre/<string:genre_id>/')
# api.add_resource(MovieListByDateRange, '/api/v0/movies/daterange/<int:start>/<int:end>')
# api.add_resource(MovieListByPersonActedIn, '/api/v0/movies/acted_in_by/<string:person_id>')
# api.add_resource(MovieListByWrittenBy, '/api/v0/movies/written_by/<string:person_id>')
# api.add_resource(MovieListByDirectedBy, '/api/v0/movies/directed_by/<string:person_id>')
# api.add_resource(MovieListRatedByMe, '/api/v0/movies/rated')
# api.add_resource(MovieListRecommended, '/api/v0/movies/recommended')
# api.add_resource(Person, '/api/v0/people/<string:id>')
# api.add_resource(PersonList, '/api/v0/people')
# api.add_resource(PersonBacon, '/api/v0/people/bacon')

#GET CACHE
#api.add_resource(Cache,'/api/v0/query/page/<int:start>/')

#HomePage
api.add_resource(RankedArticles,'/api/v1/articles/recommended/')


#Archive
api.add_resource(ArticleList,'/api/v1/articles/page=<string:page>')


#GetResource
api.add_resource(ArticleByTag,'/api/v1/query/articles/with_tag/<string:tag>')
api.add_resource(ArticleById,'/api/v1/query/articles/with_id/<string:id>')
api.add_resource(ArticleRelated,'/api/v1/query/articles/about/<string:id>')
api.add_resource(AuthorList,'/api/v1/authors')
api.add_resource(TagList,'/api/v1/tags')
api.add_resource(ArticleByAuthor,'/api/v1/query/articles/by/<string:name>')
#USER
api.add_resource(Register, '/api/v1/register')
api.add_resource(Login, '/api/v1/login')
api.add_resource(UserMe, '/api/v1/users/me')
#USER ACTIONS
api.add_resource(ArticleTouched,'/api/v0/query/user/rated/<string:id>')


#Check
api.add_resource(TestSwagger,'/api/v1/check')

#Search
api.add_resource(QueryTitle,'/api/v1/search/index_only/article_title_contains/<string:text>')
api.add_resource(QueryAuthor,'/api/v1/search/index_only/author_name_contains/<string:text>')
api.add_resource(QueryTitleAndTags,'/api/v1/search/index_only/titleOrTag_name_contains/<string:text>')


#Favorate
api.add_resource(FavorateArticle,'/api/v1/favorate/<string:id>')
api.add_resource(FavorateArticleList,'/api/v1/favoratelist')
