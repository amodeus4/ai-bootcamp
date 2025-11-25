"""Elasticsearch email storage and search."""

from typing import Dict, List
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from .schemas import EmailDocument


class ElasticsearchEmailStore:
    """Manages email documents in Elasticsearch."""

    def __init__(
        self,
        es_host: str = "localhost",
        es_port: int = 9200,
        index_name: str = "emails",
    ):
        self.es = Elasticsearch([f"http://{es_host}:{es_port}"])
        self.index_name = index_name

        # Check if index exists
        if not self.es.indices.exists(index=self.index_name):
            print(f"Index '{self.index_name}' doesn't exist. Creating...")
            self.create_index()
        else:
            print(f"✓ Index '{self.index_name}' already exists")

    def create_index(self):
        """Create Elasticsearch index with optimized mapping."""
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "email_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop", "snowball"],
                        }
                    }
                },
            },
            "mappings": {
                "properties": {
                    "email_id": {"type": "keyword"},
                    "thread_id": {"type": "keyword"},
                    "sender": {
                        "properties": {
                            "name": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "email": {"type": "keyword"},
                        }
                    },
                    "recipients": {"type": "keyword"},
                    "cc": {"type": "keyword"},
                    "bcc": {"type": "keyword"},
                    "subject": {
                        "type": "text",
                        "analyzer": "email_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "body": {
                        "properties": {
                            "plain": {"type": "text", "analyzer": "email_analyzer"},
                            "html": {"type": "text", "index": False},
                        }
                    },
                    "snippet": {"type": "text"},
                    "date": {"type": "date"},
                    "processed_at": {"type": "date"},
                    "attachments": {
                        "type": "nested",
                        "properties": {
                            "filename": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "mime_type": {"type": "keyword"},
                            "size": {"type": "long"},
                            "has_content": {"type": "boolean"},
                        },
                    },
                    "has_attachments": {"type": "boolean"},
                    "attachment_count": {"type": "integer"},
                    "labels": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "priority": {"type": "keyword"},
                    "is_read": {"type": "boolean"},
                    "is_important": {"type": "boolean"},
                    "is_starred": {"type": "boolean"},
                    "extracted_data": {"type": "object", "enabled": True},
                    "action_items": {
                        "type": "nested",
                        "properties": {
                            "description": {"type": "text"},
                            "priority": {"type": "keyword"},
                            "due_date": {"type": "date"},
                            "type": {"type": "keyword"},
                            "completed": {"type": "boolean"},
                        },
                    },
                    "action_count": {"type": "integer"},
                    "processing_status": {"type": "keyword"},
                    "processing_errors": {"type": "text"},
                    "embedding": {"type": "keyword"},
                    "thread_messages_count": {"type": "integer"},
                    "is_thread_starter": {"type": "boolean"},
                }
            },
        }

        self.es.indices.create(index=self.index_name, body=mapping)
        print(f"✓ Created index: {self.index_name}")

    def search(self, query: Dict) -> List[Dict]:
        """Execute a search query."""
        result = self.es.search(index=self.index_name, body=query)
        return [hit["_source"] for hit in result["hits"]["hits"]]

    def bulk_index(self, documents: List[EmailDocument]) -> Dict:
        """Bulk index email documents."""
        actions = [
            {
                "_index": self.index_name,
                "_id": doc.email_id,
                "_source": doc.to_es_document()["_source"],
            }
            for doc in documents
        ]

        success, failed = bulk(self.es, actions)
        return {"success": success, "failed": failed}

    def update(self, email_id: str, updates: Dict) -> Dict:
        """Update an email document."""
        try:
            self.es.update(index=self.index_name, id=email_id, body={"doc": updates})
            return {"status": "success", "email_id": email_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}
