# app_simple_test.py
import streamlit as st
import json

st.set_page_config(page_title="Teste Storage", layout="centered")
st.title("🧪 TESTE STORAGE FIREBASE")

try:
    from google.cloud import storage
    from google.oauth2 import service_account
    
    # Configuração
    creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
    bucket_name = st.secrets['FIREBASE_BUCKET']
    
    if isinstance(creds_json, str):
        creds_dict = json.loads(creds_json)
    else:
        creds_dict = creds_json
        
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    storage_client = storage.Client(credentials=credentials, project=creds_dict['project_id'])
    
    # Testar Storage
    st.info("🔍 Verificando Storage...")
    bucket = storage_client.bucket(bucket_name)
    
    if bucket.exists():
        st.success("🎉 STORAGE CONFIGURADO COM SUCESSO!")
        st.balloons()
        
        # Testar upload
        try:
            blob = bucket.blob("teste.txt")
            blob.upload_from_string("Teste de conexão - " + st.secrets['FIREBASE_BUCKET'])
            st.success("✅ Upload de teste realizado!")
            
            # Listar buckets disponíveis
            st.write("**Buckets disponíveis no projeto:**")
            buckets = list(storage_client.list_buckets())
            for b in buckets:
                st.write(f"- {b.name}")
                
        except Exception as e:
            st.error(f"❌ Erro no upload: {e}")
            
    else:
        st.error(f"""
        ❌ **STORAGE AINDA NÃO CONFIGURADO**
        
        **Bucket esperado:** `{bucket_name}`
        
        **🚨 PASSO A PASSO PARA CONFIGURAR:**
        
        1. **Acesse:** https://console.firebase.google.com/
        2. **Clique no projeto:** partflow-81c43
        3. **No menu lateral → Storage**
        4. **Clique em "Começar"** 
        5. **Siga o assistente:**
           - Segurança: **Modo de teste**
           - Localização: **southamerica-east1**
        6. **Clique em "Concluir"**
        7. **Aguarde 1-2 minutos**
        8. **Atualize esta página**
        
        ⚠️ **Verifique se não há nenhum pop-up ou tela pendente no Firebase Console**
        """)
        
except Exception as e:
    st.error(f"❌ Erro: {e}")
