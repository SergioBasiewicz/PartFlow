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
    "recipient_emails": ["sergio.basiewicz@printerdobrasil.com.br"]  # ⬅️ ALTERE
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
# SISTEMA DE NOTIFICAÇÃO POR EMAIL
# ===============================

def enviar_email_notificacao(novo_id, tecnico, peca, modelo_equipamento, numero_serie, ordem_servico, observacoes):
    """
    Envia email de notificação quando um novo pedido é criado
    """
    try:
        # Configurações do email
        smtp_server = EMAIL_CONFIG["smtp_server"]
        port = EMAIL_CONFIG["smtp_port"]
        sender_email = EMAIL_CONFIG["sender_email"]
        password = EMAIL_CONFIG["sender_password"]
        receiver_emails = EMAIL_CONFIG["recipient_emails"]
        
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
                    <strong>Acesse o sistema:</strong> 
                    <a href="#" style="color: #2E86AB;">Clique aqui para ver todos os pedidos</a>
                </p>
            </div>
            
            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <p>Este é um email automático do Sistema de Controle de Pedidos de Peças.</p>
            </div>
        </body>
        </html>
        """
        
        # Criar mensagem MIME (CORREÇÃO DOS NOMES)
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = ", ".join(receiver_emails)
        
        # Adicionar corpo HTML
        html_part = MIMEText(body, "html")
        message.attach(html_part)
        
        # Criar contexto SSL seguro
        context = ssl.create_default_context()
        
        # Enviar email
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context)
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_emails, message.as_string())
        
        st.sidebar.success("📧 Email de notificação enviado!")
        return True
        
    except Exception as e:
        st.sidebar.warning(f"⚠️ Email não enviado: {str(e)}")
        return False

def testar_configuracao_email():
    """
    Testa a configuração de email (opcional)
    """
    try:
        smtp_server = EMAIL_CONFIG["smtp_server"]
        port = EMAIL_CONFIG["smtp_port"]
        sender_email = EMAIL_CONFIG["sender_email"]
        password = EMAIL_CONFIG["sender_password"]
        
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context)
            server.login(sender_email, password)
        
        return True
    except Exception as e:
        return False

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
    
    # Enviar email de notificação
    with st.spinner("Enviando notificação por email..."):
        enviar_email_notificacao(novo_id, tecnico, peca, modelo_equipamento, numero_serie, ordem_servico, observacoes)

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
    if not EMAIL_CONFIG["sender_email"] or EMAIL_CONFIG["sender_email"] == "seu.email@gmail.com":
        st.warning("⚠️ Configure as informações de email no código para receber notificações")
    
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

# ===============================
# FUNÇÕES DE INTERFACE - VISUALIZAR PEDIDOS
# ===============================

def mostrar_lista_pedidos():
    """Exibe a lista de todos os pedidos e estatísticas"""
    st.header("📋 Lista de Pedidos")
    
    df = obter_todos_pedidos()
    
    if not df.empty:
        # Mostrar dataframe
        st.dataframe(df, use_container_width=True)
        
        # Mostrar estatísticas
        mostrar_estatisticas(df)
    else:
        st.info("📭 Nenhum pedido cadastrado no momento.")

def mostrar_estatisticas(df):
    """Exibe estatísticas dos pedidos"""
    st.subheader("📊 Estatísticas")
    
    # Criar DataFrame temporário sem emojis para contar
    df_temp = df.copy()
    if 'Status:' in df_temp.columns:
        df_temp['Status:'] = df_temp['Status:'].str.replace(r'[🔴🟡🟢⚪] ', '', regex=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pedidos = len(df)
        st.metric("Total de Pedidos", total_pedidos)
    
    with col2:
        pendentes = len(df_temp[df_temp['Status:'] == 'Pendente'])
        st.metric("🔴 Pendentes", pendentes)
    
    with col3:
        solicitados = len(df_temp[df_temp['Status:'] == 'Solicitado'])
        st.metric("🟡 Solicitados", solicitados)
    
    with col4:
        entregues = len(df_temp[df_temp['Status:'] == 'Entregue'])
        taxa_entrega = (entregues / total_pedidos * 100) if total_pedidos > 0 else 0
        st.metric("🟢 Entregues", f"{entregues} ({taxa_entrega:.1f}%)")

# ===============================
# FUNÇÕES DE INTERFACE - ATUALIZAR STATUS
# ===============================

def mostrar_pagina_atualizar_status():
    """Exibe a página para atualizar status dos pedidos"""
    st.header("🔄 Atualizar Status do Pedido")
    
    if not st.session_state.autorizado:
        mostrar_formulario_autenticacao()
    else:
        mostrar_interface_administrativa()

def mostrar_formulario_autenticacao():
    """Exibe formulário de autenticação para administradores"""
    with st.form("form_autenticacao"):
        senha = st.text_input("🔒 Digite a senha de autorização", type="password")
        submitted = st.form_submit_button("✅ Validar Senha")
        
        if submitted:
            if senha == SENHA_AUTORIZACAO:
                st.session_state.autorizado = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta. Tente novamente.")

def mostrar_interface_administrativa():
    """Exibe a interface administrativa para atualizar status"""
    # Controles administrativos na sidebar
    mostrar_controles_admin()
    
    # Lista de pedidos na sidebar
    mostrar_lista_pedidos_sidebar()
    
    # Formulário de atualização no main
    mostrar_formulario_atualizacao_status()

def mostrar_controles_admin():
    """Exibe controles administrativos na sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔧 Controles Administrativos")
    
    if st.sidebar.button("🚪 Sair do Modo Admin"):
        st.session_state.autorizado = False
        st.rerun()

def mostrar_lista_pedidos_sidebar():
    """Exibe lista resumida de pedidos na sidebar"""
    st.sidebar.subheader("📦 Todos os Pedidos")
    
    dados_brutos = sheet.get_all_values()
    
    if len(dados_brutos) > 1:
        dados = dados_brutos[1:]
        
        with st.sidebar.container():
            for linha in dados:
                if linha and len(linha) > 8 and linha[8]:  # Verifica se existe ID
                    mostrar_card_pedido(linha)
            
            st.sidebar.caption(f"📊 Total: {len(dados)} pedidos")
    else:
        st.sidebar.info("🎯 Nenhum pedido cadastrado")

def mostrar_card_pedido(linha):
    """Exibe um card individual para cada pedido"""
    status = linha[1] if len(linha) > 1 else "Pendente"
    emoji_status = obter_emoji_status(status)
    
    with st.expander(f"{emoji_status} Pedido {linha[8]} - {linha[2]}", expanded=False):
        st.write(f"Pedido:  {linha[8]}")
        st.write(f"**Data:** {linha[0]}")
        st.write(f"**Status:** {formatar_status(status)}")
        st.write(f"**Técnico:** {linha[2]}")
        st.write(f"**Peça:** {linha[3]}")
        st.write(f"**Modelo:** {linha[4]}")
        st.write(f"**Nº Série:** {linha[5]}")
        st.write(f"**OS:** {linha[6]}")
        
        if len(linha) > 7 and linha[7]:
            st.write(f"**Observações:**")
            st.info(linha[7])

def mostrar_formulario_atualizacao_status():
    """Exibe formulário para atualizar status do pedido"""
    st.subheader("Atualizar Status")
    
    with st.form("form_atualizacao_status"):
        col1, col2 = st.columns(2)
        
        with col1:
            pedido_id = st.text_input("🔢 ID do Pedido *")
        
        with col2:
            # Adicionar emojis nas opções do selectbox
            opcoes_status = [f"{STATUS_EMOJIS[status]} {status}" for status in STATUS_PEDIDO]
            novo_status_formatado = st.selectbox("🔄 Novo Status", opcoes_status)
            # Extrair apenas o texto do status (sem emoji) para salvar
            novo_status = novo_status_formatado.split(' ', 1)[1]
        
        submitted = st.form_submit_button("🔄 Atualizar Status")
        
        if submitted:
            if pedido_id.strip():
                if atualizar_status_pedido(pedido_id, novo_status):
                    st.success("Status atualizado! Atualizando lista...")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("⚠️ Por favor, informe o ID do pedido")

# ===============================
# INICIALIZAÇÃO E CONFIGURAÇÃO PRINCIPAL
# ===============================

def inicializar_session_state():
    """Inicializa variáveis de session_state"""
    if 'autorizado' not in st.session_state:
        st.session_state.autorizado = False

def main():
    """Função principal da aplicação"""
    # Configurações iniciais
    configurar_pagina()
    inicializar_session_state()
    
    # Título principal
    st.title("📦 Controle de Pedidos de Peças Usadas")
    
    # Menu lateral
    menu = st.sidebar.selectbox(
        "📂 Menu",
        ["Adicionar Pedido", "Visualizar Pedidos", "Atualizar Status"]
    )
    
    # Navegação entre páginas
    if menu == "Adicionar Pedido":
        mostrar_formulario_adicionar_pedido()
    
    elif menu == "Visualizar Pedidos":
        mostrar_lista_pedidos()
    
    elif menu == "Atualizar Status":
        mostrar_pagina_atualizar_status()

# ===============================
# EXECUÇÃO DA APLICAÇÃO
# ===============================

if __name__ == "__main__":
    # Inicializar conexão com Google Sheets (global)
    sheet = inicializar_conexao_google_sheets()
    
    # Executar aplicação
    main()