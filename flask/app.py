from flask import Flask
from flask import session
from waitress import serve
from flask import render_template
from flask import request, url_for, redirect, flash, make_response
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect
from database import db
from flask_session import Session
import logging
import os
import datetime
import hashlib

from formLogin import LoginForm
from formFicha import FichaForm
from formEmprestimo import EmprestimoForm
from formUsuario import UsuarioForm
from formLivro import LivroForm
from ficha import Ficha
from emprestimo import Emprestimo
from usuario import Usuario
from livro import Livro


app = Flask(__name__)
bootstrap = Bootstrap(app)
CSRFProtect(app)
CSV_DIR = '/flask/'

logging.basicConfig(filename='/flask/app.log', filemode='w', format='%(asctime)s %(name)s - %(levelname)s - %(message)s',level=logging.DEBUG)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = os.urandom(24)
app.config['WTF_CSRF_SSL_STRICT'] = False
Session(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + CSV_DIR + 'bd.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.before_first_request
def inicializar_bd():
    db.create_all()

@app.route('/')
def root():
    return (render_template('index.html'))
        
@app.route('/livro/cadastrar', methods=['POST','GET'])
def cadastrar_livro():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!')
        return(redirect(url_for('login')))
    form = LivroForm()
    if form.validate_on_submit():
        titulo = request.form['titulo']
        autor = request.form['autor']
        genero = request.form['genero']
        novoLivro = Livro(titulo=titulo,
                            autor=autor, 
                            genero=genero)
        db.session.add(novoLivro)
        db.session.commit()
        flash(u'Livro cadastrado com sucesso!')
        return(redirect(url_for('root')))
    return (render_template('form.html', form=form, action=url_for('cadastrar_livro')))

@app.route('/livro/listar')
def listar_livros():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!')
        return(redirect(url_for('login')))
    livros = Livro.query.order_by(Livro.titulo).all()
    return(render_template('livros.html', livros=livros))


@app.route('/usuario/cadastrar', methods=['POST','GET'])
def cadastrar_usuario():
    form = UsuarioForm()
    if form.validate_on_submit():
        nome = request.form['nome']
        username = request.form['username']
        email = request.form['email']
        telefone = request.form['telefone']
        senha = request.form['senha']
        senhahash = hashlib.sha1(senha.encode('utf8')).hexdigest()
        admin = False
        try:
            if request.form['admin'] == 'y':
                admin = True
        except:
            admin = False
        novoUsuario = Usuario(nome=nome,
                                username=username,
                                email=email,
                                telefone=telefone,
                                senha=senhahash,
                                admin=admin)
        db.session.add(novoUsuario)
        db.session.commit()
        flash(u'Usuário cadastrado com sucesso!')
        return(redirect(url_for('root')))
    return (render_template('form.html', form=form, action=url_for('cadastrar_usuario')))

@app.route('/usuario/listar')
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return(render_template('usuarios.html', usuarios=usuarios))

@app.route('/livro/emprestimo', methods=['POST','GET'])
def emprestar_livro():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!')
        return(redirect(url_for('login')))
    form = EmprestimoForm()
    fichas = Ficha.query.order_by(Ficha.nome).all()
    livros = Livro.query.filter(Livro.disponivel==True).order_by(Livro.titulo).all()
    form.ficha.choices = [(f.id, f.nome) for f in fichas]
    form.livro.choices = [(l.id, l.titulo) for l in livros]
    if form.validate_on_submit():
        id_ficha = int(request.form['ficha'])
        id_livro = int(request.form['livro'])
        novoEmprestimo = Emprestimo(id_usuario=int(session['usuario']),
                                    id_ficha=id_ficha,
                                    id_livro=id_livro)
        livroAlterado = Livro.query.get(id_livro)
        livroAlterado.disponivel = False
        db.session.add(novoEmprestimo)
        db.session.commit()
        flash(u'Empréstimo realizado com sucesso!')
        return(redirect(url_for('root')))
    return(render_template('form.html',form=form,action=url_for('emprestar_livro')))

@app.route('/livro/emprestimo/listar')
def listar_emprestimos():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!')
        return(redirect(url_for('login')))
    emprestimos = Emprestimo.query.order_by(Emprestimo.data_emprestimo.desc()).all()
    return(render_template('emprestimos.html', emprestimos=emprestimos))

@app.route('/livro/devolver/<id_emprestimo>', methods=['POST','GET'])
def devolver_emprestimo(id_emprestimo):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!')
        return(redirect(url_for('login')))
    id_emprestimo = int(id_emprestimo)
    emprestimo = Emprestimo.query.get(id_emprestimo)
    emprestimo.data_devolucao = datetime.datetime.now()
    livro = Livro.query.get(emprestimo.id_livro)
    if livro.disponivel == True:
        flash(u'O livro já foi devolvido!')
    else:
        livro.disponivel = True
        flash(u'Livro devolvido com sucesso!')
    db.session.commit()
    return (redirect(url_for('root')))

@app.route('/livro/remover/<id_emprestimo>', methods=['POST','GET'])
def remover_emprestimo(id_emprestimo):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!')
        return(redirect(url_for('login')))
    id_emprestimo = int(id_emprestimo)
    emprestimo = Emprestimo.query.get(id_emprestimo)
    id_livro = emprestimo.id_livro
    livro = Livro.query.get(id_livro)
    livro.disponivel = True
    db.session.delete(emprestimo)
    db.session.commit()
    return (redirect(url_for('root')))

@app.route('/ficha/cadastrar', methods=['POST','GET'])
def cadastrar_ficha():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!')
        return(redirect(url_for('login')))
    form = FichaForm()
    if form.validate_on_submit():
        nome = request.form['nome']
        cpf = request.form['cpf']
        email = request.form['email']
        novaFicha = Ficha(nome=nome,
                            cpf=cpf,
                            email=email)
        db.session.add(novaFicha)
        db.session.commit()
        flash(u'Ficha cadastrada com sucesso!')
        return(redirect(url_for('root')))
    return (render_template('form.html', form=form, action=url_for('cadastrar_ficha')))

@app.route('/ficha/listar')
def listar_fichas():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!')
        return(redirect(url_for('login')))
    fichas = Ficha.query.order_by(Ficha.nome).all()
    return(render_template('fichas.html', fichas=fichas))

@app.route('/usuario/login',methods=['POST','GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = request.form['usuario']
        senha = request.form['senha']
        senhahash = hashlib.sha1(senha.encode('utf8')).hexdigest()
        linha = Usuario.query.filter(Usuario.username==usuario,Usuario.senha==senhahash).all()
        if (len(linha) > 0):
            session['autenticado'] = True
            session['usuario'] = linha[0].id
            session['username'] = linha[0].username
            session['admin'] = linha[0].admin
            flash(u'Usuário autenticado com sucesso!')
            return(redirect(url_for('root')))
        else:
            flash(u'Usuário ou senha não conferem!')
            return(redirect(url_for('login')))
    return (render_template('form.html', form=form, action=url_for('login')))

@app.route('/usuario/logout',methods=['POST','GET'])
def logout():
    session.clear()
    return(redirect(url_for('root')))

if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=80, url_prefix='/app')