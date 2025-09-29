# Railway AI Decision Support System - Backend

![Python](https://img.shields.io/badge/python-3.9-blue.svg)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-%23F7931E.svg?style=for-the-badge&logo=scikit-learn&logoColor=white)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

This repository contains the backend service for the Railway AI Decision Support System. It is responsible for simulating complex railway scenarios, training a machine learning model, and serving real-time operational decisions via a REST API.

The system is designed to model the **Solapur-Wadi** railway section, generating realistic traffic conflicts and disruptions to train a robust AI capable of optimizing network flow and minimizing delays.

### Key Features

-   **AI-Powered Decisions**: Utilizes a `RandomForestClassifier` model trained to make optimal decisions (e.g., Proceed, Reduce Speed, Hold/Reroute) for each train.
-   **Dynamic Scenario Generation**: Can generate a variety of challenging, problem-centric scenarios on-demand, including high-density traffic, bottleneck conflicts, and major disruptions.
-   **Human-Readable Reasoning**: The AI doesn't just provide a decision; it provides a clear, text-based reason for its recommendation, making the system transparent.
-   **Coordinated Actions**: Implements post-processing logic to ensure decisions are coordinated. For example, if a high-priority train is told to overtake, the lower-priority train is automatically instructed to hold.
-   **REST API**: Exposes a simple yet powerful endpoint to fetch a complete, live report of a generated scenario and the corresponding AI decisions.

### Technology Stack

-   **Language**: Python 3.9+
-   **Framework**: Flask
-   **Machine Learning**: Scikit-learn, Pandas, NumPy
-   **Production Server**: Gunicorn
-   **Deployment**: Render

---

### Getting Started (Local Setup)

Follow these instructions to get the backend running on your local machine for development and testing.

**Prerequisites:**
-   Python 3.9 or higher
-   `pip` and `venv`
-   Git LFS (for handling the large model file)

**1. Clone the repository:**
```bash
git clone https://github.com/Kartikesh07/RailSetuBackend.git
cd railway-ai-backend
```

**2. Set up Git LFS:**
This project uses Git LFS to manage the large `railway_ai_model.joblib` file.
```bash
git lfs install
git lfs pull
```

**3. Create and activate a virtual environment:**
```bash
# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate
```

**4. Install dependencies:**
```bash
pip install -r requirements.txt
```

**5. Running the Application:**

There are two main modes:

**A) Train a New Model (Optional):**
To generate new training data and train the AI model from scratch, run `main.py`. This will create a new `railway_ai_model.joblib` file.
```bash
python main.py
```

**B) Run the API Server:**
To start the Flask development server (which uses the pre-trained model), run:
```bash
flask run --host=0.0.0.0 --port=5000
```
The API will now be accessible at `http://localhost:5000`.

### API Endpoint

-   **URL**: `/api/live_report`
-   **Method**: `GET`
-   **Description**: Generates a new, random railway scenario and returns a complete report including system metrics, train data, and AI-driven decisions for each active train.
-   **Success Response (200 OK)**:
    ```json
    {
      "timestamp": "2023-10-27T10:30:00.123Z",
      "section": "Solapur-Wadi",
      "metrics": { "active_trains": 15, "average_delay_minutes": 12.5, ... },
      "decisions": {
        "13017": {
          "decision": "Proceed normally",
          "confidence": 0.98,
          "reasoning": "Path clear with low downstream congestion..."
        },
        ...
      },
      "trains": [ ... ],
      "stations": [ ... ]
    }
    ```

### Deployment

This backend is deployed on **Render** using its free tier.

-   **Build Command**: `pip install -r requirements.txt`
-   **Start Command**: `gunicorn app:app`

**Important Note:** Render's free services "spin down" after 15 minutes of inactivity. The first request to an inactive service may take 30-60 seconds to respond while the server wakes up. The frontend application has been designed to handle this delay gracefully.