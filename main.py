import os
import base64
from io import BytesIO
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, render_template, request, jsonify, url_for
import mysql.connector
from transformers import pipeline
import torch

# Configure Matplotlib for non-GUI environments
matplotlib.use("Agg")

# Suppress TensorFlow logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


class DatabaseManager:
    """Handles database connections and operations."""

    def __init__(self, config):
        self.config = config

    def get_connection(self):
        try:
            connection = mysql.connector.connect(**self.config)
            if connection.is_connected():
                return connection
        except mysql.connector.Error as e:
            print(f"Database connection error: {e}")
        return None


class SentimentAnalyzer:
    """Handles sentiment analysis and visualization."""

    def __init__(self, device):
        self.sentiment_analyzer = pipeline(
            "zero-shot-classification", model="facebook/bart-large-mnli", device=device
        )
        self.sentiment_labels = [
            "positive",
            "negative",
            "neutral",
            "joy",
            "sadness",
            "anger",
            "fear",
            "trust",
        ]

    def analyze_and_visualize(self, text, summary):
        try:
            analysis_output = self.sentiment_analyzer(
                text, candidate_labels=self.sentiment_labels, multi_label=True
            )
            sentiments = {
                emotion: score
                for emotion, score in zip(
                    analysis_output["labels"], analysis_output["scores"]
                )
            }

            # Create a DataFrame for visualization
            df_sentiments = pd.DataFrame(
                sentiments.items(), columns=["Emotion", "Score"]
            )

            # Generate a bar plot
            plt.figure(figsize=(10, 6))
            sns.set_theme(style="whitegrid")
            sns.set_palette("husl")
            sns.barplot(x="Emotion", y="Score", data=df_sentiments)

            plt.title("Sentiment Analysis", fontsize=16, fontweight="bold")
            plt.xlabel("Emotion", fontsize=14)
            plt.ylabel("Score", fontsize=14)
            plt.xticks(rotation=45)
            sns.despine()

            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            plt.close()
            plot_base64 = base64.b64encode(buf.getvalue()).decode("ascii")

            # Save sentiment data to CSV
            self._save_to_csv(summary, sentiments)

            return plot_base64
        except Exception as e:
            print(f"Error generating sentiment plot: {e}")
            return None

    @staticmethod
    def _save_to_csv(summary, sentiments):
        sentiment_data = {"Text Summary": summary, **sentiments}

        sentiment_df = pd.DataFrame([sentiment_data])
        file_exists = os.path.exists("sentiment_results.csv")
        sentiment_df.to_csv(
            "sentiment_results.csv", mode="a", header=not file_exists, index=False
        )


class Summarizer:
    """Handles text summarization."""

    def __init__(self):
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

    def summarize(self, text, max_length=100, min_length=25):
        try:
            return self.summarizer(
                text, max_length=max_length, min_length=min_length, do_sample=False
            )[0]["summary_text"]
        except Exception as e:
            print(f"Summarization error: {e}")
            return None


class NewsApp:
    """Main Flask application."""

    def __init__(self, db_config):
        self.app = Flask(__name__)
        self.db_manager = DatabaseManager(db_config)
        self.summarizer = Summarizer()
        self.sentiment_analyzer = SentimentAnalyzer(
            device=torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        )
        self._setup_routes()

    def _setup_routes(self):
        self.app.add_url_rule("/", "home", self.home)
        self.app.add_url_rule("/index", "index", self.index)
        self.app.add_url_rule("/customsummary", "customsummary", self.customsummary)

        self.app.add_url_rule(
            "/summarize", "summarize", self.summarize, methods=["POST"]
        )
        self.app.add_url_rule(
            "/summary/<int:summary_id>", "show_summary", self.show_summary
        )

    def home(self):
        return render_template("home.html")

    def customsummary(self):
        return render_template("customsummary.html")

    def index(self):
        connection = self.db_manager.get_connection()
        if not connection:
            return "Failed to connect to the database.", 500

        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, title, content FROM news ORDER BY id DESC LIMIT 10"
            )
            results = cursor.fetchall()
            return render_template("index.html", news=results)
        except mysql.connector.Error as e:
            print(f"Database error: {e}")
            return "An error occurred while fetching data.", 500
        finally:
            cursor.close()
            connection.close()

    def summarize(self):
        data = request.get_json()
        text_to_summarize = data.get("text", "").strip()
        if not text_to_summarize:
            return jsonify({"error": "No text provided to summarize."}), 400

        connection = self.db_manager.get_connection()
        if not connection:
            return jsonify({"error": "Database connection failed."}), 500

        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO summaries (full_text) VALUES (%s)", (text_to_summarize,)
            )
            connection.commit()
            saved_id = cursor.lastrowid
        except mysql.connector.Error as e:
            print(f"Error saving full text: {e}")
            return jsonify({"error": "Failed to save full text."}), 500
        finally:
            cursor.close()

        summarized_text = self.summarizer.summarize(text_to_summarize)
        if not summarized_text:
            return jsonify({"error": "Failed to generate summary."}), 500

        try:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE summaries SET summary = %s WHERE id = %s",
                (summarized_text, saved_id),
            )
            connection.commit()
        except mysql.connector.Error as e:
            print(f"Error saving summary: {e}")
            return jsonify({"error": "Failed to save summary."}), 500
        finally:
            cursor.close()
            connection.close()

        plot_data = self.sentiment_analyzer.analyze_and_visualize(
            summarized_text, summarized_text
        )

        return jsonify(
            {
                "summary": summarized_text,  # Add this
                "redirect_url": url_for("show_summary", summary_id=saved_id),
                "plot": plot_data,
            }
        )

    def show_summary(self, summary_id):
        connection = self.db_manager.get_connection()
        if not connection:
            return "Failed to connect to the database.", 500

        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT full_text, summary FROM summaries WHERE id = %s", (summary_id,)
            )
            result = cursor.fetchone()
            if not result:
                return "Summary not found.", 404

            plot_data = self.sentiment_analyzer.analyze_and_visualize(
                result["summary"], result["summary"]
            )
            return render_template(
                "summary.html",
                full_text=result["full_text"],
                summary=result["summary"],
                plot=plot_data,
            )
        except mysql.connector.Error as e:
            print(f"Error fetching summary: {e}")
            return "An error occurred while fetching the summary.", 500
        finally:
            cursor.close()
            connection.close()

    def run(self, **kwargs):
        self.app.run(**kwargs)


if __name__ == "__main__":
    DB_CONFIG = {
        "host": "localhost",
        "user": "root",
        "password": "manager",
        "database": "news_db",
    }
    app = NewsApp(DB_CONFIG)
    app.run(debug=True)
