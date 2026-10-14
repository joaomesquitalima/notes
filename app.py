import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = '1982'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notas.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Máximo de 16MB por imagem

db = SQLAlchemy(app)

# --- MODELOS DE BANCO DE DADOS ---
class Nota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    tag = db.Column(db.String(100), nullable=False) # Ex: "Hardware", "Sistemas", "Procedimentos"
    blocos = db.relationship('Bloco', backref='nota', lazy=True, cascade="all, delete-orphan")

class Bloco(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nota_id = db.Column(db.Integer, db.ForeignKey('nota.id'), nullable=False)
    titulo_bloco = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    imagem = db.Column(db.String(200), nullable=True) # Caminho da imagem

# --- ROTAS ---
@app.route('/')
def index():
    busca = request.args.get('q', '')
    if busca:
        notas = Nota.query.filter(Nota.titulo.contains(busca) | Nota.tag.contains(busca)).all()
    else:
        notas = Nota.query.order_by(Nota.id.desc()).all()
    return render_template('index.html', notas=notas, busca=busca)

@app.route('/nota/<int:id>')
def ver_nota(id):
    nota = Nota.query.get_or_404(id)
    return render_template('note.html', nota=nota)

@app.route('/criar', methods=['GET', 'POST'])
def criar_nota():
    if request.method == 'POST':
        titulo = request.form['titulo']
        tag = request.form['tag'].strip().title()
        
        nova_nota = Nota(titulo=titulo, tag=tag)
        db.session.add(nova_nota)
        db.session.commit()
        
        titulos_bloco = request.form.getlist('titulo_bloco[]')
        conteudos_bloco = request.form.getlist('conteudo[]')
        
        for i in range(len(titulos_bloco)):
            conteudo_seguro = conteudos_bloco[i] if i < len(conteudos_bloco) else ""
            novo_bloco = Bloco(
                nota_id=nova_nota.id,
                titulo_bloco=titulos_bloco[i],
                conteudo=conteudo_seguro,
                imagem=None # Removemos o upload antigo!
            )
            db.session.add(novo_bloco)
            
        db.session.commit()
        return redirect(url_for('index'))
        
    return render_template('form.html', acao="Criar")

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_nota(id):
    nota = Nota.query.get_or_404(id)
    
    if request.method == 'POST':
        nota.titulo = request.form['titulo']
        nota.tag = request.form['tag'].strip().title()
        
        titulos_bloco = request.form.getlist('titulo_bloco[]')
        conteudos_bloco = request.form.getlist('conteudo[]')
        imagens_atuais = request.form.getlist('imagem_atual[]')
        
        for bloco in nota.blocos:
            db.session.delete(bloco)
        db.session.commit()
        
        for i in range(len(titulos_bloco)):
            # Se a imagem for apagada pelo utilizador, ela vem vazia e guarda como None
            nome_imagem = imagens_atuais[i] if i < len(imagens_atuais) and imagens_atuais[i] != '' else None
            conteudo_seguro = conteudos_bloco[i] if i < len(conteudos_bloco) else ""
                
            novo_bloco = Bloco(
                nota_id=nota.id,
                titulo_bloco=titulos_bloco[i],
                conteudo=conteudo_seguro,
                imagem=nome_imagem
            )
            db.session.add(novo_bloco)
            
        db.session.commit()
        return redirect(url_for('ver_nota', id=nota.id))
        
    return render_template('editar.html', nota=nota)

@app.route('/deletar/<int:id>')
def deletar_nota(id):
    nota = Nota.query.get_or_404(id)
    db.session.delete(nota)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/temas')
def temas():
    busca = request.args.get('q', '')
    # Busca todas as tags únicas
    tags_query = db.session.query(Nota.tag).distinct()
    if busca:
        tags_query = tags_query.filter(Nota.tag.contains(busca))
    
    tags = [t[0] for t in tags_query.all()]
    
    notas_por_tag = {}
    for tag in tags:
        notas_por_tag[tag] = Nota.query.filter_by(tag=tag).all()
        
    return render_template('temas.html', notas_por_tag=notas_por_tag, busca=busca)

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Cria o banco SQLite automaticamente na primeira vez
    app.run(debug=True)