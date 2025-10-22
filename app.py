import streamlit as st
import requests
import os
from dotenv import load_dotenv

API_BASE_URL = "http://127.0.0.1:8000" 
load_dotenv()

try:
    API_KEY_HEADER = { "X-Api-Key": os.getenv("API_BACKEND_KEY") }
    ADMIN_PASSWORD_LOCAL = os.getenv("ADMIN_PASSWORD")
    if not API_KEY_HEADER["X-Api-Key"] or not ADMIN_PASSWORD_LOCAL:
        raise KeyError()
except (KeyError, FileNotFoundError):
    st.error("ERRO: Verifique se o seu arquivo .env contém as chaves ADMIN_PASSWORD e API_BACKEND_KEY.")
    st.stop()


def chat_page():
    st.header("Converse com seus documentos 💬")
    
    try:
        response = requests.get(f"{API_BASE_URL}/list-courses/", headers=API_KEY_HEADER)
        response.raise_for_status()
        available_courses = response.json()
        
        if not available_courses:
            st.warning("⚠️ Nenhum curso disponível ainda. Entre em contato com o administrador.")
            return
        
        if "selected_course" not in st.session_state:
            st.session_state.selected_course = available_courses[0]
        
        selected_course = st.selectbox(
            "📚 Selecione seu curso:",
            options=available_courses,
            index=available_courses.index(st.session_state.selected_course) if st.session_state.selected_course in available_courses else 0,
            key="course_selector"
        )
        
        if selected_course != st.session_state.selected_course:
            st.session_state.selected_course = selected_course
            st.session_state.chat_history = []
            st.rerun()
        
        st.info(f"🎓 Conversando com documentos do curso: **{selected_course}**")
        st.markdown("---")
        
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar cursos. Verifique se o servidor está rodando. Detalhes: {e}")
        return
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if message.get("source_documents"):
                unique_sources = set()
                for doc in message["source_documents"]:
                    unique_sources.add(doc['source'])
                
                with st.expander("Ver fontes"):
                    for source_name in sorted(list(unique_sources)):
                        st.markdown(f"📄 `{source_name}`") 

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
                        json={
                            "question": user_question, 
                            "course": st.session_state.selected_course,  
                            "chat_history": st.session_state.chat_history
                        }
                    )
                    response.raise_for_status()
                    
                    response_data = response.json()
                    answer = response_data.get("answer")
                    source_documents = response_data.get("source_documents")

                    st.markdown(answer)
                    
                    if source_documents:
                        unique_sources = set()
                        for doc in source_documents:
                            unique_sources.add(doc['source'])
                        
                        with st.expander("Ver fontes da resposta"):
                            for source_name in sorted(list(unique_sources)):
                                st.markdown(f"📄 `{source_name}`") 
                    
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": answer,
                        "source_documents": source_documents 
                    })

                except requests.exceptions.RequestException as e:
                    st.error(f"Erro de comunicação com a API: {e}")
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")


def admin_page():
    st.header("Área do Administrador 🔑")

    if st.session_state.get('authenticated', False):
        st.success("Acesso liberado!")
        st.markdown("---")

        try:
            response = requests.get(f"{API_BASE_URL}/list-courses/", headers=API_KEY_HEADER)
            response.raise_for_status()
            existing_courses = response.json()
        except:
            existing_courses = []

        st.subheader("📚 Documentos por Curso")
        try:
            response = requests.get(f"{API_BASE_URL}/list-documents/", headers=API_KEY_HEADER)
            response.raise_for_status()
            documents_by_course = response.json()
            
            if documents_by_course:
                for course_name, doc_list in sorted(documents_by_course.items()):
                    with st.expander(f"🎓 {course_name} ({len(doc_list)} documentos)"):
                        for doc_name in doc_list:
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.info(f"📄 {doc_name}")
                            with col2:
                                if st.button("Remover", key=f"del_{course_name}_{doc_name}", type="primary"):
                                    with st.spinner(f"Removendo {doc_name}..."):
                                        delete_response = requests.post(
                                            f"{API_BASE_URL}/delete-document/",
                                            headers=API_KEY_HEADER,
                                            json={
                                                "filename": doc_name,
                                                "course": course_name  
                                            }
                                        )
                                        if delete_response.status_code == 200:
                                            st.success(f"'{doc_name}' removido com sucesso!")
                                            st.rerun()
                                        else:
                                            st.error(f"Falha ao remover: {delete_response.json().get('detail')}")
            else:
                st.info("Nenhum documento foi processado ainda.")
        except requests.exceptions.RequestException as e:
            st.error(f"Não foi possível buscar documentos. Verifique se a API está rodando. Detalhes: {e}")
        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")

        st.markdown("---")
        st.subheader("➕ Adicionar Novos Documentos")
        
        col1, col2 = st.columns(2)
        with col1:
            course_option = st.radio(
                "Escolha uma opção:",
                ["Selecionar curso existente", "Criar novo curso"],
                key="course_option"
            )
        
        with col2:
            if course_option == "Selecionar curso existente":
                if existing_courses:
                    selected_course = st.selectbox("Curso:", existing_courses)
                else:
                    st.warning("Nenhum curso existe ainda. Crie um novo curso.")
                    selected_course = None
            else:
                selected_course = st.text_input("Nome do novo curso:")
        
        document_name = st.text_input("Nome do Documento (como ele aparecerá na lista):")
        uploaded_file = st.file_uploader("Carregue o arquivo correspondente (PDF, DOCX, TXT):", type=["pdf", "docx", "txt"])

        if st.button("Processar e Adicionar Documento"):
            if uploaded_file and document_name and selected_course:
                with st.spinner("Enviando e processando documento..."):
                    try:
                        files_and_data = {
                            'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type),
                            'doc_name': (None, document_name),
                            'course': (None, selected_course)  
                        }
                        response = requests.post(
                            f"{API_BASE_URL}/upload-and-process/", 
                            headers=API_KEY_HEADER, 
                            files=files_and_data
                        )
                        if response.status_code == 200:
                             st.success(response.json().get("message", "Documento adicionado!"))
                             st.rerun()
                        else:
                            st.error(f"Falha no processamento: {response.json().get('detail')}")
                    except Exception as e:
                        st.error(f"Ocorreu um erro inesperado: {e}")
            else:
                st.warning("Por favor, preencha todos os campos e carregue um arquivo.")

    else:
        st.warning("Você precisa de acesso de administrador para ver esta página.")
        
        password = st.text_input("Digite a senha de administrador", type="password")

        if st.button("Entrar"):
            if password == ADMIN_PASSWORD_LOCAL:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")


def main():
    st.set_page_config(page_title="Chat com Documentos por Curso", page_icon="🎓")
    
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    selected_page = st.sidebar.radio("Navegação", ["Chat com Documentos", "Administrador"])
    
    if st.session_state['authenticated'] and selected_page == "Administrador":
        if st.sidebar.button("Sair (Logout)"):
            st.session_state['authenticated'] = False
            st.rerun()

    if selected_page == "Chat com Documentos":
        chat_page()
    elif selected_page == "Administrador":
        admin_page()

if __name__ == '__main__':
    main()