import streamlit as st

import io
import os
import re
import json
import uuid
import base64
import random
import time
import pandas as pd
from PIL import Image
from datetime import datetime

from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, HttpRequest
from googleapiclient.errors import HttpError

st.set_page_config(
    page_title="Falling Walls Summit '24",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed")

#GOOGLE SERVICES    
def get_google_services():
    try:
        # Obtener la cadena codificada de la variable de entorno
        encoded_sa = os.getenv('GOOGLE_SERVICE_ACCOUNT')
        if not encoded_sa:
            raise ValueError("La variable de entorno GOOGLE_SERVICE_ACCOUNT no está configurada")

        # Decodificar la cadena
        sa_json = base64.b64decode(encoded_sa).decode('utf-8')

        # Crear un diccionario a partir de la cadena JSON
        sa_dict = json.loads(sa_json)

        # Crear las credenciales
        credentials = service_account.Credentials.from_service_account_info(
            sa_dict,
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
        )

        drive_service = build('drive', 'v3', credentials=credentials)
        sheets_service = build('sheets', 'v4', credentials=credentials)

        return drive_service, sheets_service
    except Exception as e:
        st.error(f"Error al obtener los servicios de Google: {str(e)}")
        return None, None

def download_file_from_google_drive(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return fh.getvalue()
    except Exception as e:
        st.error(f"Error al descargar el archivo: {str(e)}")
        return None

def extract_folder_id(url):
    match = re.search(r'folders/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    return None

def find_images_folder_and_csv_id(service, parent_folder_name):
    try:
        results = service.files().list(
            q=f"name='{parent_folder_name}' and mimeType='application/vnd.google-apps.folder'",
            fields="nextPageToken, files(id)"
        ).execute()
        parent_folders = results.get('files', [])
        if not parent_folders:
            st.error(f"No se encontró la carpeta principal '{parent_folder_name}'.")
            return None, None
        parent_folder_id = parent_folders[0]['id']
        results = service.files().list(
            q=f"'{parent_folder_id}' in parents",
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        items = results.get('files', [])
        images_folder_id = None
        csv_file_id = None
        for item in items:
            if item['name'] == 'IMAGES' and item['mimeType'] == 'application/vnd.google-apps.folder':
                images_folder_id = item['id']
            elif item['name'].endswith('.csv') and item['mimeType'] == 'text/csv':
                csv_file_id = item['id']
        if not images_folder_id:
            st.error("No se encontró la carpeta 'IMAGES'.")
        if not csv_file_id:
            st.error("No se encontró el archivo CSV.")
        return images_folder_id, csv_file_id
    except Exception as e:
        st.error(f"Error al buscar la carpeta 'IMAGES' y el CSV: {str(e)}")
        return None, None

#TOOLS
def generate_user_id():
    return str(uuid.uuid4())  # Unique user ID based on UUID

def display_pdf(pdf_bytes):
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')  # Encode the bytes directly
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="800" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def display_pdf_from_file(pdf_path):
    """Muestra un PDF desde un archivo local"""
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error al cargar el PDF: {str(e)}")

@st.cache_data()
def list_images_in_folder(_service, folder_id):
    try:
        results = _service.files().list(
            q=f"'{folder_id}' in parents and mimeType contains 'image/'",
            fields="nextPageToken, files(id, name)"
        ).execute()
        items = results.get('files', [])
        return items
    except Exception as e:
        st.error(f"Error al listar las imágenes: {str(e)}")
        return []

@st.cache_data()
def get_images_for_prompt(_drive_service, prompt):
    images = {}
    
    # Folder IDs for "neutral" and "older"
    neutral_folder_id = "1z8zZJQqMZDFtJG1hx7mosAt_5DlXuZU8"
    older_folder_id = "1-zseBhQMP-KeK8EoLIt6M45zTApHOGzc"

    # Adjust the prompt name for file search
    prompt_formatted = prompt.replace(" ", "_")  # Replace spaces with underscores for filenames

    # Define expected filenames for neutral and older images
    neutral_filename = f"a_person_{prompt_formatted}.jpg"
    older_filename = f"an_older_person_{prompt_formatted}.jpg"
    
    #st.write(f"Looking for images for prompt: {prompt_formatted}")

    # Search for images in the "neutral" folder
    neutral_image_query = f"'{neutral_folder_id}' in parents"
    neutral_results = _drive_service.files().list(q=neutral_image_query, fields="files(id, name)").execute()
    neutral_files = neutral_results.get('files', [])
    
    # Debug: Print all neutral files found
    # st.write("Neutral images found in folder:")
    # for file in neutral_files:
    #     st.write(f"- {file['name']}")

    # Find the specific file matching the prompt for neutral
    neutral_file = next((file for file in neutral_files if file['name'] == neutral_filename), None)

    # Search for images in the "older" folder
    older_image_query = f"'{older_folder_id}' in parents"
    older_results = _drive_service.files().list(q=older_image_query, fields="files(id, name)").execute()
    older_files = older_results.get('files', [])
    
    # Debug: Print all older files found
    # st.write("Older images found in folder:")
    #   for file in older_files:
    #     st.write(f"- {file['name']}")

    # Find the specific file matching the prompt for older
    older_file = next((file for file in older_files if file['name'] == older_filename), None)

    # Check if the images are found
    if neutral_file:
        images['neutral'] = neutral_file  # Take the first image
    if older_file:
        images['older'] = older_file  # Take the first image

    # Ensure both images exist, otherwise return an error
    if 'neutral' not in images or 'older' not in images:
        st.error(f"Error: No se encontraron imágenes para el prompt '{prompt_formatted}'. Asegúrate de que existan en Google Drive.")
        return {}

    return images

############### SENSE DRIVE ###############
# Función auxiliar para convertir una imagen a base64 (útil para preparar las imágenes)
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()
# Función auxiliar para guardar una imagen en base64
def save_image_base64(image_path, output_file):
    encoded = image_to_base64(image_path)
    with open(output_file, 'w') as f:
        f.write(encoded)

class LocalImageHandler:
    def __init__(self):
        self.base_folder = Path("IMAGES")
        self.prompts = [
            "traveling",
            "eating",
            "planning shopping",
            "taking a break",
            "participating in sports events",
            "receiving personal care services",
            "using computers",
            "in the living room",
            "at work",
            "in a job fair",
            "handling home care tasks",
            "managing the household",
            "moving to a new location",
            "in a study group",
            "in a party",
            "going for walks",
            "heating the dwelling"
        ]
        
    def get_image_path(self, prompt, image_type):
        """
        Obtiene la ruta de la imagen basada en el prompt y tipo
        image_type puede ser 'neutral' o 'older'
        """
        prefix = "a_person_" if image_type == 'neutral' else "an_older_person_"
        # Convertir el prompt a formato de nombre de archivo
        formatted_prompt = prompt.replace(" ", "_")
        filename = f"{prefix}{formatted_prompt}.jpg"  # o .jpg según el formato de tus imágenes
        return self.base_folder / image_type / filename

    def get_images_for_prompt(self, prompt):
        """Obtiene las imágenes neutral y older para un prompt específico"""
        return {
            'neutral': {
                'path': self.get_image_path(prompt, 'neutral'),
                'name': f"Person {prompt}"
            },
            'older': {
                'path': self.get_image_path(prompt, 'older'),
                'name': f"Older person {prompt}"
            }
        }

    def get_random_prompt(self):
        """Obtiene un prompt aleatorio de la lista"""
        return random.choice(self.prompts)

prompts = [
    "traveling",
    "eating",
    "planning shopping",
    "taking a break",
    "participating in sports events",
    "receiving personal care services",
    "using computers",
    "in the living room",
    "at work",
    "in a job fair",
    "handling home care tasks",
    "managing the household",
    "moving to a new location",
    "in a study group",
    "in a party",
    "going for walks",
    "heating the dwelling"]

def initialize_session_state():
    #"""Inicializa todas las variables del estado de la sesión"""
    if 'page' not in st.session_state:
        st.session_state.page = 'intro'
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'image_responses' not in st.session_state:
        st.session_state.image_responses = {}
    if 'image_handler' not in st.session_state:
        st.session_state.image_handler = LocalImageHandler()
    if 'current_prompt' not in st.session_state:
        st.session_state.current_prompt = st.session_state.image_handler.get_random_prompt()

def main():
    # Inicializar el estado de la sesión
    initialize_session_state()

    # Inicializar rutas
    intro_image = Path("IMAGES/Imagen_intro.png")
    pdf_path = Path("TERMS/TERMS.pdf")

    drive_service, sheets_service = get_google_services()

    if not drive_service or not sheets_service:
        st.error("No se pudieron obtener los servicios de Google.")
        return

    drive_url = "https://drive.google.com/drive/u/0/folders/1GwfHfrsEH7jGisVdeUdGJOPG7TlbUyl8"
    parent_folder_name = "10_14_FALLING_WALLS"
    spreadsheet_id = "1kkpKzDOkwJ58vgvp0IIAhS-yOSJxId8VJ4Bjxj7MmJk"

    # Extraer el ID de la carpeta principal de Google Drive
    parent_folder_id = extract_folder_id(drive_url)

    # Inicializar estado de sesión
    if 'page' not in st.session_state:
        st.session_state.page = 'intro'

    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'user_id' not in st.session_state:
        st.session_state.user_id = ''
    if 'random_images' not in st.session_state:
        st.session_state.random_images = []
    if 'image_responses' not in st.session_state:
        st.session_state.image_responses = {}
    if 'all_files' not in st.session_state:
        st.session_state.all_files = []

    st.write(f"Estado actual de la página: {st.session_state.page}")

    # Cargar archivos desde Google Drive (solo CSV o PDF, no imágenes) Si el folder ID de Google Drive se ha encontrado
    if parent_folder_id:
        # Buscar la carpeta de imágenes y el archivo CSV
        images_folder_id, csv_file_id = find_images_folder_and_csv_id(drive_service, parent_folder_name)
        if images_folder_id and csv_file_id:
            current_prompt = random.choice(prompts)  # Selecciona un prompt aleatorio
            images = get_images_for_prompt(drive_service, current_prompt)  # Implementa esta función

            if 'neutral' in images and 'older' in images:
                st.session_state.random_images = [images['neutral'], images['older']]
            else:
                st.error("No se encontraron imágenes adecuadas para el prompt.")
            
            if not st.session_state.all_files: # Crucial: Get all files, including the PDF
                results = drive_service.files().list(
                    q=f"'{parent_folder_id}' in parents",  # Query for files in the parent folder
                    fields="nextPageToken, files(id, name, mimeType)"
                ).execute()
                st.session_state.all_files = results.get('files', [])                
        else:
            st.error("No se pudieron encontrar las imágenes o el archivo CSV.")  
    else:
        st.error("Could not obtain the parent folder ID.")

    if st.session_state.page == 'intro':
        st.write("Estado de página: intro")  # Mensaje de depuración

        st.markdown("<h1 style='text-align: center;'>AGEAI Project</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>How age is depicted in Generative AI?</h2>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'></h2>", unsafe_allow_html=True)

        col1, col2 = st.columns([2, 2]) 

        with col1:
            st.write("In this experience, you'll explore AI-generated images using prompts in Midjourney. Your task is to identify how age is represented in relation to emotions, roles and autonomy, by selecting different tags in each image and by describing the differences between the two age groups depicted.")
            st.write("At the end, the collective insights from all participants will be revealed.")
            st.write("")
            st.write("""
                        **Terms and Conditions:**
                        * This study is part of the Ageism AI project funded by VolksWagen Foundation.
                        * Data is anonymous and will be used for scientific studies.
                        * If you start, you accept to participate in the study (no personal information will be collected).
                        """)

        with col2:
            #Cargar y mostrar la imagen
            # intro_image_id = None
            # for file in st.session_state.all_files:
            #     if file['name'] == "Imagen_intro.png":
            #         intro_image_id = file['id']
            #         break

            # if intro_image_id:
            #     intro_image_bytes = download_file_from_google_drive(drive_service, intro_image_id)
            #     if intro_image_bytes:
            #         st.image(intro_image_bytes, width=300, use_column_width=False)  # Ajustar la imagen completamente a la columna

            if intro_image.exists():
                try:
                    st.image(str(intro_image), width=300, use_column_width=False)
                except Exception as e:
                    st.error(f"Error al cargar la imagen: {str(e)}")
            else:
                st.error("Imagen de introducción no encontrada")

        # Mostrar el archivo PDF de los términos y condiciones
        # terms_pdf_id = None
        # for file in st.session_state.all_files:
        #     if file['name'] == "TERMS.pdf":
        #         terms_pdf_id = file['id']
        #         break

        # if terms_pdf_id:
        #     pdf_bytes = download_file_from_google_drive(drive_service, terms_pdf_id)
        #     if pdf_bytes:
        #         with st.expander("View the Terms and Conditions PDF below:", expanded=False):
        #             display_pdf(pdf_bytes)  # Función para mostrar el PDF
        if pdf_path.exists():
            with st.expander("View the Terms and Conditions PDF below:", expanded=False):
                display_pdf_from_file(pdf_path)
        else:
            st.error("Archivo PDF de términos y condiciones no encontrado")

        # Checkbox y botón para aceptar los términos
        agree = st.checkbox("I agree to the terms and conditions")
        if agree:
            if st.button("Start"):
                st.session_state.page = 'prompt1'
                st.rerun()

    elif st.session_state.page == 'prompt1':
        # Si current_prompt no está establecido, selecciona un prompt aleatorio
        if 'current_prompt' not in st.session_state:
            st.session_state.current_prompt = random.choice(prompts) 

        current_prompt = st.session_state.current_prompt  # Usar el prompt guardado

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"<h2 style='text-align: center;'>STEP {st.session_state.current_step} of 3</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center;'>How an older person and a person {current_prompt.replace('_', ' ')} are depicted in Midjourney?</h3>", unsafe_allow_html=True)
            
            st.markdown("""
                <style>
                div.stButton > button {
                    display: block;
                    margin: 0 auto;
                    font-size: 20px;
                    padding: 10px 40px;
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                }
                </style>
                """, unsafe_allow_html=True)

            if st.button("Go!"):
                st.session_state.page = 'questionnaire'
                st.rerun()

#QUESTIONNAIRE
    elif st.session_state.page == 'questionnaire':
        col1, col2, col3 = st.columns([2, 2, 1])
        
        # Obtener imágenes para el prompt actual
        current_prompt = st.session_state.current_prompt   
        #images = get_images_for_prompt(drive_service, current_prompt)
        images = st.session_state.image_handler.get_images_for_prompt(current_prompt)

        #if 'neutral' in images and 'older' in images:
        for i, (key, image_data) in enumerate(images.items()):
                    column = col1 if i == 0 else col2
                    with column:
                        if image_data['path'].exists():
                            image = Image.open(image_data['path'])
                            st.image(image, width=400, caption=image_data['name'])
                        else:
                            st.error(f"Image not found: {image_data['path']}")
                        
                        image_id = str(image_data['path'])
                        step_key = f"Step {st.session_state.current_step}"

                        if image_id not in st.session_state.image_responses:
                            st.session_state.image_responses[image_id] = {}

                        if step_key not in st.session_state.image_responses[image_id]:
                            st.session_state.image_responses[image_id][step_key] = {"Tags": [], "Comments": ""}

                        # Tags
                        tags = {
                            1: ["Vulnerable", "Strong", "Hallucinated", "Realistic", "Passive", "Active",
                                "Limited", "Empowered", "Funny", "Worried"],
                            2: ["Vulnerable", "Strong", "Hallucinated", "Realistic", "Passive", "Active",
                                "Limited", "Empowered", "Funny", "Worried"],
                            3: ["Vulnerable", "Strong", "Hallucinated", "Realistic", "Passive", "Active",
                                "Limited", "Empowered", "Funny", "Worried"],
                        }

                        btn_cols = st.columns(2)

                        for j, tag in enumerate(tags[st.session_state.current_step]):
                            with btn_cols[j % 2]:
                                button_key = f"tag_button_{st.session_state.current_step}_{i}_{j}"
                                if st.button(tag, key=button_key, use_container_width=True):
                                    if tag not in st.session_state.image_responses[image_id][step_key]["Tags"]:
                                        st.session_state.image_responses[image_id][step_key]["Tags"].append(tag)
                                    else:
                                        st.session_state.image_responses[image_id][step_key]["Tags"].remove(tag)

                        # Textbox individual para cada imagen
                        label = "Submit another word for left image:" if i == 0 else "Submit another word for right image:"
                        comment = st.text_area(
                            label, 
                            key=f"comments_step{st.session_state.current_step}_img{i}",
                            placeholder="Write here",
                            height=50)

                        st.markdown(f"""
                        <style>
                            #{f"comments_step{st.session_state.current_step}_img{i}"} {{
                                height: 30px !important;
                                width: 200px !important;
                                font-size: 0.8em !important;
                            }}
                        </style>
                        """, unsafe_allow_html=True)

                        # Guardar el comentario en el estado de sesión
                        st.session_state.image_responses[image_id][step_key]["Comments"] = comment

                        # Columna estrecha a la derecha
        with col3:
            # Añadir espacios en blanco para alinear con los botones de las otras columnas
            for _ in range(20):  # Ajusta este número según sea necesario
                st.write("")
            
            # Texto "Step x of 3"
            st.markdown(f"<h2 style='text-align: center;'>Step {st.session_state.current_step} of 3</h2>", unsafe_allow_html=True)
            
            # Botón para avanzar al siguiente step
            # button_label = "Next Images" if st.session_state.current_step < 3 else "Finish"
            # if st.button(button_label, key=f"next_button_step{st.session_state.current_step}_unique", use_container_width=True):
            #     if st.session_state.current_step < 3:
            #         st.session_state.current_step += 1
            #         st.session_state.current_prompt = random.choice(prompts)
            #     else:
            #         st.session_state.page = 'end'  # Cambiar a la página de finalización
            #     st.session_state.page = 'prompt1'
            #     st.rerun()
            button_label = "Next Images" if st.session_state.current_step < 3 else "Finish"
            if st.button(button_label, key=f"next_button_step{st.session_state.current_step}_unique", use_container_width=True):
                if st.session_state.current_step < 3:
                    st.session_state.current_step += 1
                    st.session_state.current_prompt = random.choice(prompts)  # Cambiar el prompt para el siguiente paso
                else:
                    st.session_state.page = 'end'  # Cambiar a la página de finalización
                    st.session_state.current_step = 1  # Reiniciar el paso si es necesario para un nuevo flujo
                    st.session_state.current_prompt = random.choice(prompts)  # Seleccionar un nuevo prompt

                # Regresar a la página de prompt1 para mostrar el nuevo prompt
                if st.session_state.page != 'end':  # Solo redirigir si no estamos en la página de finalización
                    st.session_state.page = 'prompt1'
                st.rerun()

# Página final de agradecimiento
    elif st.session_state.page == 'end':
        st.title("Thanks for participating! 😊")
        st.balloons()
        st.write("Your responses have been saved.")
        st.write("We appreciate your time and effort in completing this questionnaire.")
        if st.button("Start New Questionnaire"):
            # Reiniciar el cuestionario para una nueva sesión
            st.session_state.current_step = 1
            st.session_state.image_responses = {}
            st.session_state.page = 'intro'
            st.session_state.user_id = ''
            st.session_state.review_mode = False
            st.rerun()            

if __name__ == "__main__":
    main()
