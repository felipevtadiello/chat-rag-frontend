import streamlit as st
import requests

API_BASE_URL = "https://sua-api.onrender.com"

try:
    API_KEY_HEADER = {
        "X-Api-Key": st.secrets["API_BACKEND_KEY"]
    }
except (KeyError, FileNotFoundError):
    st.error("A chave da API do Backend (API_BACKEND_KEY) não foi configurada nos segredos.")
    st.stop()


def chat_page():
    st.header("Converse com seus documentos 💬")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_question := st.chat_input("Faça sua pergunta"):
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/ask/",
                        headers=API_KEY_HEADER,
                        json={"question": user_question, "chat_history": st.session_state.chat_history}
                    )
                    response.raise_for_status()

                    answer = response.json().get("answer")
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})

                except requests.exceptions.RequestException as e:
                    st.error(f"Erro de comunicação com a API: {e.response.json()}")
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")


def admin_page():
    st.header("Área do Administrador 🔑")
    password = st.text_input("Digite a senha de administrador", type="password")

    if password != st.secrets.get("ADMIN_PASSWORD"):
        if password:
            st.warning("Senha incorreta.")
        return

    st.success("Acesso liberado!")
    st.markdown("---")

    st.subheader("Documentos na Base de Conhecimento")
    try:
        response = requests.get(f"{API_BASE_URL}/list-documents/", headers=API_KEY_HEADER)
        response.raise_for_status()
        processed_docs = response.json()

        if processed_docs:
            for doc in processed_docs:
                st.info(f"📄 {doc}")
        else:
            st.info("Nenhum documento foi processado ainda.")

    except requests.exceptions.RequestException as e:
        st.error(f"Não foi possível buscar la lista de documentos: {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")

    st.markdown("---")
    st.subheader("Adicionar Novos Documentos")
    uploaded_file = st.file_uploader("Carregue um novo PDF para adicionar", type="pdf")

    if st.button("Processar e Adicionar Documento"):
        if uploaded_file:
            with st.spinner("Enviando e processando documento..."):
                try:
                    files_to_send = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

                    response = requests.post(
                        f"{API_BASE_URL}/upload-and-process/",
                        headers=API_KEY_HEADER,
                        files=files_to_send
                    )

                    if response.status_code == 200:
                        st.success(response.json().get("message", "Documento adicionado! A lista será atualizada."))
                        st.rerun()
                    else:
                        st.error(f"Falha no processamento: {response.json().get('detail')}")

                except Exception as e:
                    st.error(f"Ocorreu um erro inesperado: {e}")
        else:
            st.warning("Por favor, carregue um arquivo PDF.")


def main():
    st.set_page_config(page_title="Chat com Documentos", page_icon="💬")

    if "ADMIN_PASSWORD" not in st.secrets or "API_BACKEND_KEY" not in st.secrets:
        st.error("Configure as chaves ADMIN_PASSWORD e API_BACKEND_KEY nos segredos do seu app.")
        st.stop()

    selected_page = st.sidebar.radio("Navegação", ["Chat com Documentos", "Administrador"])

    if selected_page == "Chat com Documentos":
        chat_page()
    elif selected_page == "Administrador":
        admin_page()


if __name__ == '__main__':
    main()