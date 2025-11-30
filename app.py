# app_final.py - VERSÃO FINAL APÓS CONFIGURAR STORAGE
import streamlit as st
import time
import uuid
from datetime import datetime
from PIL import Image
import io
import json

# Configurações
SENHA_AUTORIZACAO = "admin123"
STATUS_PEDIDO = ["Pendente", "Solicitado", "Entregue"]
STATUS_EMOJIS = {"Pendente": "🔴", "Solicitado": "🟡", "Entregue": "🟢"}

# Inicializar Firebase
@st.cache_resource
def inicializar_firebase():
    try:
        from google.cloud import firestore, storage
        from google.oauth2 import service_account
        
        creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
        bucket_name = st.secrets['FIREBASE_BUCKET']
        
        if isinstance(creds_json, str):
            creds_dict = json.loads(creds_json)
        else:
            creds_dict = creds_json
            
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        firestore_client = firestore.Client(credentials=credentials, project=creds_dict['project_id'])
        storage_client = storage.Client(credentials=credentials, project=creds_dict['project_id'])
        
        # Verificar Storage
        bucket = storage_client.bucket(bucket_name)
        if not bucket.exists():
            st.error("❌ Storage não configurado. Configure no Firebase Console.")
            st.stop()
            
        st.success("🎉 Firebase configurado com sucesso!")
        return firestore_client, storage_client, bucket_name
        
    except Exception as e:
        st.error(f"❌ Erro Firebase: {e}")
        st.stop()

# Inicializar
firestore_client, storage_client, BUCKET_NAME = inicializar_firebase()

# App Principal
st.set_page_config(page_title="Controle de Pedidos", page_icon="📦", layout="wide")
st.title("📦 Controle de Pedidos - Firebase")
st.success("🚀 Conectado ao Firebase!")

def main():
    st.sidebar.title("Sistema")
    st.sidebar.success("✅ Firebase CONECTADO")
    
    menu = st.sidebar.selectbox("Menu", ["Adicionar", "Visualizar", "Atualizar Status"])
    
    if menu == "Adicionar":
        with st.form("form"):
            tecnico = st.text_input("👤 Técnico")
            peca = st.text_input("🔧 Peça")
            if st.form_submit_button("Salvar"):
                if tecnico and peca:
                    pedido_id = str(uuid.uuid4())
                    dados = {
                        "tecnico": tecnico, "peca": peca, 
                        "status": "Pendente", "data_criacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }
                    firestore_client.collection("pedidos").document(pedido_id).set(dados)
                    st.success(f"✅ Pedido {pedido_id} salvo no Firebase!")
    
    elif menu == "Visualizar":
        docs = firestore_client.collection("pedidos").stream()
        pedidos = [{"id": doc.id, **doc.to_dict()} for doc in docs]
        
        if pedidos:
            for pedido in pedidos:
                with st.expander(f"{pedido['tecnico']} - {pedido['peca']}"):
                    st.write(f"ID: {pedido['id']}")
                    st.write(f"Status: {pedido['status']}")
        else:
            st.info("Nenhum pedido cadastrado")

if __name__ == "__main__":
    main()
