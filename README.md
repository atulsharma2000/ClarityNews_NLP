# Clarity News 📰  

Clarity News is an advanced news aggregation system that scrapes daily articles from various news websites, providing concise insights through AI-powered summarization and sentiment analysis.  

## 🔥 Features  

- **Automated News Scraping**: Extracts top news articles from multiple sources using `Selenium`.  
- **AI-Powered Summarization**: Uses `facebook/bart-large-cnn` for generating concise summaries of news articles.  
- **Sentiment Analysis**: Implements `facebook/bart-large-mnli` to classify news sentiment.  
- **Fine-Tuning Experiments**: Evaluates performance of fine-tuned `facebook/bart-base` and `unsloth/Meta-Llama-3.1-8B` on secondary datasets.  
- **Data Processing with PySpark**: Cleans and structures raw data for efficient processing.  
- **Visualization**: Uses `Matplotlib` and `Seaborn` to present sentiment insights effectively.  

## 🚀 Tech Stack  

- **Backend**: `Flask` (for API and application logic)  
- **Web Scraping**: `Selenium`  
- **AI Models**: `Transformers`, `Torch`  
- **Database**: `MySQL` (storing scraped news data)  
- **Data Processing**: `Pandas`, `PySpark`  
- **Visualization**: `Matplotlib`, `Seaborn`  

## 🛠 Installation  

### 1️⃣ Clone the Repository  
```sh
git clone https://github.com/your-username/Clarity-News.git
cd Clarity-News
