# app.py - CONTROLE DE PEDIDOS (TUDO EM UM)
import streamlit as st
import uuid
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Controle de Pedidos",
    page_icon="📦",
    layout="wide"
)

# Configurações
SENHA_AUTORIZACAO = "admin123"
STATUS_PEDIDO = ["Pendente", "Solicitado", "Entregue"]
STATUS_EMOJIS = {"Pendente": "🔴", "Solicitado": "🟡", "Entregue": "🟢"}

# CSS personalizado
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

# Funções básicas
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# Session State para armazenar dados
if 'pedidos' not in st.session_state:
    st.session_state.pedidos = []
if 'autorizado' not in st.session_state:
    st.session_state.autorizado = False

# Funções do sistema
def salvar_pedido(dados, foto_bytes=None, nome_foto=None):
    """Salva pedido na session state"""
    try:
        pedido_id = str(uuid.uuid4())[:8]
        dados_completos = {
            **dados,
            'id': pedido_id,
            'foto_url': None,
            'tem_foto': foto_bytes is not None
        }
        
        st.session_state.pedidos.append(dados_completos)
        return pedido_id
    except Exception as e:
        return str(uuid.uuid4())[:8]

def listar_pedidos():
    """Retorna todos os pedidos"""
    return st.session_state.pedidos

def atualizar_status(pedido_id, novo_status):
    """Atualiza status de um pedido"""
    for pedido in st.session_state.pedidos:
        if pedido.get('id') == pedido_id:
            pedido['status'] = novo_status
            return True
    return False

# Interface
def mostrar_formulario_adicionar():
    st.header("📝 Adicionar Novo Pedido")
    
    with st.form("form_adicionar", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            tecnico = st.text_input("👤 Técnico *")
            peca = st.text_input("🔧 Peça *")
            modelo = st.text_input("💻 Modelo")
            
        with col2:
            numero_serie = st.text_input("🔢 Número de Série")
            ordem_servico = st.text_input("📄 OS")
            observacoes = st.text_area("📝 Observações")
        
        # Upload de foto simplificado
        uploaded_file = st.file_uploader("📸 Foto (opcional)", type=['jpg', 'png', 'jpeg'])
        
        submitted = st.form_submit_button("➕ Adicionar Pedido")
        
        if submitted:
            if tecnico.strip() and peca.strip():
                dados = {
                    'tecnico': tecnico.strip(),
                    'peca': peca.strip(),
                    'modelo': modelo.strip(),
                    'numero_serie': numero_serie.strip(),
                    'ordem_servico': ordem_servico.strip(),
                    'observacoes': observacoes.strip(),
                    'status': 'Pendente',
                    'data_criacao': datetime_now_str()
                }
                
                pedido_id = salvar_pedido(dados)
                st.success(f"✅ Pedido {pedido_id} salvo!")
                st.rerun()
            else:
                st.error("⚠️ Preencha Técnico e Peça!")

def mostrar_lista_pedidos():
    st.header("📋 Lista de Pedidos")
    
    pedidos = listar_pedidos()
    
    if not pedidos:
        st.info("📭 Nenhum pedido cadastrado")
        return
    
    # Estatísticas
    total = len(pedidos)
    pendentes = sum(1 for p in pedidos if p.get('status') == 'Pendente')
    solicitados = sum(1 for p in pedidos if p.get('status') == 'Solicitado')
    entregues = sum(1 for p in pedidos if p.get('status') == 'Entregue')
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", total)
    col2.metric("🔴 Pendentes", pendentes)
    col3.metric("🟡 Solicitados", solicitados)
    col4.metric("🟢 Entregues", entregues)
    
    st.markdown("---")
    
    # Lista de pedidos
    for pedido in pedidos:
        status = pedido.get('status', 'Pendente')
        emoji = STATUS_EMOJIS.get(status, '⚪')
        
        with st.expander(f"{emoji} {pedido.get('tecnico')} - {pedido.get('peca')} - ID: {pedido.get('id')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Data:** {pedido.get('data_criacao')}")
                st.write(f"**Técnico:** {pedido.get('tecnico')}")
                st.write(f"**Peça:** {pedido.get('peca')}")
            with col2:
                st.write(f"**Modelo:** {pedido.get('modelo')}")
                st.write(f"**Nº Série:** {pedido.get('numero_serie')}")
                st.write(f"**Status:** {emoji} {status}")
            
            if pedido.get('observacoes'):
                st.write("**Observações:**")
                st.info(pedido.get('observacoes'))

def mostrar_atualizar_status():
    st.header("🔄 Atualizar Status")
    
    # Autenticação
    if not st.session_state.autorizado:
        with st.form("auth"):
            senha = st.text_input("🔒 Senha", type="password")
            if st.form_submit_button("Entrar"):
                if senha == SENHA_AUTORIZACAO:
                    st.session_state.autorizado = True
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta")
        return
    
    # Formulário de atualização
    with st.form("update_form"):
        pedido_id = st.text_input("🔎 ID do Pedido")
        novo_status = st.selectbox("🔄 Novo Status", STATUS_PEDIDO)
        
        if st.form_submit_button("📥 Atualizar"):
            if pedido_id:
                if atualizar_status(pedido_id, novo_status):
                    st.success(f"✅ Status atualizado!")
                    st.rerun()
                else:
                    st.error("❌ Pedido não encontrado")
            else:
                st.error("⚠️ Digite o ID do pedido")

# App principal
def main():
    st.title("📦 Controle de Pedidos")
    
    # Sidebar
    st.sidebar.title("Navegação")
    menu = st.sidebar.selectbox(
        "Menu",
        ["Adicionar Pedido", "Visualizar Pedidos", "Atualizar Status"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Modo GitHub Online**\n\nDados salvos temporariamente.")
    
    # Navegação
    if menu == "Adicionar Pedido":
        mostrar_formulario_adicionar()
    elif menu == "Visualizar Pedidos":
        mostrar_lista_pedidos()
    elif menu == "Atualizar Status":
        mostrar_atualizar_status()

if __name__ == "__main__":
    main()