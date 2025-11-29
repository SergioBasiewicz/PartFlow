# app.py - VERSÃO COM FIREBASE REAL
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
# CONFIGURAÇÕES GERAIS (MESMA INTERFACE)
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
            st.error("❌ Credenciais do Firebase não encontradas nos Secrets")
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

# Inicializar Firebase uma vez
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
# CONFIGURAÇÃO DA PÁGINA (MESMA INTERFACE)
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
# FUNÇÕES UTILITÁRIAS (MESMA INTERFACE)
# =============================================================================
def processar_upload_foto(uploaded_file, pedido_id):
    """Processa upload, converte e gera data_url para envio ao backend."""
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
        img_b64 = base64.b64encode(img_bytes).decode()

        foto_info = {
            "nome": getattr(uploaded_file, "name", "foto.jpg"),
            "tamanho": getattr(uploaded_file, "size", len(img_bytes)),
            "tipo": getattr(uploaded_file, "type", "image/jpeg"),
            "dimensoes": image.size,
            "data_url": f"data:image/jpeg;base64,{img_b64}",
            "pedido_id": pedido_id,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
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

def obter_emoji_status(status):
    if not status:
        return "⚪"
    status_limpo = str(status).replace(":", "").strip()
    return STATUS_EMOJIS.get(status_limpo, "⚪")

def parse_data_pedido(row: dict):
    """Converte o campo de data para datetime para ordenar"""
    from datetime import datetime as _dt

    valor = row.get("data_criacao") or row.get("data") or row.get("timestamp") or ""

    if not valor:
        return _dt.min

    formatos = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    ]

    for fmt in formatos:
        try:
            return _dt.strptime(str(valor), fmt)
        except Exception:
            pass

    return _dt.min

# =============================================================================
# FUNÇÕES DO FIREBASE (REAIS)
# =============================================================================
def datetime_now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def dataurl_para_bytes(data_url: str):
    """Converte data:image/...;base64,... para bytes."""
    try:
        header, b64 = data_url.split(",", 1)
        return base64.b64decode(b64)
    except Exception:
        return None

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
                st.success(f"✅ Status do pedido {pedido_id} atualizado para {formatar_status(novo_status)}")
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
                        st.success(f"✅ Status do pedido {pedido_id} atualizado para {formatar_status(novo_status)}")
                        return True
            st.error("❌ Pedido não encontrado")
            return False
            
    except Exception as e:
        st.error(f"❌ Erro ao atualizar status: {e}")
        return False

def firebase_status():
    """Retorna status do Firebase"""
    return {
        "USE_FIREBASE": USE_FIREBASE,
        "BUCKET_NAME": BUCKET_NAME if USE_FIREBASE else None,
        "STATUS": "CONECTADO" if USE_FIREBASE else "DESCONECTADO"
    }

# =============================================================================
# TELAS DO SISTEMA (MESMA INTERFACE)
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
            type=["jpg", "jpeg", "png", "gif"],
            help="Formatos suportados: JPG, JPEG, PNG, GIF (máx. 5MB)",
        )

        foto_info = None
        if uploaded_file is not None:
            foto_info = processar_upload_foto(uploaded_file, "preview")
            if foto_info:
                st.success("📸 Foto anexada com sucesso!")

        submitted = st.form_submit_button("➕ Adicionar Pedido")

        if submitted:
            if validar_formulario(tecnico, peca):
                uploaded_bytes = uploaded_file.getvalue() if uploaded_file is not None else None
                nome_foto = foto_info.get("nome") if foto_info else None
                
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
                    time.sleep(1.5)
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
                st.markdown(
                    f"<div style='background: rgba(255,255,255,0.02); "
                    f"padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.03);'>"
                    f"{pedido['observacoes']}</div>",
                    unsafe_allow_html=True,
                )

            if pedido.get("tem_foto") and pedido.get("foto_url"):
                try:
                    st.image(pedido["foto_url"], use_container_width=True)
                except Exception:
                    st.warning("Não foi possível carregar a imagem deste pedido.")

    # Estatísticas gerais
    try:
        total_pedidos = len(pedidos)
        pendentes = sum(1 for p in pedidos if "pend" in str(p["status"]).lower())
        solicitados = sum(1 for p in pedidos if "solic" in str(p["status"]).lower())
        entregues = sum(1 for p in pedidos if "entreg" in str(p["status"]).lower())

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
    except Exception as e:
        st.error(f"Erro ao calcular estatísticas: {e}")

def mostrar_pagina_atualizar_status():
    st.header("🔄 Atualizar Status do Pedido")
    if not st.session_state.get("autorizado", False):
        mostrar_formulario_autenticacao()
    else:
        mostrar_formulario_atualizacao_status()

def mostrar_formulario_autenticacao():
    with st.form("form_autenticacao"):
        senha = st.text_input("🔒 Digite a senha de autorização", type="password")
        submitted = st.form_submit_button("✅ Validar Senha")
        if submitted:
            if senha == SENHA_AUTORIZACAO:
                st.session_state.autorizado = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta. Tente novamente.")

def mostrar_formulario_atualizacao_status():
    with st.container():
        st.subheader("Atualizar Status do Pedido")

        with st.form("form_atualizacao_status"):
            valor_busca = st.text_input("🔎 ID ou Número de Série *")

            opcoes_status = [f"{STATUS_EMOJIS[s]} {s}" for s in STATUS_PEDIDO]
            novo_status_formatado = st.selectbox("🔄 Novo Status", opcoes_status)
            novo_status = novo_status_formatado.split(" ", 1)[1]

            submitted = st.form_submit_button("📥 Atualizar Status")

            if submitted:
                if not valor_busca.strip():
                    st.warning("⚠️ Por favor, informe o ID ou o Número de Série.")
                    return

                pedidos = listar_pedidos()
                if not pedidos:
                    st.error("Nenhum pedido encontrado para atualizar.")
                    return

                valor_busca_norm = valor_busca.strip().lower()

                pedido_encontrado = None
                for pedido in pedidos:
                    rid = str(pedido.get("id", "")).strip().lower()
                    rnum = str(pedido.get("numero_serie", "")).strip().lower()

                    if valor_busca_norm == rid or valor_busca_norm == rnum:
                        pedido_encontrado = pedido
                        break

                if not pedido_encontrado:
                    st.error("❌ Nenhum pedido encontrado com esse ID ou Número de Série.")
                    return

                pedido_id_real = str(pedido_encontrado.get("id") or "")
                if not pedido_id_real:
                    st.error("❌ Pedido encontrado, mas sem ID válido.")
                    return

                if atualizar_status(pedido_id_real, novo_status):
                    time.sleep(1)
                    st.rerun()

    # Pré-visualização na sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Pré-visualização dos Pedidos")

    pedidos_sidebar = listar_pedidos()

    if not pedidos_sidebar:
        st.sidebar.info("📭 Nenhum pedido encontrado.")
        return

    for p in pedidos_sidebar:
        status = p.get("status", "Pendente")
        emoji = STATUS_EMOJIS.get(status, "⚪")
        pid = p.get("id", "")
        tecnico = p.get("tecnico", "-")
        numero_serie = p.get("numero_serie", "-")

        label = f"{emoji} Pedido — Tecnico: {tecnico} — Nº de Serie: {numero_serie} — ID: {pid}"

        with st.sidebar.expander(label, expanded=False):
            st.write(f"**📅 Data:** {p.get('data_criacao', '-')}")
            st.write(f"**👤 Técnico:** {tecnico}")
            st.write(f"**🔧 Peça:** {p.get('peca', '-')}")
            st.write(f"**💻 Modelo:** {p.get('modelo', '-')}")
            st.write(f"**🔢 Nº Série:** {numero_serie}")
            st.write(f"**📄 OS:** {p.get('ordem_servico', '-')}")
            st.write(f"**🆔 ID:** {pid}")
            st.write(f"**📌 Status:** {formatar_status(status)}")

            obs = p.get("observacoes", "")
            if obs:
                st.write("**📝 Observações:**")
                st.info(obs)

            if p.get("tem_foto") and p.get("foto_url"):
                try:
                    st.image(p["foto_url"], use_container_width=True)
                except Exception:
                    st.warning("Não foi possível carregar a imagem deste pedido.")

# =============================================================================
# MAIN (MESMA INTERFACE)
# =============================================================================
def inicializar_session_state():
    if "autorizado" not in st.session_state:
        st.session_state.autorizado = False
    if "pedidos" not in st.session_state:
        st.session_state.pedidos = []

def main():
    configurar_pagina()
    inicializar_session_state()

    st.title("📦 Controle de Pedidos de Peças Usadas")

    # Status do backend
    fb_info = firebase_status()
    backend_nome = "Firebase" if fb_info.get("USE_FIREBASE") else "Local (Session State)"
    st.sidebar.markdown(f"**Backend:** {backend_nome}")
    if fb_info.get("BUCKET_NAME"):
        st.sidebar.markdown(f"**Bucket:** {fb_info['BUCKET_NAME']}")

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
