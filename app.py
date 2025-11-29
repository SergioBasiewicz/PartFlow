# app.py - VERSÃO SIMPLIFICADA ENQUANTO RESOLVEMOS OS SECRETS
import streamlit as st
import uuid
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Controle de Pedidos",
    page_icon="📦", 
    layout="wide"
)

# CSS
st.markdown("""
<style>
.main {
    background-color: #0d1113;
    color: #e6eef8;
}
.card {
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    border: 1px solid rgba(255,255,255,0.1);
}
</style>
""", unsafe_allow_html=True)

# Configurações
SENHA_AUTORIZACAO = "admin123"
STATUS_PEDIDO = ["Pendente", "Solicitado", "Entregue"]
STATUS_EMOJIS = {"Pendente": "🔴", "Solicitado": "🟡", "Entregue": "🟢"}

# Debug dos Secrets
st.sidebar.title("🔧 Debug Secrets")

try:
    secrets_keys = list(st.secrets.keys())
    st.sidebar.write("Chaves encontradas:", secrets_keys)
    
    if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
        st.sidebar.success("✅ GOOGLE_APPLICATION_CREDENTIALS_JSON: ENCONTRADO")
        creds = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
        st.sidebar.write("Tipo:", type(creds))
    else:
        st.sidebar.error("❌ GOOGLE_APPLICATION_CREDENTIALS_JSON: NÃO ENCONTRADO")
        
    if 'FIREBASE_BUCKET' in st.secrets:
        st.sidebar.success(f"✅ FIREBASE_BUCKET: {st.secrets['FIREBASE_BUCKET']}")
    else:
        st.sidebar.error("❌ FIREBASE_BUCKET: NÃO ENCONTRADO")
        
except Exception as e:
    st.sidebar.error(f"Erro: {e}")

# Session State
if 'pedidos' not in st.session_state:
    st.session_state.pedidos = []
if 'autorizado' not in st.session_state:
    st.session_state.autorizado = False

# Funções
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def salvar_pedido(dados):
    pedido_id = str(uuid.uuid4())[:8]
    dados_completos = {**dados, 'id': pedido_id, 'data_criacao': datetime_now_str()}
    st.session_state.pedidos.append(dados_completos)
    return pedido_id

def listar_pedidos():
    return st.session_state.pedidos

def atualizar_status(pedido_id, novo_status):
    for pedido in st.session_state.pedidos:
        if pedido['id'] == pedido_id:
            pedido['status'] = novo_status
            return True
    return False

# Interface
def mostrar_formulario():
    st.header("📝 Adicionar Novo Pedido")
    
    with st.form("form"):
        col1, col2 = st.columns(2)
        
        with col1:
            tecnico = st.text_input("👤 Técnico *")
            peca = st.text_input("🔧 Peça *")
            modelo = st.text_input("💻 Modelo")
            
        with col2:
            numero_serie = st.text_input("🔢 Número de Série")
            ordem_servico = st.text_input("📄 OS")
            observacoes = st.text_area("📝 Observações")
        
        if st.form_submit_button("➕ Adicionar Pedido"):
            if tecnico and peca:
                dados = {
                    'tecnico': tecnico,
                    'peca': peca, 
                    'modelo': modelo,
                    'numero_serie': numero_serie,
                    'ordem_servico': ordem_servico,
                    'observacoes': observacoes,
                    'status': 'Pendente'
                }
                pedido_id = salvar_pedido(dados)
                st.success(f"✅ Pedido {pedido_id} salvo!")
                st.rerun()
            else:
                st.error("⚠️ Preencha Técnico e Peça!")

def mostrar_lista():
    st.header("📋 Lista de Pedidos")
    
    pedidos = listar_pedidos()
    if not pedidos:
        st.info("📭 Nenhum pedido cadastrado")
        return
    
    for pedido in pedidos:
        status = pedido['status']
        emoji = STATUS_EMOJIS[status]
        
        with st.expander(f"{emoji} {pedido['tecnico']} - {pedido['peca']} - ID: {pedido['id']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Data:** {pedido['data_criacao']}")
                st.write(f"**Técnico:** {pedido['tecnico']}")
                st.write(f"**Peça:** {pedido['peca']}")
            with col2:
                st.write(f"**Modelo:** {pedido['modelo']}")
                st.write(f"**Nº Série:** {pedido['numero_serie']}")
                st.write(f"**Status:** {emoji} {status}")

def mostrar_atualizar():
    st.header("🔄 Atualizar Status")
    
    if not st.session_state.autorizado:
        with st.form("auth"):
            senha = st.text_input("🔒 Senha", type="password")
            if st.form_submit_button("Entrar"):
                if senha == SENHA_AUTORIZACAO:
                    st.session_state.autorizado = True
                    st.rerun()
        return
    
    with st.form("update"):
        pedido_id = st.text_input("🔎 ID do Pedido")
        novo_status = st.selectbox("🔄 Novo Status", STATUS_PEDIDO)
        
        if st.form_submit_button("📥 Atualizar"):
            if pedido_id and atualizar_status(pedido_id, novo_status):
                st.success("✅ Status atualizado!")
                st.rerun()

# App Principal
def main():
    st.title("📦 Controle de Pedidos")
    
    menu = st.sidebar.selectbox(
        "📂 Menu", 
        ["Adicionar Pedido", "Visualizar Pedidos", "Atualizar Status"]
    )
    
    if menu == "Adicionar Pedido":
        mostrar_formulario()
    elif menu == "Visualizar Pedidos":
        mostrar_lista()
    elif menu == "Atualizar Status":
        mostrar_atualizar()

if __name__ == "__main__":
    main()
