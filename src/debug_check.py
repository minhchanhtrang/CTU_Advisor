import chromadb
import os

db = chromadb.PersistentClient(path="./vector_db")
collection = db.get_collection("ctu_courses")
result = collection.get(include=["metadatas"])

metadatas = result.get("metadatas", [])
all_files = set()
nganh_hoc_list = set()

for m in metadatas:
    path = m.get("file_path", "")
    if path:
        all_files.add(os.path.basename(path))
    
    nganh = m.get("nganh_hoc", "Lỗi mất nhãn")
    nganh_hoc_list.add(nganh)

print(f"📊 Tổng số Node (Chunks): {collection.count()}")
print(f"📄 Tổng số File trong DB: {len(all_files)}")
print(f"📚 Danh sách các nhãn 'Ngành học' đang có:")
for n in sorted(nganh_hoc_list):
    print(f"   - {n}")