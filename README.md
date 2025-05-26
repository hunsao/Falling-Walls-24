# AI & Ageism Project

This project aims to collect data on how AI portrays age. Users can tag and describe AI-generated images, contributing to a better understanding of age representation in AI.

This project is part of the "Ageism in AI" initiative, funded by the Volkswagen Foundation.

## Technologies Used

* Python
* Streamlit
* Google Drive
* Google Sheets

## Repository Structure

*   `IMAGES/`: Contains AI-generated images categorized by age depiction (neutral, older).
*   `TERMS/`: Contains terms and consent documents.
*   `falling_walls.py`: The main Streamlit application script for the interactive questionnaire.
*   `falling_walls_multilingual.py`, `falling_walls_polish.py`: Likely variations of the main script for different languages.
*   `requirements.txt`: Lists Python dependencies.

## Running the Application

To run the application, follow these steps:

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up Google Cloud credentials:**
    Ensure your Google Cloud service account key JSON file is available and set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to its path. For example:
    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
    ```
    Alternatively, you might need to set up the `GOOGLE_SERVICE_ACCOUNT` environment variable if the application uses it directly.

3.  **Run the Streamlit application:**
    ```bash
    streamlit run falling_walls.py
    ```

## Data Collection

User responses from the interactive questionnaire are collected and stored in a Google Sheet. This data is used for research purposes to analyze how AI portrays different age groups and to understand potential biases in AI-generated content. All data is collected anonymously and handled in accordance with privacy regulations.
