from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pymysql as mysql
import requests
from bs4 import BeautifulSoup
import time
import re

app = Flask(__name__)
app.secret_key = "troque-esta-chave-para-uma-segura"

# Uploads
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}


# -------------------------
# CONFIGURAÇÕES
# -------------------------

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "142536",
    "database": "mandato",
    "charset": "utf8mb4",
    "use_unicode": True
}

FONTES = [
    {
        "url": "https://g1.globo.com/politica/",
        "nome": "G1",
        "tema": "Política"
    },
    {
        "url": "https://www.uol.com.br/politica/",
        "nome": "UOL",
        "tema": "Política"
    },
    {
        "url": "https://www1.folha.uol.com.br/poder/",
        "nome": "Folha",
        "tema": "Política"
    },
    {
        "url": "https://www.poder360.com.br/",
        "nome": "Poder360",
        "tema": "Política"
    },
    {
        "url": "https://www.metropoles.com/politica/",
        "nome": "Metrópoles",
        "tema": "Política"
    }
]

# Create a shared requests session with safer default headers
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
})

RELEVANT_KEYWORDS = [
    "eleição", "eleições", "eleitoral", "candidato", "candidatura", "voto", "urna", "campanha",
    "lei", "legislação", "pl", "pec", "projeto de lei", "senado", "câmara", "parlamento", "governo",
    "ministro", "ministra", "parlamentar", "deputado", "senador", "vereador", "bancada", "política",
    "políticas públicas", "saúde", "educação", "infraestrutura", "saneamento", "assistência", "orçamento",
    "direito", "supremo", "stf", "cpi", "congresso", "trâmite", "legislativo", "judiciário", "eleitor"
]

UNWANTED_LINK_SEGMENTS = [
    "/sobre", "/projeto", "/equipe", "/contato", "/marketing", "/politica-de-privacidade",
    "/termos", "/cookies", "/metodologia", "/carreira", "/servicos", "/guia", "/newsletter",
    "/agenda", "/evento", "/eventos", "/colunistas", "/coluna", "/podcast", "/podcasts",
    "/para-voce", "/publicidade", "/assinatura", "/maps", "/anuncie", "/parcerias"
]

UNWANTED_TITLE_PATTERNS = [
    "o projeto consiste", "ecossistema digital", "desenvolvimento de", "metodologia ágil",
    "controle do código-fonte", "github", "cronograma", "sprints", "gestão de tarefas",
    "ferramenta de apoio", "plataforma integrada", "notificações configuradas",
    "aplicação mobile", "aplicação web", "dashboard analítico", "gestão do projeto",
    "fase de planejamento", "implantação em ambiente", "repositório no github"
]


def eh_titulo_relevante(manchete):
    texto = manchete.lower()
    if any(padrao in texto for padrao in UNWANTED_TITLE_PATTERNS):
        return False
    return any(termo in texto for termo in RELEVANT_KEYWORDS)


def eh_link_relevante(link):
    lower_link = link.lower()
    if any(seg in lower_link for seg in UNWANTED_LINK_SEGMENTS):
        return False
    return True

# -------------------------
# CLASSIFICAÇÃO DE TEMA
# -------------------------

def classificar_tema(manchete, fonte_tema):
    texto = manchete.lower()
    eleicoes = ["eleição", "eleições", "candidato", "candidatura", "voto", "urna", "campanha", "colégio eleitoral"]
    legislacao = ["lei", "legislação", "pl", "pec", "projeto de lei", "câmara", "senado", "parlamento", "comissão"]
    politicas_publicas = ["política pública", "políticas públicas", "ministro", "governo", "programa", "saúde", "educação", "infraestrutura", "saneamento", "assistência"]
    parlamentares = ["parlamentar", "deputado", "senador", "vereador", "líder", "bancada", "frente parlamentar", "deputados", "senadores"]

    if any(p in texto for p in eleicoes):
        return "Eleições"
    if any(p in texto for p in legislacao):
        return "Legislação"
    if any(p in texto for p in politicas_publicas):
        return "Políticas Públicas"
    if any(p in texto for p in parlamentares):
        return "Parlamentares"

    return fonte_tema or "Política"


# -------------------------
# BANCO DE DADOS
# -------------------------

def conectar_banco():
    try:
        return mysql.connect(**DB_CONFIG)
    except mysql.Error as erro:
        print(f"Erro ao conectar no banco: {erro}")
        return None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()
        foto = request.files.get('foto')

        filename = None
        if foto and foto.filename and allowed_file(foto.filename):
            filename = secure_filename(foto.filename)
            # prefixa com timestamp para reduzir colisões
            filename = f"{int(time.time())}_{filename}"
            destino = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            foto.save(destino)

        banco = conectar_banco()
        if banco is None:
            flash('Erro ao conectar ao banco. Tente novamente mais tarde.')
            return redirect(url_for('register'))

        cursor = banco.cursor()
        try:
            # procura por email se fornecido
            user_id = None
            if email:
                cursor.execute("SELECT id_usuario FROM tb_usuario WHERE email = %s", (email,))
                row = cursor.fetchone()
                if row:
                    user_id = row[0]

            if user_id:
                # atualiza
                updates = []
                params = []
                if nome:
                    updates.append('nome = %s')
                    params.append(nome)
                if senha:
                    updates.append('senha = %s')
                    params.append(generate_password_hash(senha))
                if filename:
                    updates.append('profile_image = %s')
                    params.append(filename)
                if updates:
                    params.append(user_id)
                    sql = f"UPDATE tb_usuario SET {', '.join(updates)} WHERE id_usuario = %s"
                    cursor.execute(sql, tuple(params))
            else:
                # insere novo usuário (email pode ficar vazio)
                hashed = generate_password_hash(senha) if senha else None
                cursor.execute(
                    "INSERT INTO tb_usuario (email, nome, senha, profile_image) VALUES (%s, %s, %s, %s)",
                    (email or None, nome or None, hashed, filename or None)
                )
                user_id = cursor.lastrowid

            banco.commit()

            # salva no session para exibir no navbar
            session['user_id'] = user_id
            session['user_name'] = nome or 'Usuário'
            if filename:
                session['profile_image'] = filename

            flash('Cadastro salvo. Perfil atualizado.')
            return redirect(url_for('index'))

        except mysql.Error as e:
            print(f"Erro ao salvar usuário: {e}")
            flash('Erro ao salvar usuário no banco.')
            return redirect(url_for('register'))
        finally:
            cursor.close()
            banco.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()

        if not email or not senha:
            flash('Preencha email e senha.')
            return redirect(url_for('login'))

        banco = conectar_banco()
        if banco is None:
            flash('Erro de conexão ao banco.')
            return redirect(url_for('login'))

        cursor = banco.cursor()
        try:
            cursor.execute('SELECT id_usuario, nome, senha, profile_image FROM tb_usuario WHERE email = %s', (email,))
            row = cursor.fetchone()
            if not row:
                flash('Usuário não encontrado.')
                return redirect(url_for('login'))

            user_id, nome, hashed, profile_image = row

            if not hashed or not check_password_hash(hashed, senha):
                flash('Credenciais inválidas.')
                return redirect(url_for('login'))

            # sucesso
            session['user_id'] = user_id
            session['user_name'] = nome or 'Usuário'
            if profile_image:
                session['profile_image'] = profile_image

            flash('Login efetuado.')
            return redirect(url_for('index'))

        except mysql.Error as e:
            print(f"Erro no login: {e}")
            flash('Erro no sistema. Tente novamente.')
            return redirect(url_for('login'))
        finally:
            cursor.close()
            banco.close()

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('profile_image', None)
    flash('Você saiu da sessão.')
    return redirect(url_for('index'))


def setup_banco():
    """Cria a tabela se não existir e garante índice único no link."""
    banco = conectar_banco()
    if banco is None:
        print("ERRO: Não foi possível conectar ao banco. Verifique se o MySQL está rodando.")
        return False

    cursor = banco.cursor()

    try:
        # Cria tabela se não existir (sem UNIQUE aqui para não conflitar com tabelas existentes)
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS noticias (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                tema       VARCHAR(100),
                manchete   VARCHAR(500),
                link       VARCHAR(500),
                fonte      VARCHAR(50),
                image      VARCHAR(500),
                data       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Cria tabela de usuários (se não existir) e garante coluna profile_image
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_usuario (
                id_usuario INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255),
                nome VARCHAR(255),
                senha VARCHAR(255),
                profile_image VARCHAR(255)
            ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Garante que a coluna link é VARCHAR (não TEXT)
        cursor.execute("""
            ALTER TABLE noticias MODIFY COLUMN link VARCHAR(500)
        """)

        # Garante que a coluna image existe
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE table_schema = DATABASE()
              AND table_name = 'noticias'
              AND column_name = 'image'
        """)
        existe_img = cursor.fetchone()[0]
        if not existe_img:
            try:
                cursor.execute("ALTER TABLE noticias ADD COLUMN image VARCHAR(500)")
                print("Coluna 'image' adicionada em noticias.")
            except mysql.Error as e:
                print(f"Erro ao adicionar coluna image: {e}")

        # Remove coluna 'sentimento' caso exista (migração após remoção da feature)
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE table_schema = DATABASE()
              AND table_name = 'noticias'
              AND column_name = 'sentimento'
        """)
        existe_col = cursor.fetchone()[0]
        if existe_col:
            try:
                cursor.execute("ALTER TABLE noticias DROP COLUMN sentimento")
                print("Coluna 'sentimento' removida (migração).")
            except mysql.Error as e:
                print(f"Erro ao remover coluna 'sentimento': {e}")

        # Adiciona índice único se ainda não existe
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = 'noticias'
              AND index_name = 'idx_link'
        """)
        existe = cursor.fetchone()[0]
        if not existe:
            cursor.execute("ALTER TABLE noticias ADD UNIQUE INDEX idx_link (link)")

        banco.commit()
        print("Banco de dados configurado com sucesso.")
        return True

    except mysql.Error as e:
        print(f"ERRO no setup do banco: {e}")
        return False

    finally:
        cursor.close()
        banco.close()


# -------------------------
# SCRAPING
# -------------------------

def coletar_noticias():
    banco = conectar_banco()
    if banco is None:
        return 0

    cursor = banco.cursor()
    total_novas = 0

    for fonte in FONTES:
        try:
            # use shared session (better connection reuse) and include a Referer
            url = fonte.get("url")
            print(f"[scrape] Acessando {url}")
            headers = {"Referer": url}
            resposta = SESSION.get(url, headers=headers, timeout=12, allow_redirects=True)
            print(f"[scrape] {url} -> {resposta.status_code}")

            # If access denied, try one quick retry with an alternate UA and Referer
            if resposta.status_code == 403:
                print(f"[scrape] 403 recebido em {url}, tentando UA alternativo")
                alt_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
                    "Referer": "https://www.google.com/",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "pt-BR,pt;q=0.9",
                }
                resposta = SESSION.get(url, headers=alt_headers, timeout=12, allow_redirects=True)
                print(f"[scrape] retry -> {resposta.status_code}")

            # If resource missing (404) try requesting the site root (to avoid stale category paths)
            if resposta.status_code == 404:
                print(f"[scrape] 404 em {url}, tentando raiz do site")
                m = re.match(r"(https?://[^/]+)", url)
                if m:
                    root = m.group(1)
                    resposta = SESSION.get(root, headers={"Referer": root}, timeout=12)
                    print(f"[scrape] {root} -> {resposta.status_code}")

            resposta.raise_for_status()

            soup = BeautifulSoup(resposta.text, "html.parser")

            # Pega apenas links que parecem ser manchetes reais
            links_encontrados = soup.find_all("a", href=True)

            for tag in links_encontrados:
                manchete = tag.get_text(strip=True)
                link = tag.get("href", "")

                # Filtros de qualidade
                if len(manchete) < 40:
                    continue
                if not link.startswith("http"):
                    continue
                if any(p in link for p in ["/autor/", "/tag/", "/videos/", "#"]):
                    continue
                if not eh_link_relevante(link):
                    continue
                if not eh_titulo_relevante(manchete):
                    continue

                tema_noticia = classificar_tema(manchete, fonte["tema"])

                # Tenta extrair imagem OG da página da notícia (silenciosamente)
                image_url = None
                try:
                    art_resp = SESSION.get(link, headers={"Referer": url}, timeout=8)
                    if art_resp.status_code == 200:
                        art_soup = BeautifulSoup(art_resp.text, "html.parser")
                        meta = art_soup.find('meta', property='og:image') or art_soup.find('meta', attrs={'name': 'twitter:image'})
                        if meta and meta.get('content'):
                            image_url = meta.get('content')
                except Exception:
                    image_url = None

                sql = """
                    INSERT IGNORE INTO noticias
                    (tema, manchete, link, fonte, image)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    tema_noticia,
                    manchete[:480],
                    link[:980],
                    fonte["nome"],
                    image_url[:480] if image_url else None
                ))

                if cursor.rowcount > 0:
                    total_novas += 1

        except requests.RequestException as e:
            print(f"Erro ao acessar {fonte['url']}: {e}")
        except Exception as e:
            print(f"Erro inesperado em {fonte['nome']}: {e}")

    banco.commit()
    cursor.close()
    banco.close()

    return total_novas


# -------------------------
# ROTA PRINCIPAL
# -------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    mensagem = None

    if request.method == "POST":
        novas = coletar_noticias()
        mensagem = f"{novas} nova(s) notícia(s) coletada(s)."

    banco = conectar_banco()
    if banco is None:
        return "Erro de conexão com o banco de dados.", 500

    cursor = banco.cursor(mysql.cursors.DictCursor)

    try:
        # Busca com filtro opcional por fonte/tema/palavra-chave/data
        filtro_fonte = request.args.get("fonte", "")
        filtro_tema = request.args.get("tema", "")
        pesquisa = request.args.get("q", "").strip()
        data_inicio = request.args.get("data_inicio", "")
        data_fim = request.args.get("data_fim", "")

        query = "SELECT * FROM noticias WHERE 1=1"
        params = []

        if filtro_fonte:
            query += " AND fonte = %s"
            params.append(filtro_fonte)

        if filtro_tema:
            query += " AND tema = %s"
            params.append(filtro_tema)

        if pesquisa:
            query += " AND (manchete LIKE %s OR link LIKE %s)"
            params.append(f"%{pesquisa}%")
            params.append(f"%{pesquisa}%")

        if data_inicio:
            query += " AND DATE(data) >= %s"
            params.append(data_inicio)

        if data_fim:
            query += " AND DATE(data) <= %s"
            params.append(data_fim)

        query += " ORDER BY data DESC LIMIT 100"

        cursor.execute(query, params)
        noticias = cursor.fetchall()

        cursor.execute("""
            SELECT fonte, COUNT(*) as total
            FROM noticias
            GROUP BY fonte
        """)
        dados_fonte = cursor.fetchall()

        cursor.execute("""
            SELECT tema, COUNT(*) as total
            FROM noticias
            GROUP BY tema
        """)
        dados_tema = cursor.fetchall()

        cursor.execute("""
            SELECT DATE(data) AS dia, COUNT(*) AS total
            FROM noticias
            WHERE data >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
            GROUP BY DATE(data)
            ORDER BY dia
        """)
        dados_timeline = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) as total FROM noticias")
        total_row = cursor.fetchone()
        total_noticias = total_row["total"] if total_row else 0

    except mysql.Error as e:
        print(f"Erro na consulta: {e}")
        noticias, dados_fonte, dados_tema, dados_timeline = [], [], [], []
        total_noticias = 0

    finally:
        cursor.close()
        banco.close()

    # Monta dicts para os gráficos
    fontes_grafico = {d["fonte"]: d["total"] for d in dados_fonte}
    temas_grafico = {d["tema"]: d["total"] for d in dados_tema}
    temas_disponiveis = [d["tema"] for d in dados_tema]
    fontes_disponiveis = [d["fonte"] for d in dados_fonte]
    timeline_labels = [d["dia"].strftime("%d/%m") for d in dados_timeline]
    timeline_values = [d["total"] for d in dados_timeline]

    return render_template(
        "index.html",
        noticias=noticias,
        fontes_grafico=fontes_grafico,
        temas_grafico=temas_grafico,
        temas_disponiveis=temas_disponiveis,
        fontes_disponiveis=fontes_disponiveis,
        timeline_labels=timeline_labels,
        timeline_values=timeline_values,
        total_noticias=total_noticias,
        mensagem=mensagem,
        filtro_fonte=filtro_fonte,
        filtro_tema=filtro_tema,
        pesquisa=pesquisa,
        data_inicio=data_inicio,
        data_fim=data_fim
    )


# -------------------------

if __name__ == "__main__":
    print("Iniciando Observatorio de Noticias...")
    ok = setup_banco()
    if not ok:
        print("Aviso: problema no banco, mas tentando iniciar o servidor mesmo assim.")
    print("Acesse: http://localhost:5000")
    app.run(debug=True, use_reloader=False)