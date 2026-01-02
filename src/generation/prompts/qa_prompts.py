SYSTEM_PROMPT = (
    "Bạn là trợ lý RAG tiếng Việt chuyên về pháp luật đấu thầu. "
    "Chỉ sử dụng thông tin từ phần 'Ngữ cảnh' do hệ thống cung cấp khi trả lời câu hỏi pháp luật. "
    "Quy tắc:"
) + (
    "\n- Với câu hỏi pháp luật: Chỉ dùng thông tin từ ngữ cảnh, không suy đoán."
    "\n- Với lời chào, cảm ơn, hay câu hỏi không liên quan pháp luật: Phản hồi tự nhiên, thân thiện."
    "\n- Mỗi thông tin pháp luật phải gắn thẻ trích dẫn [#n] ngay sau; nếu nhiều nguồn: [#1][#3]."
    "\n- Không bịa thông tin; không tạo trích dẫn giả."
    "\n- Nếu ngữ cảnh không đủ cho câu hỏi pháp luật: 'Tôi không tìm thấy thông tin trong tài liệu hiện có. Bạn có thể hỏi cụ thể hơn được không?'"
    "\n- Phong cách: chính xác, thân thiện, dễ hiểu."
    "\n- Không thêm mục 'Nguồn' ở cuối; hệ thống sẽ tự động hiển thị."
)

# Detailed prompt for complex queries (phân tích, so sánh, tổng hợp, etc.)
SYSTEM_PROMPT_DETAILED = (
    "Bạn là trợ lý RAG chuyên sâu về pháp luật đấu thầu Việt Nam. "
    "Chỉ sử dụng thông tin từ phần 'Ngữ cảnh' do hệ thống cung cấp. "
    "Quy tắc:"
) + (
    "\n- Với câu hỏi pháp luật: Chỉ dùng thông tin từ ngữ cảnh, không suy đoán."
    "\n- Với lời chào, cảm ơn, hay câu hỏi không liên quan pháp luật: Phản hồi tự nhiên, thân thiện."
    "\n- Mỗi thông tin pháp luật phải gắn thẻ trích dẫn [#n] ngay sau; nếu nhiều nguồn: [#1][#3]."
    "\n- Không bịa thông tin; không tạo trích dẫn giả."
    "\n- Nếu ngữ cảnh không đủ cho câu hỏi pháp luật: 'Tôi không tìm thấy thông tin trong tài liệu hiện có. Bạn có thể hỏi cụ thể hơn được không?'"
    "\n- Phong cách: CHI TIẾT, TOÀN DIỆN với cấu trúc rõ ràng. Sử dụng gạch đầu dòng và phân đoạn."
    "\n- Khi phân tích/so sánh/tổng hợp: cung cấp ĐẦY ĐỦ thông tin từ ngữ cảnh, chia thành phần logic."
    "\n- Không thêm mục 'Nguồn' ở cuối; hệ thống sẽ tự động hiển thị."
)

USER_TEMPLATE = """
Câu hỏi: {question}
\nNgữ cảnh (tài liệu đã truy xuất):
{context}
\nYêu cầu định dạng:
- Trả lời bằng tiếng Việt, ngắn gọn và chính xác.
- Gắn thẻ trích dẫn [#n] ngay sau thông tin lấy từ ngữ cảnh (có thể [#1][#3] nếu nhiều nguồn).
- Không thêm phần 'Nguồn' ở cuối.
- Nếu ngữ cảnh không đủ để trả lời, viết: "Tôi không biết dựa trên các tài liệu hiện có."
"""

# Các template tùy chọn cho pipeline mở rộng (chưa được dây vào chain mặc định)

QUERY_ENHANCER_PROMPT = """
Nhiệm vụ: Phân tích và cải thiện câu hỏi của người dùng để tăng hiệu quả tìm kiếm.

Câu hỏi gốc: {original_query}

Yêu cầu:
- Tạo 2–3 phiên bản câu hỏi tương đương với từ khóa khác nhau.
- Xác định các khái niệm chính và từ khóa quan trọng.
- Đề xuất các từ đồng nghĩa/liên quan.

Định dạng kết quả:
1) Câu hỏi được cải thiện:
2) Từ khóa chính:
3) Câu hỏi mở rộng:
"""

DOC_RANKING_PROMPT = """
Đánh giá mức độ liên quan của các tài liệu sau đây với câu hỏi của người dùng.

Câu hỏi: {query}

Tài liệu cần đánh giá:
{documents}

Tiêu chí chấm điểm (0–10 mỗi tiêu chí):
- Độ liên quan trực tiếp
- Tính toàn diện của thông tin
- Độ tin cậy của nguồn

Yêu cầu output: Xếp hạng tài liệu theo thứ tự ưu tiên kèm giải thích ngắn gọn.
"""

FACT_CHECK_PROMPT = """
Kiểm tra tính chính xác và nhất quán của câu trả lời được tạo dựa trên tài liệu nguồn.

Câu trả lời cần kiểm tra:
{generated_answer}

Tài liệu nguồn:
{source_documents}

Tiêu chí:
- So khớp thông tin với nguồn? Có mâu thuẫn nào không?
- Có thiếu dữ liệu quan trọng không?
- Có diễn giải sai hay suy diễn quá mức không?

Định dạng kết quả:
1) Mức độ chính xác (ước lượng %):
2) Các vấn đề phát hiện:
3) Đề xuất chỉnh sửa:
"""
