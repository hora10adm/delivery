#!/usr/bin/env python3
"""
Script de Migração - Sistema Hora 10
Adiciona novas colunas ao banco sem perder dados existentes
"""

import sqlite3
import os

# Caminho do banco
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'entregas.db')

print("=" * 60)
print("🔄 MIGRAÇÃO DO BANCO DE DADOS - SISTEMA HORA 10")
print("=" * 60)
print(f"\n📍 Banco de dados: {DATABASE}\n")

# Conectar ao banco
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# Lista de colunas para adicionar
novas_colunas = [
    ('quantidade_pedidos', 'TEXT'),
    ('tipo_entrega', 'TEXT'),
    ('valor_turbo', 'REAL'),
    ('data_cancelamento', 'TIMESTAMP'),
    ('motivo_cancelamento', 'TEXT'),
    ('pedido_pago', 'INTEGER DEFAULT 0')
]

print("🔍 Verificando colunas existentes...\n")

# Obter colunas atuais
cursor.execute("PRAGMA table_info(entregas)")
colunas_existentes = [row[1] for row in cursor.fetchall()]

print(f"✅ Colunas atuais: {', '.join(colunas_existentes)}\n")

# Adicionar cada coluna se não existir
colunas_adicionadas = []
colunas_ja_existem = []

for nome_coluna, tipo_coluna in novas_colunas:
    if nome_coluna not in colunas_existentes:
        try:
            sql = f"ALTER TABLE entregas ADD COLUMN {nome_coluna} {tipo_coluna}"
            cursor.execute(sql)
            colunas_adicionadas.append(nome_coluna)
            print(f"✅ Coluna '{nome_coluna}' adicionada com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao adicionar '{nome_coluna}': {e}")
    else:
        colunas_ja_existem.append(nome_coluna)
        print(f"ℹ️  Coluna '{nome_coluna}' já existe")

# Commit das mudanças
conn.commit()

# Verificar resultado final
cursor.execute("PRAGMA table_info(entregas)")
colunas_finais = [row[1] for row in cursor.fetchall()]

# Contar entregas
cursor.execute("SELECT COUNT(*) FROM entregas")
total_entregas = cursor.fetchone()[0]

# Fechar conexão
conn.close()

print("\n" + "=" * 60)
print("📊 RESUMO DA MIGRAÇÃO")
print("=" * 60)
print(f"\n✅ Colunas adicionadas: {len(colunas_adicionadas)}")
if colunas_adicionadas:
    for col in colunas_adicionadas:
        print(f"   • {col}")

if colunas_ja_existem:
    print(f"\nℹ️  Colunas que já existiam: {len(colunas_ja_existem)}")
    for col in colunas_ja_existem:
        print(f"   • {col}")

print(f"\n📦 Total de entregas preservadas: {total_entregas}")
print(f"\n📋 Total de colunas na tabela: {len(colunas_finais)}")

print("\n" + "=" * 60)
print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
print("=" * 60)
print("\n💡 Próximos passos:")
print("   1. Reinicie o serviço no Render")
print("   2. Teste criar uma nova entrega")
print("   3. Verifique se os novos campos aparecem")
print("\n🎉 Todas as entregas foram preservadas!\n")
