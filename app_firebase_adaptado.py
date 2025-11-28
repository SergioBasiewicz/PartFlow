# app_firebase_adaptado.py
# Controle de Pedidos de Peças Usadas + Firebase

import streamlit as st
import time
import uuid
import base64
from datetime import datetime
from PIL import Image
import io
import os

# Funções do Firebase – mantenha seu firebase_funcoes.py configurado
from firebase_funcoes import (
    salvar_pedido,
    listar_pedidos,
    atualizar_status,
    dataurl_para_bytes,
    firebase_status,
)

# --------------------------------------------------------------------
# Configurações gerais
# --------------------------------------------------------------------
SENHA_AUTORIZACAO = "admin123"

STATUS_PEDIDO = ["Pendente", "Solicitado", "Entregue"]
STATUS_EMOJIS = {
    "Pendente": "🔴",
    "Solicitado": "🟡",
    "Entregue": "🟢",
}

EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": os.environ.get("SENDER_EMAIL", "seu_email@exemplo.com"),
    "sender_password": os.environ.get("EMAIL_PASSWORD", "SUA_SENHA"),
    "recipient_emails": [os.environ.get("RECIPIENT_EMAIL", "seu_email@exemplo.com")],
}

# --------------------------------------------------------------------
# Aparência geral
# --------------------------------------------------------------------
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


# --------------------------------------------------------------------
# Utilitários de imagem
# --------------------------------------------------------------------
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


# --------------------------------------------------------------------
# Helpers gerais
# --------------------------------------------------------------------
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
    """
    Converte o campo de data (data_criacao / data / timestamp) para datetime
    para permitir ordenar do mais novo para o mais antigo.
    """
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


# --------------------------------------------------------------------
# Firebase: adicionar / listar / atualizar
# --------------------------------------------------------------------
def adicionar_novo_pedido(
    numero_serie,
    peca,
    tecnico,
    modelo_equipamento,
    ordem_servico,
    observacoes,
    foto_info=None,
    uploaded_bytes=None,
):
    try:
        dados = {
            "tecnico": tecnico,
            "peca": peca,
            "modelo": modelo_equipamento or "",
            "numero_serie": numero_serie or "",
            "ordem_servico": ordem_servico or "",
            "observacoes": observacoes or "",
            "status": "Pendente",
            "data_criacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }

        foto_bytes = None
        nome_foto = None

        if uploaded_bytes is not None:
            foto_bytes = uploaded_bytes
            nome_foto = foto_info.get("nome") if foto_info else f"{uuid.uuid4()}.jpg"
        elif foto_info and "data_url" in foto_info:
            foto_bytes = dataurl_para_bytes(foto_info["data_url"])
            nome_foto = foto_info.get("nome") if foto_info else f"{uuid.uuid4()}.jpg"

        resultado = salvar_pedido(dados, foto_bytes=foto_bytes, nome_foto=nome_foto)

        # salvar_pedido pode retornar dict ou string (id)
        if isinstance(resultado, dict):
            pedido_id = resultado.get("id")
        else:
            pedido_id = resultado

        st.success(f"✅ Pedido {pedido_id} adicionado com sucesso!")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao adicionar pedido: {e}")
        return False


def obter_todos_pedidos():
    try:
        pedidos = listar_pedidos()
        if not pedidos:
            return []
        import pandas as pd

        df = pd.DataFrame(pedidos)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar pedidos do Firebase: {e}")
        return []


def atualizar_status_pedido(pedido_id, novo_status):
    try:
        ok = atualizar_status(pedido_id, novo_status)
        if ok:
            st.success(f"✅ Status do pedido {pedido_id} atualizado para {formatar_status(novo_status)}")
            return True
        else:
            st.error("❌ Pedido não encontrado")
            return False
    except Exception as e:
        st.error(f"❌ Erro ao atualizar status: {e}")
        return False


# --------------------------------------------------------------------
# Tela: Adicionar Pedido
# --------------------------------------------------------------------
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
                if adicionar_novo_pedido(
                    numero_serie,
                    peca,
                    tecnico,
                    modelo_equipamento,
                    ordem_servico,
                    observacoes,
                    foto_info,
                    uploaded_bytes,
                ):
                    time.sleep(1.5)
                    st.rerun()


# --------------------------------------------------------------------
# Tela: Visualizar Pedidos (Expanders)
# --------------------------------------------------------------------
def mostrar_lista_pedidos():
    st.header("📋 Lista de Pedidos")

    df = obter_todos_pedidos()
    import pandas as pd

    if df is None or (isinstance(df, list) and not df):
        st.info("📭 Nenhum pedido cadastrado no momento.")
        return

    if isinstance(df, list):
        try:
            df = pd.DataFrame(df)
        except Exception:
            st.error("Erro ao converter lista de pedidos em DataFrame.")
            st.write(df)
            return

    if isinstance(df, pd.DataFrame) and df.empty:
        st.info("📭 Nenhum pedido cadastrado no momento.")
        return

    registros = df.to_dict(orient="records")

    # Ordenar do mais novo para o mais antigo
    registros = sorted(registros, key=parse_data_pedido, reverse=True)

    st.markdown("### 📦 Pedidos cadastrados")
    st.write("")

    pedidos = []
    for row in registros:
        pedidos.append(
            {
                "id": row.get("id", row.get("ID", "")) or row.get("id", ""),
                "data": row.get("data_criacao", row.get("data", "")) or row.get("timestamp", ""),
                "tecnico": row.get("tecnico", ""),
                "peca": row.get("peca", ""),
                "modelo": row.get("modelo", ""),
                "numero_serie": row.get("numero_serie", ""),
                "os": row.get("ordem_servico", row.get("os", "")),
                "observacoes": row.get("observacoes", ""),
                "status": row.get("status", ""),
                "tem_foto": str(row.get("tem_foto", "")).lower() in ("true", "sim", "yes", "1"),
                "foto_url": row.get("foto_url", ""),
            }
        )

    for pedido in pedidos:
        status_label = pedido["status"] or "Pendente"
        emoji_status = STATUS_EMOJIS.get(status_label, "⚪")
        titulo = (
            f"{emoji_status} Pedido — Tecnico: {pedido['tecnico'] or '-'} "
            f"— Nº de Série: {pedido['numero_serie'] or '-'} — Id: {pedido['id']}"
        )

        with st.expander(titulo, expanded=False):
            st.write(f"**Data:** {pedido['data'] or '-'}")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Técnico:** {pedido['tecnico'] or '-'}")
                st.markdown(f"**Peça:** {pedido['peca'] or '-'}")
                st.markdown(f"**Modelo:** {pedido['modelo'] or '-'}")
                st.markdown(f"**ID:** {pedido['id'] or '-'}")

            with col2:
                st.markdown(f"**Nº Série:** {pedido['numero_serie'] or '-'}")
                st.markdown(f"**OS:** {pedido['os'] or '-'}")
                st.markdown(f"**Status:** {formatar_status(status_label)}")

            if pedido["observacoes"]:
                st.markdown("**Observações:**")
                st.markdown(
                    f"<div style='background: rgba(255,255,255,0.02); "
                    f"padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.03);'>"
                    f"{pedido['observacoes']}</div>",
                    unsafe_allow_html=True,
                )

            if pedido["tem_foto"] and pedido["foto_url"]:
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


# --------------------------------------------------------------------
# Tela: Atualizar Status (com pré-visualização na sidebar)
# --------------------------------------------------------------------
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
    import pandas as pd

    with st.container():
        st.subheader("Atualizar Status do Pedido")

        df = obter_todos_pedidos()

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

                if df is None or (isinstance(df, list) and not df):
                    st.error("Nenhum pedido encontrado para atualizar.")
                    return

                if isinstance(df, list):
                    try:
                        df = pd.DataFrame(df)
                    except Exception:
                        st.error("Erro ao converter pedidos para DataFrame.")
                        return

                if isinstance(df, pd.DataFrame) and df.empty:
                    st.error("Nenhum pedido encontrado para atualizar.")
                    return

                registros = df.to_dict(orient="records")
                registros = sorted(registros, key=parse_data_pedido, reverse=True)

                valor_busca_norm = valor_busca.strip().lower()

                pedido_encontrado = None
                for row in registros:
                    rid = str(row.get("id", "")).strip().lower()
                    rnum = str(row.get("numero_serie", "")).strip().lower()

                    if valor_busca_norm == rid or valor_busca_norm == rnum:
                        pedido_encontrado = row
                        break

                if not pedido_encontrado:
                    st.error("❌ Nenhum pedido encontrado com esse ID ou Número de Série.")
                    return

                pedido_id_real = str(pedido_encontrado.get("id") or "")
                if not pedido_id_real:
                    st.error("❌ Pedido encontrado, mas sem ID válido.")
                    return

                if atualizar_status_pedido(pedido_id_real, novo_status):
                    st.success(f"Status do pedido {pedido_id_real} atualizado com sucesso!")
                    time.sleep(1)
                    st.rerun()

    # Pré-visualização na sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Pré-visualização dos Pedidos")

    df_sidebar = obter_todos_pedidos()

    if df_sidebar is None:
        st.sidebar.info("📭 Nenhum pedido encontrado.")
        return

    if isinstance(df_sidebar, list):
        if not df_sidebar:
            st.sidebar.info("📭 Nenhum pedido encontrado.")
            return
        try:
            df_sidebar = pd.DataFrame(df_sidebar)
        except Exception:
            st.sidebar.error("Erro ao converter pedidos para visualização.")
            return

    if isinstance(df_sidebar, pd.DataFrame) and df_sidebar.empty:
        st.sidebar.info("📭 Nenhum pedido encontrado.")
        return

    registros_sidebar = df_sidebar.to_dict(orient="records")
    registros_sidebar = sorted(registros_sidebar, key=parse_data_pedido, reverse=True)

    for p in registros_sidebar:
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


# --------------------------------------------------------------------
# Session state + main
# --------------------------------------------------------------------
def inicializar_session_state():
    if "autorizado" not in st.session_state:
        st.session_state.autorizado = False
    if "fotos_pedidos" not in st.session_state:
        st.session_state.fotos_pedidos = {}


def main():
    configurar_pagina()
    inicializar_session_state()

    st.title("📦 Controle de Pedidos de Peças Usadas")

    # 🔍 Debug do backend (mostra se está usando Firebase ou local)
    fb_info = firebase_status()
    backend_nome = "Firebase" if fb_info.get("USE_FIREBASE") else "Local (arquivo)"
    st.sidebar.markdown(f"**Backend:** {backend_nome}")
    if fb_info.get("BUCKET_NAME"):
        st.sidebar.caption(f"Bucket: {fb_info['BUCKET_NAME']}")

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
