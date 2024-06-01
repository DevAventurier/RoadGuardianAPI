from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import datetime
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash

# Initialisation de l'application Flask
app = Flask(__name__)
Bootstrap(app)

# Configuration de la clé secrète et de la base de données
app.secret_key = "Secret Key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:93017539@localhost/charityv2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'

# Initialisation des extensions Flask
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# ============================= Modèles de la base de données

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password)

class Critere(db.Model):
    __tablename__ = 'criteres'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(100), nullable=False)

    def __init__(self, nom, description):
        self.nom = nom
        self.description = description

class Agent(db.Model):
    __tablename__ = 'agents'
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(100), unique=True, nullable=False)
    mail = db.Column(db.String(100), unique=True, nullable=False)
    telephone = db.Column(db.String(20), nullable=False)

    def __init__(self, matricule, mail, telephone):
        self.matricule = matricule
        self.mail = mail
        self.telephone = telephone

class Amande(db.Model):
    __tablename__ = 'amandes'
    id = db.Column(db.Integer, primary_key=True)
    montant = db.Column(db.Float, nullable=False)
    status = db.Column(db.Boolean, default=False)
    controle_routier_id = db.Column(db.Integer, db.ForeignKey('controles_routiers.id'), nullable=False)
    controle_routier = db.relationship('ControleRoutier', backref=db.backref('amandes', lazy=True))

    def __init__(self, montant, status, controle_routier):
        self.montant = montant
        self.status = status
        self.controle_routier = controle_routier

class PointDeControle(db.Model):
    __tablename__ = 'points_de_controle'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    ville = db.Column(db.String(100), nullable=False)
    quartier = db.Column(db.String(100), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    agent = db.relationship('Agent', backref=db.backref('points_de_controle', lazy=True))

    def __init__(self, nom, ville, quartier, agent):
        self.nom = nom
        self.ville = ville
        self.quartier = quartier
        self.agent = agent

class ControleRoutier(db.Model):
    __tablename__ = 'controles_routiers'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    nom_prenom = db.Column(db.String(100), nullable=False)
    type_piece = db.Column(db.String(50), nullable=False)
    type_vehicule = db.Column(db.String(50), nullable=False)
    numero_piece = db.Column(db.String(100), nullable=False)
    immatriculation = db.Column(db.String(20), nullable=False)
    telephone_conducteur = db.Column(db.String(20), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    agent = db.relationship('Agent', backref=db.backref('controles_routiers', lazy=True))
    point_de_controle_id = db.Column(db.Integer, db.ForeignKey('points_de_controle.id'), nullable=False)
    point_de_controle = db.relationship('PointDeControle', backref=db.backref('controles_routiers', lazy=True))
    critere_id = db.Column(db.Integer, db.ForeignKey('criteres.id'), nullable=True)
    critere = db.relationship('Critere', backref=db.backref('controles_routiers', lazy=True))

    def __init__(self, date, nom_prenom, type_piece, type_vehicule, numero_piece, immatriculation, telephone_conducteur, agent, point_de_controle, critere=None):
        self.date = date
        self.nom_prenom = nom_prenom
        self.type_piece = type_piece
        self.type_vehicule = type_vehicule
        self.numero_piece = numero_piece
        self.immatriculation = immatriculation
        self.telephone_conducteur = telephone_conducteur
        self.agent = agent
        self.point_de_controle = point_de_controle
        self.critere = critere

class CritereByControle(db.Model):
    __tablename__ = 'criteres_by_controle'
    id = db.Column(db.Integer, primary_key=True)
    critere_id = db.Column(db.Integer, db.ForeignKey('criteres.id'), nullable=False)
    controle_routier_id = db.Column(db.Integer, db.ForeignKey('controles_routiers.id'), nullable=False)
    critere = db.relationship('Critere', backref=db.backref('criteres_by_controle', lazy=True))
    controle_routier = db.relationship('ControleRoutier', backref=db.backref('criteres_by_controle', lazy=True))

    def __init__(self, critere, controle_routier):
        self.critere = critere
        self.controle_routier = controle_routier

class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), nullable=False)

    def __init__(self, jti):
        self.jti = jti

    def add(self):
        db.session.add(self)
        db.session.commit()

# =================  Initialiser la base de données
with app.app_context():
    db.create_all()

# =================  Méthode utilitaire pour convertir les objets en dictionnaire
def as_dict(self):
    return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# =================  Ajout de la méthode utilitaire à chaque modèle
User.as_dict = as_dict
Critere.as_dict = as_dict
Agent.as_dict = as_dict
Amande.as_dict = as_dict
PointDeControle.as_dict = as_dict
ControleRoutier.as_dict = as_dict
CritereByControle.as_dict = as_dict

# ============================================ Route pour la page de connexion
@app.route('/')
def home():
    return render_template('login.html')

# ============================================= Route pour la page du tableau de bord
@app.route('/dashboard')
def dashboard():
    return render_template('users.html')

# ============================================ Route API pour l'enregistrement des utilisateurs

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

# ============================================================== Route API pour la connexion des utilisateurs
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid username or password'}), 401

    access_token = create_access_token(identity=user.username)
    return jsonify({'access_token': access_token}), 200

    access_token = create_access_token(identity=user.username)
    # Rediriger vers le dashboard après la connexion réussie
    return redirect(url_for('dashboard'))

# ============================================================== Route API pour la déconnexion des utilisateurs
@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    revoked_token = RevokedToken(jti=jti)
    revoked_token.add()
    return jsonify({"message": "Déconnexion réussie"}), 200

# ============================================================== Fonction pour vérifier si un token est révoqué
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    token = RevokedToken.query.filter_by(jti=jti).first()
    return token is not None
# ============================================================== html user
@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.as_dict() for user in users])

@app.route('/api/user/<int:id>', methods=['GET'])
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.as_dict())

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    new_user = User(username=data['username'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify(new_user.as_dict()), 201

@app.route('/api/user/<int:id>', methods=['PUT'])
def update_user(id):
    data = request.get_json()
    user = User.query.get_or_404(id)
    user.username = data['username']
    user.password = data['password']
    db.session.commit()
    return jsonify(user.as_dict())

@app.route('/api/user/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return '', 204

# ============================================================== Routes API CRUD pour Critere

@app.route('/api/critere', methods=['GET'])
#@jwt_required() #pour securiser la route / @login_required
def get_criteres():
    criteres = Critere.query.all()
    return jsonify([critere.as_dict() for critere in criteres])
    #return render_template('critere.html', criteres=criteres)

@app.route('/api/critere/<int:id>', methods=['GET'])
def get_critere(id):
    critere = Critere.query.get(id)
    return jsonify(critere.as_dict())

@app.route('/api/critere', methods=['POST'])
def create_critere():
    data = request.get_json()
    nom = data.get('nom')
    description = data.get('description')
    critere = Critere(nom=nom, description=description)
    db.session.add(critere)
    db.session.commit()
    return jsonify(critere.as_dict()), 201

@app.route('/api/critere/<int:id>', methods=['PUT'])
def update_critere(id):
    data = request.get_json()
    critere = Critere.query.get(id)
    critere.nom = data.get('nom')
    critere.description = data.get('description')
    db.session.commit()
    return jsonify(critere.as_dict())

@app.route('/api/critere/<int:id>', methods=['DELETE'])
def delete_critere(id):
    critere = Critere.query.get(id)
    db.session.delete(critere)
    db.session.commit()
    return jsonify({'message': 'Critère supprimé avec succès'})

# ============================================================== Routes API CRUD pour Agent
@app.route('/api/agent', methods=['GET'])
def get_agents():
    agents = Agent.query.all()
    return jsonify([agent.as_dict() for agent in agents])

@app.route('/api/agent/<int:id>', methods=['GET'])
def get_agent(id):
    agent = Agent.query.get(id)
    return jsonify(agent.as_dict())

@app.route('/api/agent', methods=['POST'])
def create_agent():
    data = request.get_json()
    matricule = data.get('matricule')
    mail = data.get('mail')
    telephone = data.get('telephone')
    agent = Agent(matricule=matricule, mail=mail, telephone=telephone)
    db.session.add(agent)
    db.session.commit()
    return jsonify(agent.as_dict()), 201

@app.route('/api/agent/<int:id>', methods=['PUT'])
def update_agent(id):
    data = request.get_json()
    agent = Agent.query.get(id)
    agent.matricule = data.get('matricule')
    agent.mail = data.get('mail')
    agent.telephone = data.get('telephone')
    db.session.commit()
    return jsonify(agent.as_dict())

@app.route('/api/agent/<int:id>', methods=['DELETE'])
def delete_agent(id):
    agent = Agent.query.get(id)
    db.session.delete(agent)
    db.session.commit()
    return jsonify({'message': 'Agent supprimé avec succès'})

# ============================================================== Routes API CRUD pour Amande
@app.route('/api/amande', methods=['GET'])
def get_amandes():
    amandes = Amande.query.all()
    return jsonify([amande.as_dict() for amande in amandes])

@app.route('/api/amande/<int:id>', methods=['GET'])
def get_amande(id):
    amande = Amande.query.get(id)
    return jsonify(amande.as_dict())

@app.route('/api/amande', methods=['POST'])
def create_amande():
    data = request.get_json()
    montant = data.get('montant')
    status = data.get('status', False)
    controle_routier_id = data.get('controle_routier_id')
    controle_routier = ControleRoutier.query.get(controle_routier_id)
    amande = Amande(montant=montant, status=status, controle_routier=controle_routier)
    db.session.add(amande)
    db.session.commit()
    return jsonify(amande.as_dict()), 201

@app.route('/api/amande/<int:id>', methods=['PUT'])
def update_amande(id):
    data = request.get_json()
    amande = Amande.query.get(id)
    amande.montant = data.get('montant')
    amande.status = data.get('status', amande.status)
    controle_routier_id = data.get('controle_routier_id')
    amande.controle_routier = ControleRoutier.query.get(controle_routier_id)
    db.session.commit()
    return jsonify(amande.as_dict())


@app.route('/api/amande/<int:id>', methods=['DELETE'])
def delete_amande(id):
    amande = Amande.query.get(id)
    db.session.delete(amande)
    db.session.commit()
    return jsonify({'message': 'Amande supprimée avec succès'})

# ============================================================== Routes API CRUD pour PointDeControle
@app.route('/api/point_de_controle', methods=['GET'])
def get_points_de_controle():
    points_de_controle = PointDeControle.query.all()
    return jsonify([point_de_controle.as_dict() for point_de_controle in points_de_controle])

@app.route('/api/point_de_controle/<int:id>', methods=['GET'])
def get_point_de_controle(id):
    point_de_controle = PointDeControle.query.get(id)
    return jsonify(point_de_controle.as_dict())

@app.route('/api/point_de_controle', methods=['POST'])
def create_point_de_controle():
    data = request.get_json()
    nom = data.get('nom')
    ville = data.get('ville')
    quartier = data.get('quartier')
    agent_id = data.get('agent_id')
    agent = Agent.query.get(agent_id)
    point_de_controle = PointDeControle(nom=nom, ville=ville, quartier=quartier, agent=agent)
    db.session.add(point_de_controle)
    db.session.commit()
    return jsonify(point_de_controle.as_dict()), 201

@app.route('/api/point_de_controle/<int:id>', methods=['PUT'])
def update_point_de_controle(id):
    data = request.get_json()
    point_de_controle = PointDeControle.query.get(id)
    point_de_controle.nom = data.get('nom')
    point_de_controle.ville = data.get('ville')
    point_de_controle.quartier = data.get('quartier')
    agent_id = data.get('agent_id')
    point_de_controle.agent = Agent.query.get(agent_id)
    db.session.commit()
    return jsonify(point_de_controle.as_dict())

@app.route('/api/point_de_controle/<int:id>', methods=['DELETE'])
def delete_point_de_controle(id):
    point_de_controle = PointDeControle.query.get(id)
    db.session.delete(point_de_controle)
    db.session.commit()
    return jsonify({'message': 'Point de contrôle supprimé avec succès'})

# ============================================================== Routes API CRUD pour ControleRoutier
@app.route('/api/controle_routier', methods=['GET'])
def get_controles_routiers():
    controles_routiers = ControleRoutier.query.all()
    return jsonify([controle_routier.as_dict() for controle_routier in controles_routiers])

@app.route('/api/controle_routier/<int:id>', methods=['GET'])
def get_controle_routier(id):
    controle_routier = ControleRoutier.query.get(id)
    return jsonify(controle_routier.as_dict())

@app.route('/api/controle_routier', methods=['POST'])
def create_controle_routier():
    data = request.get_json()
    date = datetime.datetime.strptime(data.get('date'), '%Y-%m-%d %H:%M:%S')
    nom_prenom = data.get('nom_prenom')
    type_piece = data.get('type_piece')
    type_vehicule = data.get('type_vehicule')
    numero_piece = data.get('numero_piece')
    immatriculation = data.get('immatriculation')
    telephone_conducteur = data.get('telephone_conducteur')
    agent_id = data.get('agent_id')
    point_de_controle_id = data.get('point_de_controle_id')
    critere_id = data.get('critere_id')

    agent = Agent.query.get(agent_id)
    point_de_controle = PointDeControle.query.get(point_de_controle_id)
    critere = Critere.query.get(critere_id) if critere_id else None

    controle_routier = ControleRoutier(
        date=date,
        nom_prenom=nom_prenom,
        type_piece=type_piece,
        type_vehicule=type_vehicule,
        numero_piece=numero_piece,
        immatriculation=immatriculation,
        telephone_conducteur=telephone_conducteur,
        agent=agent,
        point_de_controle=point_de_controle,
        critere=critere
    )
    db.session.add(controle_routier)
    db.session.commit()
    return jsonify(controle_routier.as_dict()), 201

@app.route('/api/controle_routier/<int:id>', methods=['PUT'])
def update_controle_routier(id):
    data = request.get_json()
    controle_routier = ControleRoutier.query.get(id)
    controle_routier.date = datetime.datetime.strptime(data.get('date'), '%Y-%m-%d %H:%M:%S')
    controle_routier.nom_prenom = data.get('nom_prenom')
    controle_routier.type_piece = data.get('type_piece')
    controle_routier.type_vehicule = data.get('type_vehicule')
    controle_routier.numero_piece = data.get('numero_piece')
    controle_routier.immatriculation = data.get('immatriculation')
    controle_routier.telephone_conducteur = data.get('telephone_conducteur')
    agent_id = data.get('agent_id')
    controle_routier.agent = Agent.query.get(agent_id)
    point_de_controle_id = data.get('point_de_controle_id')
    controle_routier.point_de_controle = PointDeControle.query.get(point_de_controle_id)
    critere_id = data.get('critere_id')
    controle_routier.critere = Critere.query.get(critere_id) if critere_id else None
    db.session.commit()
    return jsonify(controle_routier.as_dict())

@app.route('/api/controle_routier/<int:id>', methods=['DELETE'])
def delete_controle_routier(id):
    controle_routier = ControleRoutier.query.get(id)
    db.session.delete(controle_routier)
    db.session.commit()
    return jsonify({'message': 'Contrôle routier supprimé avec succès'})

# ============================================================== END ============================================================== #

if __name__ == '__main__':
    app.run(debug=True)
