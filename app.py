from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float
import os
from flask_marshmallow import Marshmallow
# need a method to allow access the existing users
from flask_jwt_extended import JWTManager,jwt_required,create_access_token
from flask_mail import Mail,Message

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'planets.db')
app.config['JWT_SECRET_KEY'] = 'the-secret' # change this to UUID in real life
# implement the email sending
app.config['MAIL_SERVER'] = 'smtp.mailtrap.io'
app.config['MAIL_USERNAME'] = os.environ['MAIL_USERNAME'] # use environment variables
app.config['MAIL_PASSWORD'] = os.environ['MAIL_PASSWORD']
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)
#initialize jwt manager
jwt = JWTManager(app)
mail = Mail(app)

@app.cli.command('db_create')
def db_create():
    db.create_all()
    print('Database created!')


@app.cli.command('db_drop')
def db_drop():
    db.drop_all()
    print('Database dropped!')


@app.cli.command('db_seed')
def db_seed():
    mercury = Planet(planet_name='Mercury',
                     planet_type='Class D',
                     home_star='Sol',
                     mass=2.258e23,
                     radius=1516,
                     distance=35.98e6)

    venus = Planet(planet_name='Venus',
                         planet_type='Class K',
                         home_star='Sol',
                         mass=4.867e24,
                         radius=3760,
                         distance=67.24e6)

    earth = Planet(planet_name='Earth',
                     planet_type='Class M',
                     home_star='Sol',
                     mass=5.972e24,
                     radius=3959,
                     distance=92.96e6)

    db.session.add(mercury)
    db.session.add(venus)
    db.session.add(earth)

    test_user = User(first_name='William',
                     last_name='Herschel',
                     email='test@test.com',
                     password='P@ssw0rd')

    db.session.add(test_user)
    db.session.commit()
    print('Database seeded!')




@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/super_simple')
def super_simple():
    return jsonify(message='Hello from the Planetary API.'), 200


@app.route('/not_found')
def not_found():
    return jsonify(message='That resource was not found'), 404


@app.route('/parameters')
def parameters():
    name = request.args.get('name')
    age = int(request.args.get('age'))
    if age < 18:
        return jsonify(message="Sorry " + name + ", you are not old enough."), 401
    else:
        return jsonify(message="Welcome " + name + ", you are old enough!")


@app.route('/url_variables/<string:name>/<int:age>')
def url_variables(name: str, age: int):
    if age < 18:
        return jsonify(message="Sorry " + name + ", you are not old enough."), 401
    else:
        return jsonify(message="Welcome " + name + ", you are old enough!")


@app.route('/planets', methods=['GET'])
def planets():
    planets_list = Planet.query.all()
    #return jsonify(data=planets_list)
    # deserialize the planets objects
    result = planets_schema.dumps(planets_list)
    return jsonify(result)

# add a route to register user
@app.route('/register', methods=['POST'])
def register():
    # assume data came from html form at the front eds
    email = request.form['email']
    # check if user exists using the email
    test = User.query.filter_by(email=email).first()
    if test:
        return jsonify(message="Email already exists"),409
    else:
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        # create user object
        user = User(first_name=first_name,last_name=last_name,email=email,password=password)
        db.session.add(user)
        db.session.commit()
        return jsonify(message='user created successfully'),201

# crate a route for login
@app.route('/login',methods=['POST'])
def login():
    if request.is_json:
        email = request.json['email']
        password = request.json['password']
    else:
        email = request.form['email']
        password = request.form['password']

    test = User.query.filter_by(email=email,password=password).first()
    if test:
        access_token = create_access_token(identity=email)
        return jsonify(message='Login successfully',access_token=access_token)
    else:
        return jsonify(message='Bad Email or password'),401

# sending email with the password
@app.route('/retrieve_password/<string:email>',methods=['GET'])
def retrieve_password(email:str):
    user = User.query.filter_by(email=email).first()
    if user:
        msg = Message("Your planetary API password is "+user.password,sender="admin@planetary-api.com",recipients=[email])
        mail.send(msg)
        return jsonify(message="Password sent to "+email)
    else:
        return jsonify(message="That email address does not exists")

# get a planet
@app.route('/planet_details/<int:planet_id>',methods=['GET'])
def planet_details(planet_id:int):
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        result = planet_schema.dumps(planet)
        return jsonify(result)
    else:
        return jsonify(message="Planet does not exists"),404

# add a planet # need login
@app.route('/add_planet',methods=['POST'])
@jwt_required() 
def add_planet():
    planet_name = request.form['planet_name']
    test = Planet.query.filter_by(planet_name=planet_name).first()
    if test:
        return jsonify(Message="Planet already exists in DB"),409
    else:
        planet_type = request.form['planet_type']
        home_star = request.form['home_star']
        mass = float(request.form['mass'])
        radius = float(request.form['radius'])
        distance = float(request.form['distance'])

        new_planet = Planet(planet_name=planet_name,planet_type=planet_type,home_star=home_star,mass=mass,radius=radius,distance=distance)
        db.session.add(new_planet)
        db.session.commit()
        return jsonify(message="New planet is added"),201


@app.route('/update_planet',methods=['PUT'])
@jwt_required()
def update_planet():
    planet_id = int(request.form['planet_id'])
    planet = Planet.query.filter_by(planet_id=planet_id)
    if planet:
        planet.planet_name = request.form['planet_name']
        planet.planet_type = request.form['planet_type']
        planet.home_star = request.form['home_star']
        planet.mass = float(request.form['mass'])
        planet.radius = float(request.form['radius'])
        planet.distance = float(request.form['distance'])
        db.session.commit()
        return jsonify(message="Updated planet details successfully"),202
    else:
        return jsonify(Message="That planet does not exist"),404

# delete
@app.route('/remove_planet/<int:planet_id>',methods=['DELETE'])
@jwt_required()
def remove_planet(planet_id:int):
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        db.session.delete(planet)
        db.session.commit()
        return jsonify(message="You delete the planet"),202
    else:
        return jsonify(message="Planet does not exist"),404


# database models
class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)


class Planet(db.Model):
    __tablename__ = 'planets'
    planet_id = Column(Integer, primary_key=True)
    planet_name = Column(String)
    planet_type = Column(String)
    home_star = Column(String)
    mass = Column(Float)
    radius = Column(Float)
    distance = Column(Float)

# create some indicator for mashmellow to show what field is it looking for
class UserSchema(ma.Schema):
    # inner class
    class Meta:
        fields = ('id','first_name','last_name','email','password')

class PlanetSchema(ma.Schema):
    class Meta:
        fields = ('planet_id','planet_name','planet_type','home_star','mass','radius','distance')

# initialize for deserialize one or more objects
user_schema = UserSchema()
users_schema = UserSchema(many=True)

planet_schema = PlanetSchema()
planets_schema = PlanetSchema(many=True)

if __name__ == '__main__':
    app.run()
