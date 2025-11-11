import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import uuid
import time
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

# ===============================
# CONFIGURAÇÕES CENTRALIZADAS
# ===============================

SENHA_AUTORIZACAO = "admin123"
SPREADSHEET_ID = "1rRYEj-Kvtyqqu8YQSiw-v2dgMf5a_kGYV7aQa1ue1JI"
WORKSHEET_NAME = "Pedidos"
STATUS_PEDIDO = ["Pendente", "Solicitado", "Entregue"]

# Configurações de Email (ALTERE ESTES VALORES)
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",  # Para Gmail
    "smtp_port": 587,
    "sender_email": "sergio.basiewicz@printerdobrasil.com.br",  # ⬅️ ALTERE
    "sender_password": "xnnk kele gijs gklg",  # ⬅️ ALTERE (senha de app do Gmail)
    "recipient_emails": ["sergio.basiewicz@printerdobrasil.com.br"],  # ⬅️ ALTERE
    "timeout": 10  # Timeout em segundos
}

# Mapeamento de status para emojis
STATUS_EMOJIS = {
    "Pendente": "🔴",
    "Solicitado": "🟡", 
    "Entregue": "🟢"
}

# ===============================
# CONFIGURAÇÃO DE ESTILO
# ===============================

def configurar_pagina():
    st.set_page_config(
        page_title="Controle de Pedidos",
        page_icon="📦",
        layout="wide"
    )

# ===============================
# SISTEMA DE NOTIFICAÇÃO POR EMAIL - VERSÃO CORRIGIDA
# ===============================

def enviar_email_notificacao(novo_id, tecnico, peca, modelo_equipamento, numero_serie, ordem_servico, observacoes):
    """
    Envia email de notificação quando um novo pedido é criado
    """
    # Verificar se o email está configurado
    if (not EMAIL_CONFIG["sender_email"] or 
        EMAIL_CONFIG["sender_email"] == "seu.email@gmail.com" or
        not EMAIL_CONFIG["sender_password"] or
        EMAIL_CONFIG["sender_password"] == "sua_senha_de_app"):
        st.sidebar.warning("⚠️ Email não configurado - Configure as credenciais no código")
        return False
    
    try:
        # Configurações do email
        smtp_server = EMAIL_CONFIG["smtp_server"]
        port = EMAIL_CONFIG["smtp_port"]
        sender_email = EMAIL_CONFIG["sender_email"]
        password = EMAIL_CONFIG["sender_password"]
        receiver_emails = EMAIL_CONFIG["recipient_emails"]
        timeout = EMAIL_CONFIG["timeout"]
        
        # Criar mensagem
        subject = f"📦 Novo Pedido de Peça - ID: {novo_id}"
        
        body = f"""
        <html>
        <body>
            <h2 style="color: #2E86AB;">📦 Novo Pedido de Peça Registrado</h2>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #2E86AB;">
                <h3 style="color: #2E86AB; margin-top: 0;">Detalhes do Pedido:</h3>
                
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold; width: 30%;">ID do Pedido:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>{novo_id}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Técnico:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{tecnico}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Peça Solicitada:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{peca}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Modelo do Equipamento:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{modelo_equipamento or 'Não informado'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Número de Série:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{numero_serie or 'Não informado'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Ordem de Serviço:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{ordem_servico or 'Não informada'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Observações:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{observacoes or 'Nenhuma'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Data/Hora:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Status:</td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">🔴 Pendente</td>
                    </tr>
                </table>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background-color: #e7f3ff; border-radius: 5px;">
                <p style="margin: 0; color: #2E86AB;">
                    <strong>Acesse o sistema para mais detalhes.</strong>
                </p>
            </div>
            
            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <p>Este é um email automático do Sistema de Controle de Pedidos de Peças.</p>
            </div>
        </body>
        </html>
        """
        
        # Criar mensagem MIME
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = ", ".join(receiver_emails)
        
        # Adicionar corpo HTML
        html_part = MIMEText(body, "html")
        message.attach(html_part)
        
        # Criar contexto SSL seguro
        context = ssl.create_default_context()
        
        # Enviar email com timeout
        with smtplib.SMTP(smtp_server, port, timeout=timeout) as server:
            server.ehlo()  # Identificar com o servidor
            server.starttls(context=context)  # Segurança
            server.ehlo()  # Reidentificar após TLS
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_emails, message.as_string())
        
        st.sidebar.success("📧 Email de notificação enviado!")
        return True
        
    except smtplib.SMTPAuthenticationError:
        st.sidebar.error("❌ Falha na autenticação do email. Verifique usuário/senha.")
        return False
    except smtplib.SMTPConnectError:
        st.sidebar.error("❌ Não foi possível conectar ao servidor de email.")
        return False
    except smtplib.SMTPException as e:
        st.sidebar.error(f"❌ Erro no servidor SMTP: {str(e)}")
        return False
    except Exception as e:
        st.sidebar.error(f"❌ Erro inesperado ao enviar email: {str(e)}")
        return False

def verificar_configuracao_email():
    """Verifica se o email está configurado corretamente"""
    if (EMAIL_CONFIG["sender_email"] == "seu.email@gmail.com" or 
        EMAIL_CONFIG["sender_password"] == "sua_senha_de_app"):
        return False
    return True

# ===============================
# CONEXÃO COM GOOGLE SHEETS
# ===============================

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def inicializar_conexao_google_sheets():
    """Inicializa e retorna a conexão com o Google Sheets"""
    creds = carregar_credenciais()
    if creds is None:
        mostrar_erro_credenciais()
        st.stop()
    
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    st.sidebar.success("✅ Conectado ao Google Sheets")
    return sheet

def carregar_credenciais():
    """Carrega as credenciais do Google Sheets"""
    # Tenta carregar das variáveis de ambiente (produção)
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        except Exception as e:
            st.error(f"Erro nas credenciais de variável de ambiente: {e}")
    
    # Tenta carregar de arquivo local (desenvolvimento)
    try:
        if os.path.exists('credenciais.json'):
            return ServiceAccountCredentials.from_json_keyfile_name('credenciais.json', SCOPE)
    except Exception as e:
        st.error(f"Erro ao carregar credenciais.json: {e}")
    
    return None

def mostrar_erro_credenciais():
    """Mostra mensagem de erro para credenciais não encontradas"""
    st.error("""
    ❌ Credenciais do Google Sheets não encontradas!
    
    Para desenvolvimento local:
    1. Baixe o arquivo JSON de credenciais do Google Cloud
    2. Renomeie para 'credenciais.json' 
    3. Coloque na mesma pasta do script
    
    Para produção:
    Configure a variável de ambiente GOOGLE_CREDENTIALS
    """)

# ===============================
# FUNÇÕES AUXILIARES
# ===============================

def formatar_status(status):
    """Formata o status adicionando o emoji correspondente"""
    status_limpo = status.replace(':', '').strip()  # Remove possíveis dois pontos
    emoji = STATUS_EMOJIS.get(status_limpo, "⚪")
    return f"{emoji} {status}"

def obter_emoji_status(status):
    """Retorna apenas o emoji do status"""
    status_limpo = status.replace(':', '').strip()
    return STATUS_EMOJIS.get(status_limpo, "⚪")

# ===============================
# FUNÇÕES DE DADOS
# ===============================

def obter_todos_pedidos():
    """Retorna todos os pedidos como DataFrame"""
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Formatar a coluna de status com emojis, se existir
    if 'Status:' in df.columns:
        df['Status:'] = df['Status:'].apply(lambda x: formatar_status(str(x)))
    
    return df

def adicionar_novo_pedido(numero_serie, peca, tecnico, modelo_equipamento, ordem_servico, observacoes):
    """Adiciona um novo pedido à planilha"""
    linhas = sheet.get_all_values()
    ids_existentes = [linha[8] for linha in linhas if len(linha) > 8]
    
    # Gerar ID único
    novo_id = gerar_id_unico(ids_existentes)
    
    # Preparar dados do pedido
    data = datetime.now().strftime("%d/%m/%Y")
    status = "Pendente"
    
    nova_linha = [
        data, status, tecnico, peca, modelo_equipamento, 
        numero_serie, ordem_servico, observacoes, novo_id
    ]
    
    sheet.append_row(nova_linha)
    st.success(f"✅ Pedido {novo_id} adicionado com sucesso!")
    
    # Enviar email de notificação (não bloqueante)
    if verificar_configuracao_email():
        try:
            with st.spinner("Enviando notificação por email..."):
                enviar_email_notificacao(novo_id, tecnico, peca, modelo_equipamento, numero_serie, ordem_servico, observacoes)
        except Exception as e:
            st.sidebar.warning(f"⚠️ Email não enviado, mas pedido foi salvo: {str(e)}")
    else:
        st.sidebar.warning("⚠️ Email não configurado - Configure as credenciais")

def gerar_id_unico(ids_existentes):
    """Gera um ID único para o pedido"""
    while True:
        novo_id = str(uuid.uuid4())[:8]
        if novo_id not in ids_existentes:
            return novo_id

def atualizar_status_pedido(pedido_id, novo_status):
    """Atualiza o status de um pedido específico"""
    pedidos = sheet.get_all_values()
    for i, linha in enumerate(pedidos):
        if len(linha) > 8 and linha[8] == str(pedido_id):
            sheet.update_cell(i + 1, 2, novo_status)
            st.success(f"✅ Status do pedido {pedido_id} atualizado para {formatar_status(novo_status)}")
            return True
    st.error("❌ Pedido não encontrado")
    return False

# ===============================
# FUNÇÕES DE INTERFACE - ADICIONAR PEDIDO
# ===============================

def mostrar_formulario_adicionar_pedido():
    """Exibe o formulário para adicionar novo pedido"""
    st.header("📝 Adicionar Novo Pedido")
    
    # Mostrar status da configuração de email
    if not verificar_configuracao_email():
        st.warning("""
        ⚠️ **Sistema de Email Não Configurado**
        
        Para ativar as notificações por email, configure no código:
        1. **EMAIL_CONFIG** - linhas 20-27
        2. **sender_email**: seu email Gmail
        3. **sender_password**: senha de app do Gmail
        4. **recipient_emails**: lista de emails para notificar
        """)
    
    with st.form("form_adicionar_pedido"):
        col1, col2 = st.columns(2)
        
        with col1:
            tecnico = st.text_input("👤 Técnico *", help="Nome do técnico responsável")
            peca = st.text_input("🔧 Peça *", help="Descrição da peça necessária")
            modelo_equipamento = st.text_input("💻 Modelo do Equipamento", help="Modelo do equipamento")
        
        with col2:
            numero_serie = st.text_input("🔢 Número de Série", help="Número de série do equipamento")
            ordem_servico = st.text_input("📄 OS", help="Número da ordem de serviço")
            observacoes = st.text_area("📝 Observações", help="Observações adicionais")
        
        submitted = st.form_submit_button("➕ Adicionar Pedido")
        
        if submitted:
            if validar_formulario(tecnico, peca):
                adicionar_novo_pedido(numero_serie, peca, tecnico, modelo_equipamento, ordem_servico, observacoes)
                time.sleep(2)  # Dar tempo para ver as mensagens
                st.rerun()

def validar_formulario(tecnico, peca):
    """Valida os campos obrigatórios do formulário"""
    if not tecnico.strip():
        st.error("⚠️ O campo Técnico é obrigatório!")
        return False
    if not peca.strip():
        st.error("⚠️ O campo Peça é obrigatório!")
        return False
    return True

# ... (o restante do código permanece igual - funções de visualização, atualização status, etc.)
