# app.py - VERSÃO DEFINITIVA FIREBASE
import streamlit as st
import time
import uuid
from datetime import datetime
from PIL import Image
import io
import json

# =============================================================================
# CONFIGURAÇÕES GERAIS
# =============================================================================
SENHA_AUTORIZACAO = "admin123"
STATUS_PEDIDO = ["Pendente", "Solicitado", "Entregue"]
STATUS_EMOJIS = {"Pendente": "🔴", "Solicitado": "🟡", "Entregue": "🟢"}

# =============================================================================
# INICIALIZAÇÃO FIREBASE (OBRIGATÓRIA)
# =============================================================================
@st.cache_resource
def inicializar_firebase():
    try:
        if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' not in st.secrets:
            st.error("❌ Credenciais Firebase não encontradas")
            st.stop()
            
        creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
        bucket_name = st.secrets['FIREBASE_BUCKET']
        
        if isinstance(creds_json, str):
            creds_dict = json.loads(creds_json)
        else:
            creds_dict = creds_json

        from google.cloud import firestore, storage
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        firestore_client = firestore.Client(credentials=credentials, project=creds_dict['project_id'])
        storage_client = storage.Client(credentials=credentials, project=creds_dict['project_id'])
        
        # Testar conexão
        bucket = storage_client.bucket(bucket_name)
        if not bucket.exists():
            st.error("❌ Storage não configurado. Configure no Firebase Console.")
            st.stop()
            
        st.success("✅ Firebase configurado com sucesso!")
        return firestore_client, storage_client, bucket_name
        
    except Exception as e:
        st.error(f"❌ Erro Firebase: {e}")
        st.stop()

# Inicializar Firebase
firestore_client, storage_client, BUCKET_NAME = inicializar_firebase()

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================
st.set_page_config(page_title="Controle de Pedidos", page_icon="📦", layout="wide")

st.markdown("""
<style>
.main { background-color: #0d1113; color: #e6eef8; font-family: "Inter", sans-serif; }
.card { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); 
        border-radius: 10px; padding: 18px; box-shadow: 0 8px 24px rgba(0,0,0,0.6); 
        border: 1px solid rgba(255,255,255,0.03); margin-bottom: 20px; }
a { color: #9fd3ff; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# FUNÇÕES PRINCIPAIS
# =============================================================================
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def processar_upload_foto(uploaded_file):
    if not uploaded_file: return None
    try:
        image = Image.open(uploaded_file)
        if image.mode != "RGB": image = image.convert("RGB")
        image.thumbnail((800, 800), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        return {"nome": uploaded_file.name, "bytes": buffered.getvalue()}
    except Exception as e:
        st.error(f"Erro ao processar imagem: {e}")
        return None

def salvar_pedido(dados, foto_bytes=None, nome_foto=None):
    try:
        pedido_id = str(uuid.uuid4())
        foto_url = None
        
        if foto_bytes and nome_foto:
            bucket = storage_client.bucket(BUCKET_NAME)
            blob_name = f"fotos_pedidos/{uuid.uuid4().hex}_{nome_foto}"
            blob = bucket.blob(blob_name)
            blob.upload_from_string(foto_bytes, content_type='image/jpeg')
            blob.make_public()
            foto_url = blob.public_url
        
        pedido_completo = {
            **dados, "id": pedido_id, "data_criacao": datetime_now_str(),
            "foto_url": foto_url, "tem_foto": foto_url is not None
        }
        
        doc_ref = firestore_client.collection("pedidos").document(pedido_id)
        doc_ref.set(pedido_completo)
        st.success(f"✅ Pedido {pedido_id} salvo no Firebase!")
        return pedido_id
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {e}")
        return None

def listar_pedidos():
    try:
        from google.cloud.firestore import Query
        docs = firestore_client.collection("pedidos").order_by("data_criacao", direction=Query.DESCENDING).stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        st.error(f"❌ Erro ao buscar pedidos: {e}")
        return []

def atualizar_status(pedido_id, novo_status):
    try:
        doc_ref = firestore_client.collection("pedidos").document(pedido_id)
        if doc_ref.get().exists:
            doc_ref.update({"status": novo_status})
            st.success(f"✅ Status atualizado para {novo_status}")
            return True
        st.error("❌ Pedido não encontrado")
        return False
    except Exception as e:
        st.error(f"❌ Erro ao atualizar: {e}")
        return False

# =============================================================================
# INTERFACE
# =============================================================================
def main():
    st.title("📦 Controle de Pedidos - Firebase")
    st.success("🚀 Conectado ao Firebase - Dados na nuvem!")

    st.sidebar.title("🔧 Sistema")
    st.sidebar.success("✅ Firebase CONECTADO")
    st.sidebar.write(f"**Bucket:** {BUCKET_NAME}")

    menu = st.sidebar.selectbox("📂 Menu", ["Adicionar Pedido", "Visualizar Pedidos", "Atualizar Status"])

    if menu == "Adicionar Pedido":
        st.header("📝 Adicionar Pedido")
        with st.form("form_adicionar"):
            col1, col2 = st.columns(2)
            with col1:
                tecnico = st.text_input("👤 Técnico *")
                peca = st.text_input("🔧 Peça *")
                modelo = st.text_input("💻 Modelo")
            with col2:
                numero_serie = st.text_input("🔢 Nº Série")
                ordem_servico = st.text_input("📄 OS")
                observacoes = st.text_area("📝 Observações")
            
            uploaded_file = st.file_uploader("📸 Foto (opcional)", type=["jpg", "jpeg", "png"])
            foto_info = processar_upload_foto(uploaded_file) if uploaded_file else None
            
            if st.form_submit_button("➕ Adicionar"):
                if tecnico and peca:
                    dados = {
                        "tecnico": tecnico, "peca": peca, "modelo": modelo or "",
                        "numero_serie": numero_serie or "", "ordem_servico": ordem_servico or "",
                        "observacoes": observacoes or "", "status": "Pendente"
                    }
                    if salvar_pedido(dados, foto_info["bytes"] if foto_info else None, 
                                   foto_info["nome"] if foto_info else None):
                        time.sleep(2)
                        st.rerun()
                else:
                    st.error("⚠️ Preencha Técnico e Peça!")

    elif menu == "Visualizar Pedidos":
        st.header("📋 Lista de Pedidos")
        pedidos = listar_pedidos()
        if not pedidos:
            st.info("📭 Nenhum pedido no Firebase")
            return
        
        for pedido in pedidos:
            status = pedido.get("status", "Pendente")
            emoji = STATUS_EMOJIS.get(status, "⚪")
            with st.expander(f"{emoji} {pedido['tecnico']} - {pedido['peca']} - ID: {pedido['id']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Data:** {pedido.get('data_criacao', '-')}")
                    st.write(f"**Técnico:** {pedido['tecnico']}")
                    st.write(f"**Peça:** {pedido['peca']}")
                with col2:
                    st.write(f"**Modelo:** {pedido.get('modelo', '-')}")
                    st.write(f"**Nº Série:** {pedido.get('numero_serie', '-')}")
                    st.write(f"**Status:** {emoji} {status}")
                
                if pedido.get("observacoes"):
                    st.info(f"**Observações:** {pedido['observacoes']}")
                
                if pedido.get("tem_foto") and pedido.get("foto_url"):
                    st.image(pedido["foto_url"], use_container_width=True)

    elif menu == "Atualizar Status":
        st.header("🔄 Atualizar Status")
        if not st.session_state.get("autorizado"):
            with st.form("auth"):
                if st.form_submit_button("🔒 Acessar Área Admin"):
                    st.session_state.autorizado = True
                    st.rerun()
            return
        
        with st.form("update"):
            pedido_id = st.text_input("🔎 ID do Pedido")
            novo_status = st.selectbox("🔄 Novo Status", STATUS_PEDIDO)
            if st.form_submit_button("📥 Atualizar") and pedido_id:
                atualizar_status(pedido_id.strip(), novo_status)

if __name__ == "__main__":
    if "autorizado" not in st.session_state:
        st.session_state.autorizado = False
    main()
