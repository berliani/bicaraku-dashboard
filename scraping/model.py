from pymongo import MongoClient
from datetime import datetime
import pytz

class MongoDBHandler:
    def __init__(self, connection_uri):
        self.client = MongoClient(connection_uri)
        self.db = self.client.get_database("bicarakudb")
        self.collection = self.db["scraping"]
        
    def get_articles_by_sources(self, sources):
        return list(self.collection.find({"source": {"$in": sources}}, {"_id": 0}))
    
    def upsert_article(self, title, data):
        data["timestamp"] = datetime.now(pytz.timezone('Asia/Jakarta'))
        self.collection.update_one(
            {"title": title},
            {"$set": data},
            upsert=True
        )
    
    def get_last_update(self):
        last_article = self.collection.find_one(
            sort=[("timestamp", -1)],  
            projection={"timestamp": 1}  
        )
        
        if last_article and last_article.get("timestamp"):
            return last_article["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
        else:
            return "Belum ada data"