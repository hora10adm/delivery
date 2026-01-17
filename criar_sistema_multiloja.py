#!/usr/bin/env python3
"""
Script para adicionar sistema MULTI-LOJA ao Sistema Hora 10
- Cria tabela de lojas
- Adiciona coluna loja_id nas entregas
- Cria sistema de sessões
"""

import sqlite3
import hashlib
import os

# Usa o banco na pasta atual (funciona em Windows e Linux)
DATABASE = os.path.join(os.path.dirname(__file__), 'entregas.db')

def criar_tabela_lojas():
    """Cria tabela de lojas"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lojas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            identificador TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    print("✅ Tabela 'lojas' criada com sucesso!")
    return conn

def adicionar_coluna_loja_entregas(conn):
    """Adiciona coluna loja_id na tabela entregas"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(entregas)")
        colunas = [row[1] for row in cursor.fetchall()]
        
        if 'loja_id' not in colunas:
            cursor.execute('ALTER TABLE entregas ADD COLUMN loja_id INTEGER DEFAULT 1')
            conn.commit()
            print("✅ Coluna 'loja_id' adicionada na tabela entregas!")
        else:
            print("ℹ️  Coluna 'loja_id' já existe na tabela entregas")
    except Exception as e:
        print(f"⚠️  Erro ao adicionar coluna: {e}")

def adicionar_coluna_loja_motoboys(conn):
    """Adiciona coluna loja_id na tabela motoboys"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(motoboys)")
        colunas = [row[1] for row in cursor.fetchall()]
        
        if 'loja_id' not in colunas:
            cursor.execute('ALTER TABLE motoboys ADD COLUMN loja_id INTEGER DEFAULT 1')
            conn.commit()
            print("✅ Coluna 'loja_id' adicionada na tabela motoboys!")
        else:
            print("ℹ️  Coluna 'loja_id' já existe na tabela motoboys")
    except Exception as e:
        print(f"⚠️  Erro ao adicionar coluna: {e}")

def criar_lojas_exemplo(conn):
    """Cria lojas de exemplo"""
    cursor = conn.cursor()
    
    # Lojas de exemplo
    lojas = [
        {
            'nome': 'Loja Centro',
            'identificador': 'centro',
            'senha': 'centro123'
        },
        {
            'nome': 'Loja Shopping',
            'identificador': 'shopping',
            'senha': 'shopping123'
        },
        {
            'nome': 'Loja Bairro Norte',
            'identificador': 'norte',
            'senha': 'norte123'
        }
    ]
    
    for loja in lojas:
        senha_hash = hashlib.sha256(loja['senha'].encode()).hexdigest()
        
        try:
            cursor.execute('''
                INSERT INTO lojas (nome, identificador, senha_hash)
                VALUES (?, ?, ?)
            ''', (loja['nome'], loja['identificador'], senha_hash))
            print(f"✅ Loja '{loja['nome']}' criada! Login: {loja['identificador']} | Senha: {loja['senha']}")
        except sqlite3.IntegrityError:
            print(f"ℹ️  Loja '{loja['nome']}' já existe")
    
    conn.commit()

def main():
    """Função principal"""
    print("=" * 70)
    print("🏪 CRIANDO SISTEMA MULTI-LOJA - HORA 10")
    print("=" * 70)
    print()
    
    # 1. Criar tabela de lojas
    conn = criar_tabela_lojas()
    
    # 2. Adicionar coluna loja_id nas entregas
    adicionar_coluna_loja_entregas(conn)
    
    # 3. Adicionar coluna loja_id nos motoboys
    adicionar_coluna_loja_motoboys(conn)
    
    # 4. Criar lojas de exemplo
    print()
    print("📝 Criando lojas de exemplo...")
    criar_lojas_exemplo(conn)
    
    conn.close()
    
    print()
    print("=" * 70)
    print("✅ SISTEMA MULTI-LOJA CRIADO COM SUCESSO!")
    print("=" * 70)
    print()
    print("🔑 LOJAS CRIADAS:")
    print()
    print("1. Loja Centro")
    print("   Login: centro")
    print("   Senha: centro123")
    print()
    print("2. Loja Shopping")
    print("   Login: shopping")
    print("   Senha: shopping123")
    print()
    print("3. Loja Bairro Norte")
    print("   Login: norte")
    print("   Senha: norte123")
    print()
    print("📋 Próximos passos:")
    print("   1. Atualizar app.py com rotas de login multi-loja")
    print("   2. Criar template de login multi-loja")
    print("   3. Adicionar filtros por loja_id nas consultas")

if __name__ == '__main__':
    main()
