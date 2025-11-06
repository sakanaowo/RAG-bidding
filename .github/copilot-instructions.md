## Những điều cần lưu ý cho GitHub Copilot:

- khi đối thoại, nếu không phải từ ngữ chuyên ngành kỹ thuật, hãy sử dụng tiếng Việt.
- Cần xác nhận rằng các đề xuất mới của bạn phù hợp với phong cách mã hiện có trong kho lưu trữ này.
- Tránh đề xuất mã đã bị xóa hoặc không còn liên quan.
- Khi thiếu thông tin, hãy yêu cầu làm rõ thay vì đưa ra giả định. Hoặc nếu bạn không chắc chắn về một thay đổi, hãy đề xuất các lựa chọn thay thế.
- Hãy nhớ rằng các đề xuất của bạn sẽ được xem xét bởi các nhà phát triển
- Đảm bảo rằng các đề xuất của bạn tuân thủ các nguyên tắc và tiêu chuẩn mã hóa của dự án.
- Luôn ưu tiên tính rõ ràng và bảo trì trong các đề xuất của bạn.
- Nếu bạn nhận thấy các mẫu mã không nhất quán trong kho lưu trữ, hãy đề xuất các cải tiến để chuẩn hóa mã.
- Project này sử dụng tiếng Việt làm ngôn ngữ chính cho tài liệu và chú thích mã. Hãy đảm bảo rằng các đề xuất của bạn phù hợp với ngôn ngữ này.
- Project này sử dụng môi trường conda có tên là "venv". Đảm bảo rằng các đề xuất chạy code mới của bạn đã active môi trường này.
- Khi đề xuất các test mới:
  - hãy tham khảo cấu trúc và phong cách của các test hiện có trong `scripts/tests/TEST_README.md` để đảm bảo tính nhất quán.
  - Nếu muốn chạy một đoạn mã test api, mở một terminal mới và chạy đoạn mã đó trong môi trường conda "venv" vì các test api cần server đang chạy để kiểm tra.
- Khi có lỗi xảy ra, hãy kiểm tra các code logic liên quan trong project để hiểu nguyên nhân gốc rễ trước khi đề xuất sửa lỗi.
- Không được tự ý thay đổi code legacy trừ khi có chỉ dẫn cụ thể.
- bỏ qua các file hoặc folder có tên chứa -deprecated
