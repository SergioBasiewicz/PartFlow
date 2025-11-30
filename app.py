# app_test.py - VERIFICA CONFIGURAÇÃO
import streamlit as st
import json

st.set_page_config(page_title="Teste Firebase", layout="centered")

st.title("🔧 TESTE DE CONFIGURAÇÃO FIREBASE")

# Verificar Secrets
st.header("1. ✅ Secrets Configurados")
try:
    if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
        st.success("✅ GOOGLE_APPLICATION_CREDENTIALS_JSON: OK")
        creds = json.loads(st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON'])
        st.write(f"**Project ID:** {creds.get('project_id')}")
    else:
        st.error("❌ GOOGLE_APPLICATION_CREDENTIALS_JSON: FALTANDO")
        
    if 'FIREBASE_BUCKET' in st.secrets:
        st.success(f"✅ FIREBASE_BUCKET: {st.secrets['FIREBASE_BUCKET']}")
    else:
        st.error("❌ FIREBASE_BUCKET: FALTANDO")
except Exception as e:
    st.error(f"Erro nos secrets: {e}")

# Testar Conexão Firebase
st.header("2. 🔗 Teste de Conexão Firebase")
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
    
    # Testar Firestore
    try:
        firestore_client = firestore.Client(credentials=credentials, project=creds_dict['project_id'])
        st.success("✅ Firestore: CONECTADO")
    except Exception as e:
        st.error(f"❌ Firestore: {e}")
        st.info("💡 Configure Firestore Database no console")
    
    # Testar Storage
    try:
        storage_client = storage.Client(credentials=credentials, project=creds_dict['project_id'])
        bucket = storage_client.bucket(bucket_name)
        
        if bucket.exists():
            st.success("✅ Storage: CONFIGURADO E PRONTO!")
        else:
            st.error(f"❌ Storage: Bucket '{bucket_name}' não existe")
            st.info("""
            **🚨 CONFIGURE O STORAGE AGORA:**
            
            1. **Acesse:** https://console.firebase.google.com/
            2. **Projeto:** partflow-81c43
            3. **Menu lateral → Storage**
            4. **Clique em "Começar"**
            5. **Configure:**
               - Localização: **southamerica-east1**
               - Segurança: **Modo de teste**
            6. **Clique em "Concluir"**
            
            ⏱️ **Aguarde 1-2 minutos após configurar**
            """)
            
    except Exception as e:
        st.error(f"❌ Storage: {e}")
        
except Exception as e:
    st.error(f"❌ Erro geral: {e}")

st.markdown("---")
st.info("**📝 Depois de configurar o Storage, atualize esta página para testar novamente!**")
