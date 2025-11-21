# Hướng dẫn Triển khai Chiến lược Cache Đa tầng cho Hệ thống RAG

## TL;DR

Để giảm độ trễ, tiết kiệm chi phí API và tăng hiệu suất, chúng ta sẽ triển khai kiến trúc cache 3 tầng sử dụng **Redis**.

-   **Nền tảng:** Sử dụng **Redis** vì tốc độ, khả năng chia sẻ và hỗ trợ **Tìm kiếm Vector (VSS)** qua module RediSearch.
-   **Tầng 1: Semantic Cache (Quan trọng nhất):** Cache câu trả lời cuối cùng. Key là *embedding của câu hỏi*, giúp xử lý các câu hỏi tương tự về mặt ngữ nghĩa. Bỏ qua toàn bộ pipeline RAG khi có cache hit.
-   **Tầng 2: Generation Cache:** Cache câu trả lời cuối cùng. Key là *hash của (câu hỏi + context đã truy xuất)*. Tránh gọi lại LLM khi có cùng ngữ cảnh.
-   **Tầng 3: Retrieval Cache:** Cache kết quả truy xuất (danh sách chunk ID). Key là *câu hỏi gốc (exact match)*. Đây là phiên bản nâng cấp của cache in-memory hiện tại.
-   **Vô hiệu hóa cache:** Bắt đầu với chiến lược **TTL (Time-To-Live)** đơn giản (ví dụ: 24 giờ).
-   **Kế hoạch:** Triển khai theo từng giai đoạn, bắt đầu bằng việc cài đặt Redis, sau đó tới Tầng 2, Tầng 1 và cuối cùng là Tầng 3.

---

## 1. Giới thiệu

Hệ thống RAG hiện tại thực hiện lại toàn bộ chu trình (embedding, retrieval, generation) cho gần như mọi yêu cầu, dẫn đến:
-   **Chi phí cao:** Mỗi lần gọi API của LLM và embedding đều tốn tiền.
-   **Độ trễ cao:** Thời gian chờ đợi của người dùng tăng lên do các tác vụ tính toán nặng.
-   **Lãng phí tài nguyên:** Xử lý lại các yêu cầu lặp đi lặp lại hoặc có cùng ngữ nghĩa.

Kiến trúc cache đa tầng được đề xuất để giải quyết triệt để các vấn đề này bằng cách lưu trữ kết quả ở các giai đoạn khác nhau của pipeline.

## 2. Công nghệ nền tảng: Redis

Redis được chọn làm trái tim của hệ thống cache vì các lý do sau:
-   **Tốc độ:** Là một CSDL in-memory, Redis cho tốc độ đọc/ghi cực nhanh, lý tưởng cho việc cache.
-   **Bền bỉ & Chia sẻ:** Dữ liệu có thể được lưu trữ bền bỉ và chia sẻ giữa nhiều tiến trình, nhiều server, khắc phục hoàn toàn nhược điểm của cache in-memory hiện tại.
-   **Vector Similarity Search (VSS):** Module **RediSearch** cho phép Redis lưu trữ và truy vấn các vector embedding hiệu quả, là nền tảng cho **Semantic Cache**.
-   **Cấu trúc dữ liệu đa dạng:** Hỗ trợ key-value, hash, list... phù hợp cho mọi tầng cache.

### Cài đặt Redis với RediSearch (Sử dụng Docker)

Tạo file `docker-compose.yml` với nội dung sau để khởi chạy một instance Redis có sẵn module RediSearch:

```yaml
version: '3.8'
services:
  redis-stack:
    image: redis/redis-stack:latest
    container_name: redis-rag-cache
    ports:
      - "6379:6379" # Cổng Redis client
      - "8001:8001" # Cổng RedisInsight UI (tùy chọn)
    volumes:
      - redis_data:/data
volumes:
  redis_data:
```
Chạy `docker-compose up -d` để khởi động.

## 3. Kiến trúc Cache Đa tầng

Thứ tự kiểm tra cache sẽ là: **Tầng 1 -> Tầng 2 -> Tầng 3**.

### 3.1. Tầng 1: Semantic Cache

-   **Mục tiêu:** Nắm bắt các câu hỏi có cùng ngữ nghĩa. Đây là tầng cache có tác động lớn nhất.
-   **Luồng hoạt động:**
    1.  Nhận `query` từ người dùng.
    2.  Tạo `query_embedding` từ `query`.
    3.  Thực hiện tìm kiếm vector trong chỉ mục cache trên Redis để tìm các embedding gần nhất.
    4.  **Cache Hit:** Nếu tìm thấy một embedding đủ gần (ví dụ: `cosine_similarity > 0.98`), lấy `final_answer` tương ứng từ Redis Hash và trả về ngay lập tức.
    5.  **Cache Miss:**
        a. Thực hiện toàn bộ pipeline RAG (Tầng 2, Tầng 3, retrieval, generation) để tạo `final_answer`.
        b. Lưu `query_embedding` vào chỉ mục vector trên Redis.
        c. Lưu `final_answer` và các metadata khác (ví dụ: `original_query`) vào một Redis Hash với key là ID của vector.

-   **Mã giả (Python):**
    ```python
    # Giả sử redis_vss_client là một client đã được cấu hình để tương tác với RediSearch
    SEMANTIC_CACHE_THRESHOLD = 0.98

    def get_answer_with_semantic_cache(query: str):
        query_embedding = embedding_service.create_embedding(query)

        # 1. Tìm kiếm trong cache
        search_results = redis_vss_client.search(query_embedding, top_k=1)

        if search_results and search_results[0].similarity > SEMANTIC_CACHE_THRESHOLD:
            # Cache Hit
            cached_answer_id = search_results[0].id
            cached_data = redis_client.hgetall(f"semantic_cache:{cached_answer_id}")
            print("Semantic Cache HIT!")
            return cached_data['answer']

        # 2. Cache Miss: Chạy pipeline RAG
        print("Semantic Cache MISS!")
        final_answer = run_full_rag_pipeline(query) # Bao gồm cả logic cache Tầng 2, 3

        # 3. Lưu vào cache
        new_id = str(uuid.uuid4())
        redis_vss_client.add(vector=query_embedding, id=new_id)
        redis_client.hset(f"semantic_cache:{new_id}", mapping={
            "answer": final_answer,
            "original_query": query,
            "created_at": datetime.now().isoformat()
        })

        return final_answer
    ```

### 3.2. Tầng 2: Generation Cache

-   **Mục tiêu:** Tránh gọi LLM khi có cùng một ngữ cảnh (câu hỏi + tài liệu truy xuất).
-   **Luồng hoạt động:**
    1.  Sau khi có được `retrieved_chunks` từ bước retrieval.
    2.  Tạo một `cache_key` bằng cách hash `query` và ID của các `retrieved_chunks`. Việc sắp xếp các ID đảm bảo hash nhất quán.
    3.  Kiểm tra `cache_key` trong Redis.
    4.  **Cache Hit:** Lấy `final_answer` từ Redis và trả về.
    5.  **Cache Miss:**
        a. Gọi LLM để sinh `final_answer`.
        b. Lưu cặp `(cache_key, final_answer)` vào Redis với một TTL.

-   **Mã giả (Python):**
    ```python
    import hashlib

    def get_answer_with_generation_cache(query: str, retrieved_chunks: list):
        chunk_ids = sorted([chunk.id for chunk in retrieved_chunks])
        
        # Tạo key nhất quán
        key_material = query + "".join(chunk_ids)
        cache_key = f"gen_cache:{hashlib.sha256(key_material.encode()).hexdigest()}"

        # 1. Kiểm tra cache
        cached_answer = redis_client.get(cache_key)
        if cached_answer:
            # Cache Hit
            print("Generation Cache HIT!")
            return cached_answer.decode('utf-8')

        # 2. Cache Miss
        print("Generation Cache MISS!")
        prompt = create_prompt(query, retrieved_chunks)
        final_answer = generation_service.generate(prompt)

        # 3. Lưu vào cache
        redis_client.set(cache_key, final_answer, ex=86400) # 24-hour TTL

        return final_answer
    ```

### 3.3. Tầng 3: Retrieval Cache

-   **Mục tiêu:** Giảm tải cho Vector DB (Pinecone). Nâng cấp cache hiện tại.
-   **Luồng hoạt động:**
    1.  Tạo `cache_key` từ `query`.
    2.  Kiểm tra `cache_key` trong Redis.
    3.  **Cache Hit:** Lấy danh sách `chunk_ids` từ Redis, sau đó lấy nội dung đầy đủ của chunks từ một CSDL khác (nếu cần) và trả về.
    4.  **Cache Miss:**
        a. Thực hiện truy vấn trên Pinecone để lấy `retrieved_chunks`.
        b. Lưu danh sách `chunk_ids` vào Redis với key là `cache_key`.

-   **Mã giả (Python):**
    ```python
    import json

    def get_chunks_with_retrieval_cache(query: str):
        cache_key = f"ret_cache:{query}"

        # 1. Kiểm tra cache
        cached_chunk_ids_json = redis_client.get(cache_key)
        if cached_chunk_ids_json:
            print("Retrieval Cache HIT!")
            chunk_ids = json.loads(cached_chunk_ids_json)
            return get_chunks_by_ids(chunk_ids) # Hàm giả định lấy chunk từ DB

        # 2. Cache Miss
        print("Retrieval Cache MISS!")
        query_embedding = embedding_service.create_embedding(query)
        retrieved_chunks = vector_db_client.query(embedding=query_embedding)
        
        # 3. Lưu IDs vào cache
        chunk_ids_to_cache = [chunk.id for chunk in retrieved_chunks]
        redis_client.set(cache_key, json.dumps(chunk_ids_to_cache), ex=86400)

        return retrieved_chunks
    ```

## 4. Chiến lược Vô hiệu hóa Cache (Cache Invalidation)

-   **TTL (Time-To-Live):** Đơn giản và hiệu quả cho bước đầu. Đặt thời gian hết hạn (ví dụ: `ex=86400` cho 24 giờ) khi `set` key trong Redis. Dữ liệu sẽ tự động được làm mới sau khi hết hạn.
-   **Event-Driven (Nâng cao):** Trong tương lai, có thể xây dựng một cơ chế lắng nghe sự kiện cập nhật tài liệu. Khi một tài liệu thay đổi, một tác vụ sẽ được kích hoạt để tìm và xóa tất cả các mục cache có chứa ID của tài liệu đó.

## 5. Kế hoạch Triển khai Phân kỳ

1.  **Giai đoạn 1: Setup:** Cài đặt Redis (sử dụng Docker như hướng dẫn ở trên) và tích hợp `redis-py` client vào project (trong `src/utils/`).
2.  **Giai đoạn 2: Triển khai Generation Cache (Tầng 2):** Tích hợp logic của Tầng 2 vào `ChatService`. Đây là "quick win" giúp giảm chi phí LLM.
3.  **Giai đoạn 3: Triển khai Semantic Cache (Tầng 1):** Đây là bước phức tạp nhất, đòi hỏi thiết lập chỉ mục vector trên RediSearch. Tích hợp logic của Tầng 1 vào `ChatService` để nó được kiểm tra đầu tiên.
4.  **Giai đoạn 4: Nâng cấp Retrieval Cache (Tầng 3):** Thay thế cache in-memory hiện tại bằng logic của Tầng 3 sử dụng Redis.
5.  **Giai đoạn 5: Hoàn thiện:** Áp dụng TTL nhất quán và xem xét chiến lược vô hiệu hóa cache nâng cao nếu cần.
