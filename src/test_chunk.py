import chromadb

db = chromadb.PersistentClient(path="./vector_db")
collection = db.get_collection("ctu_courses")
result = collection.get(limit=3, include=["documents", "metadatas"])

for i in range(3):
    text = result["documents"][i]
    metadata = result["metadatas"][i]
    
    print(f"\n{'='*40}")
    print(f"MẢNH THỨ {i+1}")
    print(f"{'='*40}")
    print("📊 METADATA BỊ ẨN:")
    for key, value in metadata.items():
        print(f"   - {key}: {value}")
        
    print(f"\n📝 NỘI DUNG:\n{text[:250]}...\n")