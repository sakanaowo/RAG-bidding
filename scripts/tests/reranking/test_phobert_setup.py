"""
Test script để verify PhoBERT setup
Chạy: python test_phobert_setup.py
"""

import time
from sentence_transformers import CrossEncoder

print("🔍 Testing PhoBERT setup...")
print("-" * 60)

# Test 1: Load model
print("\n1️⃣ Loading PhoBERT model...")
start = time.time()

try:
    # Thử với vinai/phobert-base-v2 (nhỏ hơn, nhanh hơn)
    model = CrossEncoder(
        'vinai/phobert-base-v2',
        device='cpu',
        max_length=256  # PhoBERT max sequence length
    )
    load_time = time.time() - start
    print(f"   ✅ Model loaded successfully in {load_time:.2f}s")
    print(f"   📦 Model: vinai/phobert-base-v2")
except Exception as e:
    print(f"   ❌ Error loading model: {e}")
    exit(1)

# Test 2: Sample inference
print("\n2️⃣ Testing inference with legal text...")
start = time.time()

query = "Quy định về bảo đảm dự thầu"
docs = [
    "Điều 14. Bảo đảm dự thầu là điều kiện bắt buộc đối với nhà thầu khi dự thầu.",
    "Điều 68. Bảo đảm thực hiện hợp đồng được thực hiện sau khi ký hợp đồng.",
    "Điều 10. Ưu đãi nhà thầu trong nước được quy định chi tiết tại Nghị định."
]

pairs = [[query, doc] for doc in docs]
scores = model.predict(pairs)
inference_time = time.time() - start

print(f"   ✅ Inference completed in {inference_time:.2f}s")
print(f"   📊 Scores:")
for i, (doc, score) in enumerate(zip(docs, scores)):
    print(f"      [{i+1}] Score: {score:.4f} - {doc[:60]}...")

# Test 3: Verify ranking
print("\n3️⃣ Verifying ranking quality...")
best_idx = scores.argmax()
if best_idx == 0:  # Điều 14 nên có score cao nhất
    print(f"   ✅ Correct! Điều 14 ranked #1 (score: {scores[0]:.4f})")
else:
    print(f"   ⚠️  Warning: Điều 14 not ranked #1 (best: doc {best_idx+1})")

# Test 4: Latency benchmark
print("\n4️⃣ Benchmarking latency for 10 docs...")
docs_10 = docs * 4  # Tạo 12 docs
pairs_10 = [[query, doc] for doc in docs_10[:10]]

start = time.time()
scores_10 = model.predict(pairs_10)
latency = (time.time() - start) * 1000  # Convert to ms

print(f"   ⏱️  Latency: {latency:.2f}ms for 10 docs")
if latency < 150:
    print(f"   ✅ Good! Under 150ms target")
else:
    print(f"   ⚠️  Warning: Slower than 150ms target")

print("\n" + "=" * 60)
print("✅ PhoBERT setup test COMPLETE!")
print("=" * 60)
