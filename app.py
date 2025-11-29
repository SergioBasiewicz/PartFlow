# app.py - VERSÃO FINAL COM FIREBASE
import streamlit as st
import time
import uuid
import base64
from datetime import datetime
from PIL import Image
import io
import os
import json

# =============================================================================
# CONFIGURAÇÕES GERAIS
# =============================================================================
SENHA_AUTORIZACAO = "admin123"

STATUS_PEDIDO = ["Pendente", "Solicitado", "Entregue"]
STATUS_EMOJIS = {
    "Pendente": "🔴",
    "Solicitado": "🟡",
    "Entregue": "🟢",
}

# =============================================================================
# CONFIGURAÇÃO DO FIREBASE
# =============================================================================
def inicializar_firebase():
    """Inicializa Firebase com credenciais do Streamlit Secrets"""
    try:
        # Verificar se secrets existem
        if ('GOOGLE_APPLICATION_CREDENTIALS_JSON' not in st.secrets or 
            'FIREBASE_BUCKET' not in st.secrets):
            st.error("❌ Credenciais do Firebase não encontradas")
            return None, None, None

        # Obter credenciais
        creds_json = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_JSON']
        bucket_name = st.secrets['FIREBASE_BUCKET']
        
        # Se for string, converter para dict
        if isinstance(creds_json, str):
            creds_dict = json.loads(creds_json)
        else:
            creds_dict = creds_json

        # Importar e configurar Firebase
        from google.cloud import firestore, storage
        from google.oauth2 import service_account

        # Criar credenciais
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        
        # Inicializar clientes
        firestore_client = firestore.Client(credentials=credentials, project=creds_dict['project_id'])
        storage_client = storage.Client(credentials=credentials, project=creds_dict['project_id'])
        
        st.success("✅ Firebase conectado com sucesso!")
        return firestore_client, storage_client, bucket_name
        
    except Exception as e:
        st.error(f"❌ Erro ao conectar com Firebase: {e}")
        return None, None, None

# Inicializar Firebase
if 'firebase_inicializado' not in st.session_state:
    firestore_client, storage_client, BUCKET_NAME = inicializar_firebase()
    st.session_state.firestore_client = firestore_client
    st.session_state.storage_client = storage_client
    st.session_state.bucket_name = BUCKET_NAME
    st.session_state.firebase_inicializado = True
else:
    firestore_client = st.session_state.firestore_client
    storage_client = st.session_state.storage_client
    BUCKET_NAME = st.session_state.bucket_name

USE_FIREBASE = firestore_client is not None and storage_client is not None

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================
def configurar_pagina():
    st.set_page_config(
        page_title="Controle de Pedidos",
        page_icon="📦",
        layout="wide",
    )

    css = """
    <style>
    html, body, .main {
        background-color: #0d1113;
        color: #e6eef8;
        font-family: "Inter", "Segoe UI", Arial, sans-serif;
    }

    .card {
        background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
        border-radius: 10px;
        padding: 18px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.6);
        border: 1px solid rgba(255,255,255,0.03);
        margin-bottom: 20px;
    }

    a {
        color: #9fd3ff;
        text-decoration: none;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================
def processar_upload_foto(uploaded_file, pedido_id):
    """Processa upload de foto"""
    if uploaded_file is None:
        return None

    try:
        image = Image.open(uploaded_file)

        # Normalizar modo da imagem
        if image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Reduzir tamanho
        max_size = (800, 800)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        img_bytes = buffered.getvalue()

        foto_info = {
            "nome": uploaded_file.name,
            "bytes": img_bytes,
            "dimensoes": image.size,
        }
        return foto_info
    except Exception as e:
        st.error(f"Erro ao processar imagem: {e}")
        return None

def validar_formulario(tecnico, peca):
    if not tecnico or not tecnico.strip():
        st.error("⚠️ O campo Técnico é obrigatório!")
        return False
    if not peca or not peca.strip():
        st.error("⚠️ O campo Peça é obrigatório!")
        return False
    return True

def formatar_status(status):
    if not status:
        return "⚪ N/A"
    status_limpo = str(status).replace(":", "").strip()
    emoji = STATUS_EMOJIS.get(status_limpo, "⚪")
    return f"{emoji} {status_limpo}"

# =============================================================================
# FUNÇÕES DO FIREBASE
# =============================================================================
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def upload_foto_firebase(bytes_data: bytes, nome_arquivo: str):
    """Faz upload da foto para Firebase Storage"""
    if not USE_FIREBASE or not storage_client:
        return None
        
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_name = f"fotos_pedidos/{uuid.uuid4().hex}_{nome_arquivo}"
        blob = bucket.blob(blob_name)
        
        blob.upload_from_string(bytes_data, content_type='image/jpeg')
        blob.make_public()
        
        return blob.public_url
    except Exception as e:
        st.error(f"❌ Erro ao fazer upload da foto: {e}")
        return None

def salvar_pedido(dados: dict, foto_bytes: bytes = None, nome_foto: str = None):
    """Salva pedido no Firestore"""
    try:
        pedido_id = str(uuid.uuid4())
        foto_url = None
        
        # Upload da foto se existir
        if foto_bytes and nome_foto:
            foto_url = upload_foto_firebase(foto_bytes, nome_foto)
        
        # Preparar dados completos
        pedido_completo = {
            **dados,
            "id": pedido_id,
            "data_criacao": datetime_now_str(),
            "foto_url": foto_url,
            "tem_foto": foto_url is not None
        }
        
        # Salvar no Firebase
        if USE_FIREBASE:
            doc_ref = firestore_client.collection("pedidos").document(pedido_id)
            doc_ref.set(pedido_completo)
            st.success(f"✅ Pedido {pedido_id} salvo no Firebase!")
            return pedido_id
        else:
            # Fallback para session state
            if 'pedidos' not in st.session_state:
                st.session_state.pedidos = []
            st.session_state.pedidos.append(pedido_completo)
            st.success(f"✅ Pedido {pedido_id} salvo localmente!")
            return pedido_id
            
    except Exception as e:
        st.error(f"❌ Erro ao salvar pedido: {e}")
        return None

def listar_pedidos():
    """Busca pedidos do Firestore"""
    try:
        if USE_FIREBASE:
            from google.cloud.firestore import Query
            
            # Buscar todos os pedidos ordenados por data
            docs = firestore_client.collection("pedidos").order_by(
                "data_criacao", direction=Query.DESCENDING
            ).stream()
            
            pedidos = []
            for doc in docs:
                pedido_data = doc.to_dict()
                pedido_data["id"] = doc.id
                pedidos.append(pedido_data)
            
            return pedidos
        else:
            # Fallback para session state
            if 'pedidos' not in st.session_state:
                return []
            return st.session_state.pedidos
            
    except Exception as e:
        st.error(f"❌ Erro ao buscar pedidos: {e}")
        return []

def atualizar_status(pedido_id: str, novo_status: str):
    """Atualiza status no Firestore"""
    try:
        if USE_FIREBASE:
            doc_ref = firestore_client.collection("pedidos").document(pedido_id)
            doc = doc_ref.get()
            
            if doc.exists:
                doc_ref.update({"status": novo_status})
                st.success(f"✅ Status do pedido {pedido_id} atualizado para {novo_status}")
                return True
            else:
                st.error("❌ Pedido não encontrado no Firebase")
                return False
        else:
            # Fallback para session state
            if 'pedidos' in st.session_state:
                for pedido in st.session_state.pedidos:
                    if pedido.get("id") == pedido_id:
                        pedido["status"] = novo_status
                        st.success(f"✅ Status do pedido {pedido_id} atualizado para {novo_status}")
                        return True
            st.error("❌ Pedido não encontrado")
            return False
            
    except Exception as e:
        st.error(f"❌ Erro ao atualizar status: {e}")
        return False

# =============================================================================
# TELAS DO SISTEMA
# =============================================================================
def mostrar_formulario_adicionar_pedido():
    st.header("📝 Adicionar Novo Pedido")

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

        st.markdown("---")
        st.subheader("📸 Anexar Foto (Opcional)")

        uploaded_file = st.file_uploader(
            "Selecione uma foto do equipamento/peça",
            type=["jpg", "jpeg", "png"],
            help="Formatos suportados: JPG, JPEG, PNG"
        )

        foto_info = None
        if uploaded_file is not None:
            foto_info = processar_upload_foto(uploaded_file, "preview")
            if foto_info:
                st.success("📸 Foto processada com sucesso!")
                st.image(uploaded_file, use_container_width=True)

        submitted = st.form_submit_button("➕ Adicionar Pedido")

        if submitted:
            if validar_formulario(tecnico, peca):
                uploaded_bytes = foto_info["bytes"] if foto_info else None
                nome_foto = foto_info["nome"] if foto_info else None
                
                dados = {
                    "tecnico": tecnico,
                    "peca": peca,
                    "modelo": modelo_equipamento or "",
                    "numero_serie": numero_serie or "",
                    "ordem_servico": ordem_servico or "",
                    "observacoes": observacoes or "",
                    "status": "Pendente",
                }
                
                pedido_id = salvar_pedido(dados, uploaded_bytes, nome_foto)
                if pedido_id:
                    time.sleep(2)
                    st.rerun()

def mostrar_lista_pedidos():
    st.header("📋 Lista de Pedidos")

    pedidos = listar_pedidos()

    if not pedidos:
        st.info("📭 Nenhum pedido cadastrado no momento.")
        return

    st.markdown("### 📦 Pedidos cadastrados")
    st.write("")

    for pedido in pedidos:
        status_label = pedido.get("status") or "Pendente"
        emoji_status = STATUS_EMOJIS.get(status_label, "⚪")
        titulo = (
            f"{emoji_status} Pedido — Tecnico: {pedido['tecnico'] or '-'} "
            f"— Nº de Série: {pedido['numero_serie'] or '-'} — Id: {pedido['id']}"
        )

        with st.expander(titulo, expanded=False):
            st.write(f"**Data:** {pedido['data_criacao'] or '-'}")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Técnico:** {pedido['tecnico'] or '-'}")
                st.markdown(f"**Peça:** {pedido['peca'] or '-'}")
                st.markdown(f"**Modelo:** {pedido['modelo'] or '-'}")
                st.markdown(f"**ID:** {pedido['id'] or '-'}")

            with col2:
                st.markdown(f"**Nº Série:** {pedido['numero_serie'] or '-'}")
                st.markdown(f"**OS:** {pedido['ordem_servico'] or '-'}")
                st.markdown(f"**Status:** {formatar_status(status_label)}")

            if pedido["observacoes"]:
                st.markdown("**Observações:**")
                st.info(pedido["observacoes"])

            if pedido.get("tem_foto") and pedido.get("foto_url"):
                try:
                    st.image(pedido["foto_url"], use_container_width=True, caption="Foto do equipamento")
                except Exception:
                    st.warning("Não foi possível carregar a imagem deste pedido.")

    # Estatísticas
    total_pedidos = len(pedidos)
    pendentes = sum(1 for p in pedidos if p.get("status") == "Pendente")
    solicitados = sum(1 for p in pedidos if p.get("status") == "Solicitado")
    entregues = sum(1 for p in pedidos if p.get("status") == "Entregue")

    st.markdown("### 📊 Resumo dos pedidos")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total de Pedidos", total_pedidos)
    with c2:
        st.metric("🔴 Pendentes", pendentes)
    with c3:
        st.metric("🟡 Solicitados", solicitados)
    with c4:
        taxa = (entregues / total_pedidos * 100) if total_pedidos > 0 else 0
        st.metric("🟢 Entregues", f"{entregues} ({taxa:.1f}%)")

def mostrar_pagina_atualizar_status():
    st.header("🔄 Atualizar Status do Pedido")
    
    if not st.session_state.get("autorizado", False):
        with st.form("form_autenticacao"):
            senha = st.text_input("🔒 Digite a senha de autorização", type="password")
            submitted = st.form_submit_button("✅ Validar Senha")
            if submitted:
                if senha == SENHA_AUTORIZACAO:
                    st.session_state.autorizado = True
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta. Tente novamente.")
        return
    
    # Formulário de atualização
    with st.form("form_atualizacao_status"):
        st.subheader("Atualizar Status do Pedido")
        
        pedido_id = st.text_input("🔎 ID do Pedido *")
        
        opcoes_status = [f"{STATUS_EMOJIS[s]} {s}" for s in STATUS_PEDIDO]
        novo_status_formatado = st.selectbox("🔄 Novo Status", opcoes_status)
        novo_status = novo_status_formatado.split(" ", 1)[1]

        submitted = st.form_submit_button("📥 Atualizar Status")
        
        if submitted:
            if not pedido_id.strip():
                st.warning("⚠️ Por favor, informe o ID do pedido.")
            else:
                if atualizar_status(pedido_id.strip(), novo_status):
                    time.sleep(2)
                    st.rerun()

# =============================================================================
# MAIN
# =============================================================================
def inicializar_session_state():
    if "autorizado" not in st.session_state:
        st.session_state.autorizado = False

def main():
    configurar_pagina()
    inicializar_session_state()

    st.title("📦 Controle de Pedidos de Peças Usadas")

    # Status do sistema
    st.sidebar.title("🔧 Status do Sistema")
    st.sidebar.write(f"**Firebase:** {'✅ CONECTADO' if USE_FIREBASE else '❌ LOCAL'}")
    if USE_FIREBASE:
        st.sidebar.write(f"**Bucket:** {BUCKET_NAME}")
        st.sidebar.success("🎉 Dados salvos na nuvem!")

    menu = st.sidebar.selectbox(
        "📂 Menu",
        ["Adicionar Pedido", "Visualizar Pedidos", "Atualizar Status"],
    )

    if menu == "Adicionar Pedido":
        mostrar_formulario_adicionar_pedido()
    elif menu == "Visualizar Pedidos":
        mostrar_lista_pedidos()
    elif menu == "Atualizar Status":
        mostrar_pagina_atualizar_status()

if __name__ == "__main__":
    main()
