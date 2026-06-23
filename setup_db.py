import mysql.connector
from mysql.connector import errorcode

def criar_banco_e_tabelas():
    try:
        # Conectar sem especificar database
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="142536"
        )
        cursor = conn.cursor()

        # Criar banco de dados
        cursor.execute("CREATE DATABASE IF NOT EXISTS mop_mvp")
        cursor.execute("USE mop_mvp")

        # Criar tabelas
        tabelas = {}

        tabelas['tb_usuario'] = """
            CREATE TABLE IF NOT EXISTS tb_usuario (
                id_usuario INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                nome VARCHAR(255) NOT NULL,
                senha VARCHAR(255) NOT NULL
            )
        """

        tabelas['tb_entidade_monitoradas'] = """
            CREATE TABLE IF NOT EXISTS tb_entidade_monitoradas (
                id_entidadesMonitoradas INT AUTO_INCREMENT PRIMARY KEY,
                tb_usuario_id_usuario INT NOT NULL,
                nome VARCHAR(255) NOT NULL,
                categoria VARCHAR(100),
                palavras_chave TEXT,
                FOREIGN KEY (tb_usuario_id_usuario) REFERENCES tb_usuario(id_usuario)
            )
        """

        tabelas['alertas_notificacoes'] = """
            CREATE TABLE IF NOT EXISTS alertas_notificacoes (
                id_alertas INT AUTO_INCREMENT PRIMARY KEY,
                tipo_alerta VARCHAR(100),
                mensagem_alerta TEXT
            )
        """

        tabelas['tb_mencoes_coletadas'] = """
            CREATE TABLE IF NOT EXISTS tb_mencoes_coletadas (
                id_mencoesColetadas INT AUTO_INCREMENT PRIMARY KEY,
                tb_entidade_monitoradas_id_entidadesMonitoradas INT NOT NULL,
                alertas_notificacoes_id_alertas INT NOT NULL,
                fonte VARCHAR(255),
                data_coletada DATE,
                texto TEXT NOT NULL,
                link VARCHAR(500),
                FOREIGN KEY (tb_entidade_monitoradas_id_entidadesMonitoradas)
                    REFERENCES tb_entidade_monitoradas(id_entidadesMonitoradas),
                FOREIGN KEY (alertas_notificacoes_id_alertas)
                    REFERENCES alertas_notificacoes(id_alertas)
            )
        """

        # Executar criação das tabelas
        for nome_tabela, sql in tabelas.items():
            try:
                print(f"Criando tabela {nome_tabela}...")
                cursor.execute(sql)
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    print(f"Tabela {nome_tabela} já existe.")
                else:
                    print(f"Erro ao criar tabela {nome_tabela}: {err}")

        # Inserir dados padrão se não existirem
        cursor.execute("SELECT COUNT(*) FROM tb_usuario")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO tb_usuario (email, nome, senha)
                VALUES ('teste@email.com', 'Usuário Padrão', '123')
            """)
            print("Usuário padrão criado.")

        cursor.execute("SELECT COUNT(*) FROM alertas_notificacoes")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO alertas_notificacoes (tipo_alerta, mensagem_alerta)
                VALUES ('raspagem', 'Alerta padrão para raspagem de notícias')
            """)
            print("Alerta padrão criado.")

        cursor.execute("SELECT COUNT(*) FROM tb_entidade_monitoradas")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO tb_entidade_monitoradas (tb_usuario_id_usuario, nome, categoria, palavras_chave)
                VALUES (1, 'Entidade Padrão', 'geral', 'raspagem')
            """)
            print("Entidade padrão criada.")

        conn.commit()
        print("Banco de dados e tabelas criados com sucesso!")

    except mysql.connector.Error as err:
        print(f"Erro no MySQL: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    criar_banco_e_tabelas()
