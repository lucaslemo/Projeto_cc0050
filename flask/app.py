from flask import Flask
from flask import session
from waitress import serve
from flask import render_template
from flask import request, url_for, redirect, flash, make_response
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect
from database import db
from flask_session import Session
from flask_json import FlaskJSON, JsonError, json_response, as_json
from sqlalchemy import func
from unidecode import unidecode
import logging
import os
import datetime
import hashlib
import json

from formLogin import LoginForm
from formFicha import FichaForm
from formBusca import BuscaForm
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
app.config['WTF_CSRF_ENABLED'] = True
Session(app)
FlaskJSON(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + CSV_DIR + 'bd.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
db.init_app(app)

@app.before_first_request
def inicializar_bd():
    db.create_all()

@app.route('/')
def root():
    return (render_template('index.html'))

'''
    Rotas para os Livros
'''

@app.route('/livro/cadastrar', methods=['POST','GET'])
def cadastrar_livro():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
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
        flash(u'Livro cadastrado com sucesso!', category='info')
        return(redirect(url_for('root')))
    return (render_template('formCadastroLivro.html',
                                csrf_enabled=app.config['WTF_CSRF_ENABLED'],
                                form=form, 
                                action=url_for('cadastrar_livro')))

@app.route('/livro/listar', methods=['POST','GET'])
def listar_livros():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    form = BuscaForm()
    if form.validate_on_submit():
        livros_teste = Livro.query.order_by(Livro.titulo).all()
        livros = list()
        campo_busca = request.form['campo']
        try:
            campo_id = int(campo_busca)
            for livro in livros_teste:
                if campo_id == livro.id:
                    livros.append(livro)
                elif unidecode(campo_busca).upper() == unidecode(livro.titulo).upper():
                    livros.append(livro)
                elif unidecode(campo_busca).upper() == unidecode(livro.autor).upper():
                    livros.append(livro)
                elif unidecode(campo_busca).upper() == unidecode(livro.genero).upper():
                    livros.append(livro)
        except:
            for livro in livros_teste:
                if unidecode(campo_busca).upper() == unidecode(livro.titulo).upper():
                    livros.append(livro)
                elif unidecode(campo_busca).upper() == unidecode(livro.autor).upper():
                    livros.append(livro)
                elif unidecode(campo_busca).upper() == unidecode(livro.genero).upper():
                    livros.append(livro)
        if len(livros) == 0:
            flash(u'Nenhum item corresponde ao valor pesquisado!', category='warning')
        return(render_template('livros.html', livros=livros, form=form, action=url_for('listar_livros')))
    livros = Livro.query.order_by(Livro.titulo).all()
    return(render_template('livros.html', livros=livros, form=form, action=url_for('listar_livros')))


@app.route('/livro/remover/<id_livro>', methods=['POST','GET'])
def remover_livro(id_livro):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    if session['admin'] == True:
        id_livro = int(id_livro)
        livro = Livro.query.get(id_livro)
        if livro.disponivel == True:
            db.session.delete(livro)
            db.session.commit()
            flash(u'Livro removido com sucesso!', category='info')
            return (redirect(url_for('listar_livros')))
        flash(u'O livro precisa estar disponível!', category='warning')
        return (redirect(url_for('listar_livros')))
    flash(u'Apenas administradores podem remover livros!', category='warning')
    return (redirect(url_for('root')))

@app.route('/livro/listar/json')
def listar_livros_json():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    livros = Livro.query.order_by(Livro.id).all()
    resultado = json.dumps([ row.asdict() for row in livros ])
    return(resultado)

@app.route('/livro/<titulo>')
def buscar_livros(titulo):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    lista_livros = Livro.query.filter(func.upper(Livro.titulo)==titulo.upper()).all()
    if len(lista_livros) > 0:
        resultado = json.dumps([ row.asdict() for row in lista_livros ])
        return resultado
    return json.dumps([ {"id": 0, "titulo" : "Not Found"} ])

'''
    Rotas para os Usuários
'''

@app.route('/usuario/cadastrar', methods=['POST','GET'])
def cadastrar_usuario():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    if session['admin'] == True:
        form = UsuarioForm()
        if form.validate_on_submit():
            nome = request.form['nome']
            username = request.form['username']
            email = request.form['email']
            telefone = request.form['telefone']
            senha = request.form['senha']
            senhahash = hashlib.sha1(senha.encode('utf8')).hexdigest()
            admin = False
            linha = Usuario.query.filter((Usuario.username==username) | (Usuario.email==email)).all()
            if len(linha) == 0:
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
                flash(u'Usuário cadastrado com sucesso!', category='info')
                return(redirect(url_for('root')))
            else:
                flash(u'Já existe um usuário cadastrado com esse Nome de usuário ou E-mail', category='warning')
        return (render_template('formCadastroUsuario.html',
                                    csrf_enabled=app.config['WTF_CSRF_ENABLED'],
                                    form=form,
                                    action=url_for('cadastrar_usuario')))
    flash(u'Apenas administradores podem cadastrar novos usuários!', category='warning')
    return (redirect(url_for('root')))

@app.route('/usuario/listar', methods=['POST','GET'])
def listar_usuarios():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    if session['admin'] == True:
        form = BuscaForm()
        if form.validate_on_submit():
            usuarios_teste = Usuario.query.order_by(Usuario.nome).all()
            usuarios = list()
            campo_busca = request.form['campo']
            try:
                campo_id = int(campo_busca)
                for usuario in usuarios_teste:
                    if campo_id == usuario.id:
                        usuarios.append(usuario)
                    elif unidecode(campo_busca).upper() == unidecode(usuario.nome).upper():
                        usuario.append(usuario)
                    elif unidecode(campo_busca).upper() == unidecode(usuario.username).upper():
                        usuarios.append(usuario)
            except:
                for usuario in usuarios_teste:
                    if unidecode(campo_busca).upper() == unidecode(usuario.nome).upper():
                        usuarios.append(usuario)
                    elif unidecode(campo_busca).upper() == unidecode(usuario.username).upper():
                        usuarios.append(usuario)
            if len(usuarios) == 0:
                    flash(u'Nenhum item corresponde ao valor pesquisado!', category='warning')
            return(render_template('usuarios.html', usuarios=usuarios, form=form, action=url_for('listar_usuarios')))
        usuarios = Usuario.query.order_by(Usuario.nome).all()
        return(render_template('usuarios.html', usuarios=usuarios, form=form, action=url_for('listar_usuarios')))
    flash(u'Apenas administradores podem listar os usuários cadastrados!', category='warning')
    return (redirect(url_for('root')))

@app.route('/usuario/remover/<id_usuario>', methods=['POST','GET'])
def remover_usuario(id_usuario):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    if session['admin'] == True:
        id_usuario = int(id_usuario)
        if id_usuario == int(session['usuario']):
            flash(u'O usuário logado na sessão não pode se remover!', category='warning')
            return(redirect(url_for('listar_usuarios')))
        usuario = Usuario.query.get(id_usuario)
        db.session.delete(usuario)
        db.session.commit()
        flash(u'Usuário removido com sucesso!', category='info')
        return (redirect(url_for('listar_usuarios')))
    flash(u'Apenas administradores podem remover usuários!', category='warning')
    return (redirect(url_for('root')))

@app.route('/usuario/listar/json')
def listar_usuarios_json():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    usuarios = Usuario.query.order_by(Usuario.id).all()
    resultado = json.dumps([ row.asdict() for row in usuarios ])
    return(resultado) 

@app.route('/usuario/<username>')
def buscar_usuario(username):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    lista_usuarios = Usuario.query.filter(func.upper(Usuario.username)==username.upper()).all()
    if len(lista_usuarios) > 0:
        resultado = json.dumps([ row.asdict() for row in lista_usuarios ])
        return resultado
    return json.dumps([ {"id" : 0, "username" : "Not Found"} ])

'''
    Rotas para os Empréstimos
'''

@app.route('/emprestimo', methods=['POST','GET'])
def emprestar_livro():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
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
                                    id_livro=id_livro,
                                    data_emprestimo=datetime.datetime.now())
        livroAlterado = Livro.query.get(id_livro)
        fichaIncremento = Ficha.query.get(id_ficha)
        fichaIncremento.ativo = True
        fichaIncremento.qtdLivros += 1
        livroAlterado.disponivel = False
        db.session.add(novoEmprestimo)
        db.session.commit()
        flash(u'Empréstimo realizado com sucesso!', category='info')
        return(redirect(url_for('root')))
    return(render_template('formEmprestimo.html',
                                csrf_enabled=app.config['WTF_CSRF_ENABLED'],
                                form=form,
                                action=url_for('emprestar_livro')))

@app.route('/emprestimo/listar', methods=['POST','GET'])
def listar_emprestimos():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    form = BuscaForm()
    if form.validate_on_submit():
        emprestimos_teste = Emprestimo.query.order_by(Emprestimo.data_emprestimo.desc()).all()
        emprestimos = list()
        campo_busca = request.form['campo']
        try:
            campo_id = int(campo_busca)
            for emprestimo in emprestimos_teste:
                if campo_id == emprestimo.id:
                    emprestimos.append(emprestimo)
                    continue
                if emprestimo.usuario is not None:
                    if unidecode(campo_busca).upper() == unidecode(emprestimo.usuario.nome).upper():
                        emprestimos.append(emprestimo)
                        continue
                if emprestimo.ficha is not None:
                    if unidecode(campo_busca).upper() == unidecode(emprestimo.ficha.nome).upper():
                        emprestimos.append(emprestimo)
                        continue
                if emprestimo.livro is not None:
                    if unidecode(campo_busca).upper() == unidecode(emprestimo.livro.titulo).upper():
                        emprestimos.append(emprestimo)
        except:
            for emprestimo in emprestimos_teste:
                if emprestimo.usuario is not None:
                    if unidecode(campo_busca).upper() == unidecode(emprestimo.usuario.nome).upper():
                        emprestimos.append(emprestimo)
                        continue
                if emprestimo.ficha is not None:
                    if unidecode(campo_busca).upper() == unidecode(emprestimo.ficha.nome).upper():
                        emprestimos.append(emprestimo)
                        continue
                if emprestimo.livro is not None:
                    if unidecode(campo_busca).upper() == unidecode(emprestimo.livro.titulo).upper():
                        emprestimos.append(emprestimo)
        return(render_template('emprestimos.html', emprestimos=emprestimos, form=form, action=url_for('listar_emprestimos')))
    emprestimos = Emprestimo.query.order_by(Emprestimo.data_emprestimo.desc()).all()
    return(render_template('emprestimos.html', emprestimos=emprestimos, form=form, action=url_for('listar_emprestimos')))

@app.route('/livro/devolver/<id_emprestimo>', methods=['POST','GET'])
def devolver_emprestimo(id_emprestimo):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    id_emprestimo = int(id_emprestimo)
    emprestimo = Emprestimo.query.get(id_emprestimo)
    livro = Livro.query.get(emprestimo.id_livro)
    ficha = Ficha.query.get(emprestimo.id_ficha)
    if emprestimo.data_devolucao is not None:
        flash(u'O livro já foi devolvido!', category='warning')
    else:
        emprestimo.data_devolucao = datetime.datetime.now()
        ficha.qtdLivros -= 1
        ficha.totalLivros += 1
        if ficha.qtdLivros == 0:
            ficha.ativo = False
        livro.disponivel = True
        db.session.commit()
        flash(u'Livro devolvido com sucesso!', category='info')
    return (redirect(url_for('listar_emprestimos')))

@app.route('/emprestimo/remover/<id_emprestimo>', methods=['POST','GET'])
def remover_emprestimo(id_emprestimo):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    id_emprestimo = int(id_emprestimo)
    emprestimo = Emprestimo.query.get(id_emprestimo)
    id_livro = emprestimo.id_livro
    livro = Livro.query.get(id_livro)
    if livro is None or livro.disponivel == True:
        db.session.delete(emprestimo)
        db.session.commit()
        flash(u'Linha de empréstimo removida com sucesso!', category='info')
    else:
        flash(u'O livro precisa ser devolvido antes da remoção do empréstimo!', category='warning')
    return (redirect(url_for('listar_emprestimos')))

@app.route('/emprestimo/listar/json')
def listar_emprestimos_json():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    emprestimos = Emprestimo.query.order_by(Emprestimo.id).all()
    resultado = json.dumps([ row.asdict() for row in emprestimos ])
    return(resultado)

@app.route('/emprestimo/<id_ficha>/<id_livro>')
def buscar_emprestimo(id_ficha, id_livro):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    lista_emprestimos = Emprestimo.query.filter(Emprestimo.id_ficha==id_ficha,
                                                Emprestimo.id_livro==id_livro).all()
    if len(lista_emprestimos) > 0:
        resultado = json.dumps([ row.asdict() for row in lista_emprestimos ])
        return resultado
    return json.dumps([ {"id" : 0, "id_ficha" : 0, "id_livro" : 0} ])

'''
    Rotas para as Fichas
'''

@app.route('/ficha/cadastrar', methods=['POST','GET'])
def cadastrar_ficha():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    form = FichaForm()
    if form.validate_on_submit():
        nome = request.form['nome']
        cpf = request.form['cpf']
        email = request.form['email']
        linha = Ficha.query.filter((Ficha.cpf==cpf) | (Ficha.email==email)).all()
        if len(linha) == 0:
            novaFicha = Ficha(nome=nome,
                                cpf=cpf,
                                email=email,
                                ativo=False,
                                qtdLivros=0, 
                                totalLivros=0)
            
            db.session.add(novaFicha)
            db.session.commit()
            flash(u'Ficha cadastrada com sucesso!', category='info')
            return(redirect(url_for('root')))
        else:
            flash(u'Já existe uma ficha cadastrada com esse E-mail ou CPF', category='warning')
    return (render_template('formCadastroLeitor.html',
                                csrf_enabled=app.config['WTF_CSRF_ENABLED'],
                                form=form,
                                action=url_for('cadastrar_ficha')))

@app.route('/ficha/listar', methods=['POST','GET'])
def listar_fichas():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    form = BuscaForm()
    if form.validate_on_submit():
        fichas_teste = Ficha.query.order_by(Ficha.nome).all()
        fichas = list()
        campo_busca = request.form['campo']
        try:
            campo_id = int(campo_busca)
            for ficha in fichas_teste:
                if campo_id == ficha.id:
                    fichas.append(ficha)
                elif unidecode(campo_busca).upper() == unidecode(ficha.nome).upper():
                    fichas.append(ficha)
                elif unidecode(campo_busca).upper() == unidecode(ficha.cpf).upper():
                    fichas.append(ficha)
        except:
            for ficha in fichas_teste:
                if unidecode(campo_busca).upper() == unidecode(ficha.nome).upper():
                    fichas.append(ficha)
                elif unidecode(campo_busca).upper() == unidecode(ficha.cpf).upper():
                    fichas.append(ficha)
        if len(fichas) == 0:
            flash(u'Nenhum item corresponde ao valor pesquisado!', category='warning')
        return(render_template('fichas.html', fichas=fichas, form=form, action=url_for('listar_fichas')))
    fichas = Ficha.query.order_by(Ficha.nome).all()
    return(render_template('fichas.html', fichas=fichas, form=form, action=url_for('listar_fichas')))

@app.route('/ficha/remover/<id_ficha>', methods=['POST','GET'])
def remover_ficha(id_ficha):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    if session['admin'] == True:
        id_ficha = int(id_ficha)
        ficha = Ficha.query.get(id_ficha)
        if ficha.ativo == False:
            db.session.delete(ficha)
            db.session.commit()
            flash(u'Ficha removida com sucesso!', category='info')
            return (redirect(url_for('listar_fichas')))
        flash(u'O leitor possui livros não devolvidos!', category='warning')
        return (redirect(url_for('listar_fichas')))
    flash(u'Apenas administradores podem remover fichas!', category='warning')
    return (redirect(url_for('root')))

@app.route('/ficha/listar/json')
def listar_fichas_json():
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    fichas = Ficha.query.order_by(Ficha.id).all()
    resultado = json.dumps([ row.asdict() for row in fichas ])
    return(resultado)

@app.route('/ficha/<cpf>')
def buscar_ficha(cpf):
    if session.get('autenticado',False)==False:
        flash(u'Login necessário!', category='warning')
        return(redirect(url_for('login')))
    lista_fichas = Ficha.query.filter(func.upper(Ficha.cpf)==cpf.upper()).all()
    if len(lista_fichas) > 0:
        resultado = json.dumps([ row.asdict() for row in lista_fichas ])
        return resultado
    return json.dumps([ {"id" : 0, "cpf" : "Not Found"} ])

'''
    Rotas para Login/Logout
'''

@app.route('/usuario/login', methods=['POST','GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = request.form['usuario']
        senha = request.form['senha']
        senhahash = hashlib.sha1(senha.encode('utf8')).hexdigest()
        linha = Usuario.query.filter(Usuario.username==usuario,Usuario.senha==senhahash).all()
        if (len(linha) > 0):
            session.clear()
            session['autenticado'] = True
            session['usuario'] = linha[0].id
            session['nome'] = linha[0].nome
            session['admin'] = linha[0].admin
            flash(u'Usuário autenticado com sucesso!', category='info')
            return(redirect(url_for('root')))
        else:
            flash(u'Usuário ou senha não conferem!', category='warning')
            return(redirect(url_for('login')))
    return (render_template('formLogin.html', 
                            csrf_enabled=app.config['WTF_CSRF_ENABLED'], 
                            form=form, 
                            action=url_for('login')))

@app.route('/usuario/logout')
def logout():
    session.clear()
    flash(u'Sessão encerrada com sucesso!', category='info')
    return(redirect(url_for('root')))

if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=80, url_prefix='/app')
