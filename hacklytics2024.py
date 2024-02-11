import requests
import pandas as pd
from datetime import datetime, timedelta

def fetch_gdelt_data(base_url, date_str):
    url = f"{base_url}{date_str}.export.CSV.zip"
    response = requests.get(url)
    if response.status_code == 200:
        return pd.read_csv(response.content, compression='zip', header=None, sep='\t', usecols=[1, 4, 5], names=['Date', 'Source', 'Title'], encoding='utf-8')
    else:
        print(f"Failed to fetch data for {date_str}: Status code {response.status_code}")
        return pd.DataFrame()

def main():
    base_url = "http://data.gdeltproject.org/gdeltv2/"
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)  # Adjust based on your requirement
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    all_articles = pd.DataFrame()
    for single_date in date_range:
        date_str = single_date.strftime("%Y%m%d")
        print(f"Fetching data for {date_str}")
        daily_articles = fetch_gdelt_data(base_url, date_str)
        all_articles = pd.concat([all_articles, daily_articles], ignore_index=True)
        if len(all_articles) >= 100:  # Stop once we have 100 articles
            break
    
    # Optionally filter or process the data further here
    all_articles = all_articles.head(100)  # Ensure only 100 articles are kept
    
    # Save to CSV
    all_articles.to_csv('gdelt_articles.csv', index=False)
    print("Saved 100 articles to gdelt_articles.csv")

if __name__ == "__main__":
    main()
