# app.py - VERSÃO TESTE SECRETS
import streamlit as st
import json

st.set_page_config(page_title="Teste Secrets", layout="wide")

st.title("🔧 TESTE SECRETS FIREBASE")

# Debug detalhado
st.header("Debug dos Secrets")

try:
    # Listar TODAS as chaves disponíveis
    all_secrets = dict(st.secrets)
    st.write("### Todas as chaves e valores:")
    st.json(all_secrets)
    
    st.write("### Verificação específica:")
    
    # Verificar cada chave individualmente
    if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in st.secrets:
        st.success("✅ GOOGLE_APPLICATION_CREDENTIALS_JSON: ENCONTRADO")
        creds = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
        st.write("Tipo:", type(creds))
        
        # Tentar parsear o JSON
        if isinstance(creds, str):
            try:
                creds_dict = json.loads(creds)
                st.success("✅ JSON parseado com sucesso!")
                st.write("Project ID:", creds_dict.get('project_id', 'NÃO ENCONTRADO'))
            except json.JSONDecodeError as e:
                st.error(f"❌ Erro ao parsear JSON: {e}")
    else:
        st.error("❌ GOOGLE_APPLICATION_CREDENTIALS_JSON: NÃO ENCONTRADO")
        
    if 'FIREBASE_BUCKET' in st.secrets:
        bucket = st.secrets['FIREBASE_BUCKET']
        st.success(f"✅ FIREBASE_BUCKET: {bucket}")
    else:
        st.error("❌ FIREBASE_BUCKET: NÃO ENCONTRADO")
        
except Exception as e:
    st.error(f"Erro geral: {e}")

st.markdown("---")
st.info("💡 **Instruções:** Se as chaves não aparecerem acima, verifique se no Streamlit Cloud Secrets você colocou APENAS as duas linhas (sem [default])")
