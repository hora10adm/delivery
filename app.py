from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
import sqlite3
import hashlib
import os
import requests

app = Flask(__name__)
CORS(app)

# Configuração do banco de dados
DATABASE = 'entregas.db'

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS entregas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_pedido TEXT UNIQUE NOT NULL,
                aplicativo_delivery TEXT NOT NULL,
                quantidade_pedidos TEXT,
                tipo_entrega TEXT,
                valor_turbo REAL,
                motoboy_nome TEXT,
                bairro TEXT,
                status TEXT DEFAULT 'pendente',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_inicio TIMESTAMP,
                data_finalizacao TIMESTAMP,
                data_cancelamento TIMESTAMP,
                motivo_cancelamento TEXT,
                pedido_pago INTEGER DEFAULT 0,
                latitude REAL,
                longitude REAL,
                endereco_entrega TEXT
            )
        ''')
        
        # MIGRAÇÃO AUTOMÁTICA: Adicionar colunas se não existirem
        try:
            cursor = db.execute("PRAGMA table_info(entregas)")
            colunas_existentes = [row[1] for row in cursor.fetchall()]
            
            novas_colunas = [
                ('quantidade_pedidos', 'TEXT'),
                ('tipo_entrega', 'TEXT'),
                ('valor_turbo', 'REAL'),
                ('data_cancelamento', 'TIMESTAMP'),
                ('motivo_cancelamento', 'TEXT'),
                ('pedido_pago', 'INTEGER DEFAULT 0')
            ]
            
            for nome_coluna, tipo_coluna in novas_colunas:
                if nome_coluna not in colunas_existentes:
                    try:
                        db.execute(f"ALTER TABLE entregas ADD COLUMN {nome_coluna} {tipo_coluna}")
                        print(f"✅ Migração: Coluna '{nome_coluna}' adicionada")
                    except Exception as e:
                        print(f"⚠️ Aviso: '{nome_coluna}': {e}")
        except Exception as e:
            print(f"⚠️ Migração automática: {e}")
        
        db.execute('''
            CREATE TABLE IF NOT EXISTS motoboys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                telefone TEXT,
                ativo INTEGER DEFAULT 1
            )
        ''')
        
        # Criar motoboy de teste se não existir
        motoboy_exists = db.execute('SELECT * FROM motoboys WHERE username = ?', ('motoboy1',)).fetchone()
        if not motoboy_exists:
            senha_hash = hashlib.sha256('123456'.encode()).hexdigest()
            db.execute('INSERT INTO motoboys (nome, username, password) VALUES (?, ?, ?)', 
                      ('João Silva', 'motoboy1', senha_hash))
        
        db.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                nome TEXT NOT NULL,
                tipo TEXT DEFAULT 'admin'
            )
        ''')
        
        # Criar usuário admin padrão se não existir
        admin_exists = db.execute('SELECT * FROM usuarios WHERE username = ?', ('admin',)).fetchone()
        if not admin_exists:
    
            senha_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            db.execute('INSERT INTO usuarios (username, password, nome) VALUES (?, ?, ?)', 
                      ('admin', senha_hash, 'Administrador'))
        
        db.commit()

# Flag para controlar migração única
_migration_done = False

@app.before_request
def run_migration_once():
    global _migration_done
    if not _migration_done:
        try:
            db = get_db()
            cursor = db.execute("PRAGMA table_info(entregas)")
            colunas_existentes = [row[1] for row in cursor.fetchall()]
            
            novas_colunas = [
                ('quantidade_pedidos', 'TEXT'),
                ('tipo_entrega', 'TEXT'),
                ('valor_turbo', 'REAL'),
                ('data_cancelamento', 'TIMESTAMP'),
                ('motivo_cancelamento', 'TEXT'),
                ('pedido_pago', 'INTEGER DEFAULT 0')
            ]
            
            migrou = False
            for nome_coluna, tipo_coluna in novas_colunas:
                if nome_coluna not in colunas_existentes:
                    try:
                        db.execute(f"ALTER TABLE entregas ADD COLUMN {nome_coluna} {tipo_coluna}")
                        print(f"✅ AUTO-MIGRAÇÃO: '{nome_coluna}' adicionada")
                        migrou = True
                    except:
                        pass
            
            if migrou:
                db.commit()
                print("🎉 Migração automática concluída!")
            
            _migration_done = True
        except Exception as e:
            print(f"⚠️ Erro na auto-migração: {e}")
            _migration_done = True

# Rotas para o Painel Admin
@app.route('/')
def admin_panel():
    return render_template('admin.html')

# Rota para o Motoboy
@app.route('/motoboy/login')
def motoboy_login():
    return render_template('motoboy_login.html')

@app.route('/motoboy')
def motoboy_page():
    return render_template('motoboy.html')

# API - Criar nova entrega
@app.route('/api/entregas', methods=['POST'])
def criar_entrega():
    try:
        data = request.json
        db = get_db()
        
        # INSERT básico apenas com campos obrigatórios
        cursor = db.execute('''
            INSERT INTO entregas (codigo_pedido, aplicativo_delivery)
            VALUES (?, ?)
        ''', (data['codigo_pedido'], data['aplicativo_delivery']))
        
        entrega_id = cursor.lastrowid
        
        # UPDATE com campos opcionais se existirem
        updates = []
        params = []
        
        if 'quantidade_pedidos' in data and data.get('quantidade_pedidos'):
            updates.append('quantidade_pedidos = ?')
            params.append(data['quantidade_pedidos'])
        
        if 'tipo_entrega' in data and data.get('tipo_entrega'):
            updates.append('tipo_entrega = ?')
            params.append(data['tipo_entrega'])
        
        if 'valor_turbo' in data and data.get('valor_turbo'):
            updates.append('valor_turbo = ?')
            params.append(float(data['valor_turbo']))
        
        # Executar UPDATE se houver campos opcionais
        if updates:
            params.append(entrega_id)
            sql = f"UPDATE entregas SET {', '.join(updates)} WHERE id = ?"
            db.execute(sql, params)
        
        db.commit()
        
        # Gerar QR code
        import qrcode
        import io
        import base64
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(data['codigo_pedido'])
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'id': entrega_id,
            'codigo_pedido': data['codigo_pedido'],
            'qrcode': img_str,
            'message': 'Entrega criada com sucesso'
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Código de pedido já existe'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API - Listar todas as entregas
@app.route('/api/entregas', methods=['GET'])
def listar_entregas():
    db = get_db()
    status = request.args.get('status', None)
    
    if status:
        entregas = db.execute('SELECT * FROM entregas WHERE status = ? ORDER BY data_criacao DESC', (status,)).fetchall()
    else:
        entregas = db.execute('SELECT * FROM entregas ORDER BY data_criacao DESC').fetchall()
    
    return jsonify([dict(entrega) for entrega in entregas])

# API - Buscar entrega por código (para QR Code)
@app.route('/api/entregas/<codigo_pedido>', methods=['GET'])
def buscar_entrega(codigo_pedido):
    db = get_db()
    entrega = db.execute('SELECT * FROM entregas WHERE codigo_pedido = ?', (codigo_pedido,)).fetchone()
    
    if entrega:
        return jsonify(dict(entrega))
    else:
        return jsonify({'success': False, 'message': 'Entrega não encontrada'}), 404

# API - Atribuir motoboy e iniciar entrega
@app.route('/api/entregas/<codigo_pedido>/iniciar', methods=['PUT'])
def iniciar_entrega(codigo_pedido):
    try:
        data = request.json
        db = get_db()
        
        db.execute('''
            UPDATE entregas 
            SET motoboy_nome = ?, status = 'em_rota', data_inicio = ?
            WHERE codigo_pedido = ?
        ''', (data['motoboy_nome'], datetime.now(), codigo_pedido))
        
        db.commit()
        
        return jsonify({'success': True, 'message': 'Entrega iniciada'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API - Finalizar entrega (com localização)
@app.route('/api/entregas/<codigo_pedido>/finalizar', methods=['PUT'])
def finalizar_entrega(codigo_pedido):
    try:
        data = request.json
        db = get_db()
        
        # Buscar endereço aproximado usando Nominatim (OpenStreetMap)
        endereco = f"Lat: {data['latitude']}, Long: {data['longitude']}"
        bairro = ""
        try:
            import requests
            response = requests.get(
                f"https://nominatim.openstreetmap.org/reverse",
                params={
                    'lat': data['latitude'],
                    'lon': data['longitude'],
                    'format': 'json',
                    'zoom': 18  # Mais detalhado para pegar bairro
                },
                headers={'User-Agent': 'SistemaEntregas/1.0'}
            )
            if response.status_code == 200:
                result = response.json()
                if 'display_name' in result:
                    endereco = result['display_name']
                
                # Tentar extrair o bairro (ordem de prioridade)
                address = result.get('address', {})
                
                # Lista de campos que representam bairro (do mais específico ao menos)
                campos_bairro = [
                    'suburb',           # Bairro/Subúrbio
                    'neighbourhood',    # Vizinhança
                    'quarter',          # Quarteirão
                    'city_district',    # Distrito da cidade
                    'district',         # Distrito
                    'borough',          # Bairro (termo inglês)
                    'allotments'        # Loteamento
                ]
                
                # Pegar o primeiro campo que existir e NÃO seja uma cidade
                cidade = address.get('city') or address.get('town') or address.get('village') or ''
                
                for campo in campos_bairro:
                    if campo in address and address[campo]:
                        possivel_bairro = address[campo].strip()
                        # Verificar se não é o nome da cidade
                        if possivel_bairro and possivel_bairro != cidade:
                            bairro = possivel_bairro
                            break
                
                # Se ainda não achou, tenta municipality ou hamlet (mas só se for diferente da cidade)
                if not bairro:
                    if 'municipality' in address and address['municipality'] != cidade:
                        bairro = address['municipality']
                    elif 'hamlet' in address and address['hamlet'] != cidade:
                        bairro = address['hamlet']
                
        except:
            pass  # Se falhar, usa apenas lat/long
        
        db.execute('''
            UPDATE entregas 
            SET status = 'finalizada',
                data_finalizacao = ?,
                latitude = ?,
                longitude = ?,
                endereco_entrega = ?,
                bairro = ?
            WHERE codigo_pedido = ?
        ''', (datetime.now(), data['latitude'], data['longitude'], endereco, bairro, codigo_pedido))
        
        db.commit()
        
        return jsonify({'success': True, 'message': 'Entrega finalizada com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API - Gerar QR code para um pedido
@app.route('/api/entregas/<codigo_pedido>/qrcode', methods=['GET'])
def gerar_qrcode_pedido(codigo_pedido):
    try:
        import qrcode
        import io
        import base64
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(codigo_pedido)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'qrcode': img_str,
            'codigo_pedido': codigo_pedido
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API - Estatísticas do dashboard
@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    db = get_db()
    
    stats = {
        'total': db.execute('SELECT COUNT(*) as count FROM entregas').fetchone()['count'],
        'pendentes': db.execute('SELECT COUNT(*) as count FROM entregas WHERE status = "pendente"').fetchone()['count'],
        'em_rota': db.execute('SELECT COUNT(*) as count FROM entregas WHERE status = "em_rota"').fetchone()['count'],
        'finalizadas': db.execute('SELECT COUNT(*) as count FROM entregas WHERE status = "finalizada"').fetchone()['count']
    }
    
    return jsonify(stats)

# Rotas Admin
@app.route('/admin/login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/motoboys')
def admin_motoboys():
    return render_template('admin_motoboys.html')

# API - Login
@app.route('/api/admin/login', methods=['POST'])
def api_login():
    try:
        data = request.json
        db = get_db()
        

        senha_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        usuario = db.execute(
            'SELECT * FROM usuarios WHERE username = ? AND password = ?',
            (data['username'], senha_hash)
        ).fetchone()
        
        if usuario:
            return jsonify({'success': True, 'nome': usuario['nome']})
        else:
            return jsonify({'success': False, 'message': 'Usuário ou senha inválidos'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API - Login Motoboy
@app.route('/api/motoboy/login', methods=['POST'])
def api_motoboy_login():
    try:
        data = request.json
        db = get_db()
        

        senha_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        motoboy = db.execute(
            'SELECT * FROM motoboys WHERE username = ? AND password = ? AND ativo = 1',
            (data['username'], senha_hash)
        ).fetchone()
        
        if motoboy:
            return jsonify({
                'success': True, 
                'nome': motoboy['nome'],
                'id': motoboy['id']
            })
        else:
            return jsonify({'success': False, 'message': 'Usuário ou senha inválidos'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API - Entregas do motoboy (em andamento)
@app.route('/api/motoboy/entregas/<motoboy_nome>', methods=['GET'])
def entregas_motoboy(motoboy_nome):
    try:
        db = get_db()
        entregas = db.execute(
            'SELECT * FROM entregas WHERE motoboy_nome = ? AND status = "em_rota" ORDER BY data_inicio DESC',
            (motoboy_nome,)
        ).fetchall()
        return jsonify([dict(e) for e in entregas])
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API - Estatísticas por entregador
@app.route('/api/admin/stats/entregadores', methods=['GET'])
def stats_entregadores():
    db = get_db()
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    query = '''
        SELECT 
            motoboy_nome,
            COUNT(*) as total_entregas,
            AVG(CAST((julianday(data_finalizacao) - julianday(data_inicio)) * 24 * 60 AS INTEGER)) as tempo_medio_minutos
        FROM entregas
        WHERE status = 'finalizada' 
        AND motoboy_nome IS NOT NULL
        AND data_inicio IS NOT NULL
        AND data_finalizacao IS NOT NULL
    '''
    
    params = []
    if data_inicio:
        query += ' AND date(data_finalizacao) >= ?'
        params.append(data_inicio)
    if data_fim:
        query += ' AND date(data_finalizacao) <= ?'
        params.append(data_fim)
    
    query += ' GROUP BY motoboy_nome ORDER BY total_entregas DESC'
    
    resultados = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in resultados])

# API - Ranking de tempos
@app.route('/api/admin/stats/ranking-tempos', methods=['GET'])
def ranking_tempos():
    db = get_db()
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    query = '''
        SELECT 
            motoboy_nome,
            COUNT(*) as total_entregas,
            AVG(CAST((julianday(data_finalizacao) - julianday(data_inicio)) * 24 * 60 AS INTEGER)) as tempo_medio_minutos,
            MIN(CAST((julianday(data_finalizacao) - julianday(data_inicio)) * 24 * 60 AS INTEGER)) as melhor_tempo_minutos
        FROM entregas
        WHERE status = 'finalizada' 
        AND motoboy_nome IS NOT NULL
        AND data_inicio IS NOT NULL
        AND data_finalizacao IS NOT NULL
    '''
    
    params = []
    if data_inicio:
        query += ' AND date(data_finalizacao) >= ?'
        params.append(data_inicio)
    if data_fim:
        query += ' AND date(data_finalizacao) <= ?'
        params.append(data_fim)
    
    query += ' GROUP BY motoboy_nome HAVING COUNT(*) >= 3 ORDER BY tempo_medio_minutos ASC LIMIT 10'
    
    resultados = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in resultados])

# API - Ranking de bairros
@app.route('/api/admin/stats/ranking-bairros', methods=['GET'])
def ranking_bairros():
    db = get_db()
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    query = '''
        SELECT 
            bairro,
            COUNT(*) as total_entregas
        FROM entregas
        WHERE status = 'finalizada' 
        AND bairro IS NOT NULL
        AND bairro != ''
    '''
    
    params = []
    if data_inicio:
        query += ' AND date(data_finalizacao) >= ?'
        params.append(data_inicio)
    if data_fim:
        query += ' AND date(data_finalizacao) <= ?'
        params.append(data_fim)
    
    query += ' GROUP BY bairro ORDER BY total_entregas DESC LIMIT 15'
    
    resultados = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in resultados])

# API - Ranking completo de motoboys
@app.route('/api/admin/ranking-motoboys', methods=['GET'])
def ranking_motoboys():
    db = get_db()
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Query complexa para calcular todas as métricas
    query = '''
        SELECT 
            motoboy_nome,
            
            -- Entregas Turbo Finalizadas
            SUM(CASE 
                WHEN tipo_entrega = 'Turbo' AND status = 'finalizada' 
                THEN 1 ELSE 0 
            END) as entregas_turbo,
            
            -- Entregas Duplas Finalizadas
            SUM(CASE 
                WHEN quantidade_pedidos = 'Duplo' AND status = 'finalizada' 
                THEN 1 ELSE 0 
            END) as entregas_duplas,
            
            -- Entregas Simples Finalizadas
            SUM(CASE 
                WHEN quantidade_pedidos = 'Simples' AND status = 'finalizada' 
                THEN 1 ELSE 0 
            END) as entregas_simples,
            
            -- Entregas Canceladas mas Pagas
            SUM(CASE 
                WHEN status = 'cancelada' AND pedido_pago = 1 
                THEN 1 ELSE 0 
            END) as entregas_canceladas_pagas,
            
            -- Total de Entregas Finalizadas
            SUM(CASE 
                WHEN status = 'finalizada' 
                THEN 1 ELSE 0 
            END) as total_finalizadas,
            
            -- Pontuação Total (Duplas = 2, Simples = 1, Canceladas Pagas = 1)
            SUM(CASE 
                WHEN quantidade_pedidos = 'Duplo' AND status = 'finalizada' THEN 2
                WHEN status = 'finalizada' THEN 1
                WHEN status = 'cancelada' AND pedido_pago = 1 THEN 1
                ELSE 0 
            END) as pontuacao_total
            
        FROM entregas
        WHERE motoboy_nome IS NOT NULL 
        AND motoboy_nome != ''
    '''
    
    params = []
    if data_inicio:
        query += ' AND date(data_criacao) >= ?'
        params.append(data_inicio)
    if data_fim:
        query += ' AND date(data_criacao) <= ?'
        params.append(data_fim)
    
    query += ' GROUP BY motoboy_nome ORDER BY pontuacao_total DESC'
    
    resultados = db.execute(query, params).fetchall()
    motoboys = [dict(r) for r in resultados]
    
    # Calcular totais gerais
    totais = {
        'motoboy_nome': 'TOTAL GERAL',
        'entregas_turbo': sum(m['entregas_turbo'] for m in motoboys),
        'entregas_duplas': sum(m['entregas_duplas'] for m in motoboys),
        'entregas_simples': sum(m['entregas_simples'] for m in motoboys),
        'entregas_canceladas_pagas': sum(m['entregas_canceladas_pagas'] for m in motoboys),
        'total_finalizadas': sum(m['total_finalizadas'] for m in motoboys),
        'pontuacao_total': sum(m['pontuacao_total'] for m in motoboys)
    }
    
    return jsonify({
        'motoboys': motoboys,
        'totais': totais
    })

# API - Cancelar entrega
@app.route('/api/entregas/<codigo_pedido>/cancelar', methods=['PUT'])
def cancelar_entrega(codigo_pedido):
    try:
        data = request.json
        db = get_db()
        
        # Verificar senha admin
        senha_hash = hashlib.sha256(data['senha_admin'].encode()).hexdigest()
        admin = db.execute('SELECT * FROM usuarios WHERE password = ?', (senha_hash,)).fetchone()
        
        if not admin:
            return jsonify({'success': False, 'message': 'Senha administrativa incorreta'}), 401
        
        # Cancelar entrega
        db.execute('''
            UPDATE entregas 
            SET status = 'cancelada',
                motivo_cancelamento = ?,
                pedido_pago = ?,
                data_cancelamento = ?
            WHERE codigo_pedido = ?
        ''', (data['motivo'], data.get('pedido_pago', False), datetime.now(), codigo_pedido))
        
        db.commit()
        
        return jsonify({'success': True, 'message': 'Entrega cancelada com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# API - CRUD Motoboys
@app.route('/api/admin/motoboys', methods=['GET'])
def listar_motoboys_api():
    try:
        db = get_db()
        motoboys = db.execute('SELECT id, nome, username, telefone, ativo FROM motoboys ORDER BY nome').fetchall()
        return jsonify([dict(m) for m in motoboys])
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/motoboys', methods=['POST'])
def criar_motoboy_api():
    try:
        data = request.json
        db = get_db()
        
        # Verificar se username já existe
        existe = db.execute('SELECT * FROM motoboys WHERE username = ?', (data['username'],)).fetchone()
        if existe:
            return jsonify({'success': False, 'message': 'Usuário já existe'}), 400
        
        # Criptografar senha

        senha_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        cursor = db.execute('''
            INSERT INTO motoboys (nome, username, password, telefone, ativo)
            VALUES (?, ?, ?, ?, 1)
        ''', (data['nome'], data['username'], senha_hash, data.get('telefone', '')))
        
        db.commit()
        
        return jsonify({
            'success': True,
            'id': cursor.lastrowid,
            'message': 'Motoboy criado com sucesso'
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/motoboys/<int:id>', methods=['PUT'])
def atualizar_motoboy_api(id):
    try:
        data = request.json
        db = get_db()
        
        # Verificar se está tentando mudar username para um que já existe
        if 'username' in data:
            existe = db.execute('SELECT * FROM motoboys WHERE username = ? AND id != ?', 
                              (data['username'], id)).fetchone()
            if existe:
                return jsonify({'success': False, 'message': 'Usuário já existe'}), 400
        
        # Atualizar senha se fornecida
        if 'password' in data and data['password']:
    
            senha_hash = hashlib.sha256(data['password'].encode()).hexdigest()
            db.execute('''
                UPDATE motoboys 
                SET nome = ?, username = ?, password = ?, telefone = ?
                WHERE id = ?
            ''', (data['nome'], data['username'], senha_hash, data.get('telefone', ''), id))
        else:
            db.execute('''
                UPDATE motoboys 
                SET nome = ?, username = ?, telefone = ?
                WHERE id = ?
            ''', (data['nome'], data['username'], data.get('telefone', ''), id))
        
        db.commit()
        
        return jsonify({'success': True, 'message': 'Motoboy atualizado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/motoboys/<int:id>/toggle', methods=['PUT'])
def toggle_motoboy_api(id):
    try:
        db = get_db()
        
        motoboy = db.execute('SELECT ativo FROM motoboys WHERE id = ?', (id,)).fetchone()
        if not motoboy:
            return jsonify({'success': False, 'message': 'Motoboy não encontrado'}), 404
        
        novo_status = 0 if motoboy['ativo'] == 1 else 1
        
        db.execute('UPDATE motoboys SET ativo = ? WHERE id = ?', (novo_status, id))
        db.commit()
        
        return jsonify({
            'success': True, 
            'ativo': novo_status,
            'message': 'Status atualizado'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/motoboys/<int:id>', methods=['DELETE'])
def deletar_motoboy_api(id):
    try:
        db = get_db()
        
        # Verificar se tem entregas
        entregas = db.execute('SELECT COUNT(*) as count FROM entregas WHERE motoboy_nome IN (SELECT nome FROM motoboys WHERE id = ?)', (id,)).fetchone()
        
        if entregas['count'] > 0:
            return jsonify({
                'success': False, 
                'message': f'Não é possível deletar. Este motoboy possui {entregas["count"]} entrega(s) registrada(s).'
            }), 400
        
        db.execute('DELETE FROM motoboys WHERE id = ?', (id,))
        db.commit()
        
        return jsonify({'success': True, 'message': 'Motoboy deletado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
