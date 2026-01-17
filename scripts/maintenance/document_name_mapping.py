#!/usr/bin/env python3
"""
Document Name Mapping - Manual data map for document names

This module contains the correct document names based on:
1. Original filenames
2. Legal document naming conventions

Usage:
    from scripts.maintenance.document_name_mapping import DOCUMENT_NAME_MAP, get_document_name
"""

# ==============================================================================
# DATA MAP: Tên chính xác cho các documents
# Key: document UUID (id)
# Value: dict với các metadata chính xác
# ==============================================================================

DOCUMENT_NAME_MAP = {
    # =========================================================================
    # LAW (Luật)
    # =========================================================================
    "2c0190d7-e443-45ca-be74-a56b5f66378e": {
        "document_name": "Văn bản hợp nhất 126/VBHN-VPQH 2025 - Luật Đấu thầu",
        "document_id": "VBHN-126-2025",
        "document_type": "law",
        "category": "Luật chính",
    },
    "b75593c5-054b-430d-a47c-dca08b5a966d": {
        "document_name": "Luật Đấu thầu số 22/2023/QH15",
        "document_id": "LUAT-22-2023-QH15",
        "document_type": "law",
        "category": "Luật chính",
    },
    "01534dc5-302b-4976-8389-73f75710670b": {
        "document_name": "Luật số 57/2024/QH15 - Sửa đổi Luật Quy hoạch",
        "document_id": "LUAT-57-2024-QH15",
        "document_type": "law",
        "category": "Luật chính",
    },
    "ce373744-54fa-482b-acf0-2a6882a21de6": {
        "document_name": "Luật số 90/2025/QH15 - Sửa đổi Luật Đấu thầu",
        "document_id": "LUAT-90-2025-QH15",
        "document_type": "law",
        "category": "Luật chính",
    },
    # =========================================================================
    # DECREE (Nghị định)
    # =========================================================================
    "901cb895-9a98-4f71-9d52-b3947846de21": {
        "document_name": "Nghị định 214/2025/NĐ-CP - Thay thế NĐ 24",
        "document_id": "ND-214-2025",
        "document_type": "decree",
        "category": "Nghị định",
    },
    # =========================================================================
    # DECISION (Quyết định)
    # =========================================================================
    "a1f13b07-70f0-40f9-b4e2-685d72150548": {
        "document_name": "Quyết định 1667/QĐ-BYT - Áp dụng hình thức lựa chọn nhà thầu",
        "document_id": "QD-1667-BYT",
        "document_type": "decision",
        "category": "Quyết định",
    },
    # =========================================================================
    # CIRCULAR (Thông tư) - Thông tư 80/2025/TT-BTC
    # =========================================================================
    "48c41cd6-cabe-4722-ba37-8d3c19712c07": {
        "document_name": "Thông tư 80/2025/TT-BTC - Lời văn",
        "document_id": "TT-80-2025-LOI-VAN",
        "document_type": "circular",
        "category": "Thông tư",
    },
    "3fddf6ca-fd3c-40f2-be67-bcad6eaaed92": {
        "document_name": "Thông tư 80/2025/TT-BTC - Phạm vi điều chỉnh",
        "document_id": "TT-80-2025-DIEU-1",
        "document_type": "circular",
        "category": "Thông tư",
    },
    "b0dc306b-3d27-448b-a5ae-c5dad159aca7": {
        "document_name": "Thông tư 80/2025/TT-BTC - Quyết định ban hành",
        "document_id": "TT-80-2025-QD",
        "document_type": "circular",
        "category": "Thông tư",
    },
    "508ce911-f0de-4a45-8b25-5ad22db4f05c": {
        "document_name": "Thông tư 80/2025/TT-BTC",
        "document_id": "TT-80-2025",
        "document_type": "circular",
        "category": "Thông tư",
    },
    # =========================================================================
    # BIDDING TEMPLATES - Kế hoạch LCNT
    # =========================================================================
    "1038ad63-be1a-4de5-84db-e2117a2f9937": {
        "document_name": "Mẫu 01A-02C: Kế hoạch tổng thể lựa chọn nhà thầu",
        "document_id": "MAU-01A-02C-KHTT",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "48e13aec-30ee-4e8d-a0f2-d71d6d761338": {
        "document_name": "Phụ lục 01: Biên bản đóng thầu và các mẫu biểu",
        "document_id": "PHU-LUC-01",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # BIDDING TEMPLATES - HSYC (Hồ sơ yêu cầu)
    # =========================================================================
    "d07d1ae2-64d5-4590-84df-3e6695931ddc": {
        "document_name": "Mẫu 01A: Hồ sơ yêu cầu - Xây lắp",
        "document_id": "MAU-01A-HSYC-XL",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "d99c7882-7199-40f7-89b8-2351cb6dd1e9": {
        "document_name": "Mẫu 01B: Hồ sơ yêu cầu - Hàng hóa",
        "document_id": "MAU-01B-HSYC-HH",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "5ff896aa-8daf-4b95-a22e-34acb1d48bcf": {
        "document_name": "Mẫu 01C: Hồ sơ yêu cầu - Phi tư vấn",
        "document_id": "MAU-01C-HSYC-PTV",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "b0429620-2e0f-4769-ba3e-06394288d1bd": {
        "document_name": "Mẫu 01D: Hồ sơ yêu cầu - Tư vấn",
        "document_id": "MAU-01D-HSYC-TV",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # BIDDING TEMPLATES - BCĐG (Báo cáo đánh giá)
    # =========================================================================
    "51203a6f-325f-46ab-a9de-302823884f47": {
        "document_name": "Mẫu 02A: Báo cáo đánh giá HSDT - 1 giai đoạn 1 túi",
        "document_id": "MAU-02A-BCDG-1GD1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "1638db9d-9d0e-4d70-822c-46f1d30a3154": {
        "document_name": "Mẫu 02B: Báo cáo đánh giá HSDT - 1 giai đoạn 2 túi",
        "document_id": "MAU-02B-BCDG-1GD2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "3673c5ea-67a4-4ce3-9aa4-1ac1f8daf4a5": {
        "document_name": "Mẫu 02C: Báo cáo đánh giá HSDT - Gói thầu tư vấn",
        "document_id": "MAU-02C-BCDG-TV",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # BIDDING TEMPLATES - BCTĐ (Báo cáo thẩm định)
    # =========================================================================
    "846f54fe-f036-461b-8bfd-88ade0fd5567": {
        "document_name": "Mẫu 03A: Báo cáo thẩm định HSMT",
        "document_id": "MAU-03A-BCTD-HSMT",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "2ac83c6a-e21f-440d-bc95-c324793fe5ce": {
        "document_name": "Mẫu 03B: Báo cáo thẩm định - Danh sách đáp ứng kỹ thuật",
        "document_id": "MAU-03B-BCTD-DSKT",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "88c2ce37-bbcd-44a9-a653-2023f2a3070e": {
        "document_name": "Mẫu 03C: Báo cáo thẩm định kết quả lựa chọn nhà thầu",
        "document_id": "MAU-03C-BCTD-KQLCNT",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # BIDDING TEMPLATES - Kiểm tra đấu thầu (Mẫu 4.x)
    # =========================================================================
    "da10cfca-66ec-4ba0-bef2-488bde421660": {
        "document_name": "Mẫu 4.1A: Kế hoạch kiểm tra định kỳ hoạt động đấu thầu",
        "document_id": "MAU-04-1A-KHKT-DK",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "51375636-7bbe-4206-a4b9-7d0cda409700": {
        "document_name": "Mẫu 4.1B: Kế hoạch kiểm tra chi tiết",
        "document_id": "MAU-04-1B-KHKT-CT",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "c049f59f-e582-42cc-94bb-2bda839f60b3": {
        "document_name": "Mẫu 4.2: Đề cương báo cáo tình hình đấu thầu",
        "document_id": "MAU-04-2-DCBC",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "7f23ccf1-50e5-493b-b9d0-ac3168924783": {
        "document_name": "Mẫu 4.3: Báo cáo kiểm tra hoạt động lựa chọn nhà thầu",
        "document_id": "MAU-04-3-BCKT",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "e1d362ff-b2a3-4e3b-88c9-6b8c52802007": {
        "document_name": "Mẫu 4.4: Kết luận kiểm tra hoạt động lựa chọn nhà thầu",
        "document_id": "MAU-04-4-KLKT",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "001c3fe9-1766-4015-94b1-3a1ae58046fb": {
        "document_name": "Mẫu 4.5: Báo cáo phản hồi về kết luận kiểm tra",
        "document_id": "MAU-04-5-BCPH",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "f067ba89-e738-4f14-a069-918a17bdc085": {
        "document_name": "Mẫu 05: Báo cáo tình hình thực hiện đấu thầu",
        "document_id": "MAU-05-BCDT",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # E-HSMT Xây lắp (Mẫu 3)
    # =========================================================================
    "f28f6b75-f794-4c60-8ebb-849b55adba7f": {
        "document_name": "Mẫu 3A: E-HSMT Xây lắp - 1 túi hồ sơ",
        "document_id": "MAU-03A-EHSMT-XL-1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "6595be7c-71ce-4114-8cfc-5cb52b1e8c9c": {
        "document_name": "Mẫu 3B: E-HSMT Xây lắp - 2 túi hồ sơ",
        "document_id": "MAU-03B-EHSMT-XL-2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "ad842823-40a3-4703-9844-e58ccf5a911e": {
        "document_name": "Mẫu 3C: E-HSMST Xây lắp - Sơ tuyển",
        "document_id": "MAU-03C-EHSMST-XL",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # E-HSMT Hàng hóa (Mẫu 4)
    # =========================================================================
    "b1c60b62-6546-4891-b5cd-1bc118b31867": {
        "document_name": "Mẫu 4A: E-HSMT Hàng hóa - 1 túi hồ sơ",
        "document_id": "MAU-04A-EHSMT-HH-1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "9a612d8c-573e-4d00-9654-99b0437158a6": {
        "document_name": "Mẫu 4B: E-HSMT Hàng hóa - 2 túi hồ sơ",
        "document_id": "MAU-04B-EHSMT-HH-2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "e59a6f70-d581-41f3-9af2-d84843877f51": {
        "document_name": "Mẫu 4C: E-HSMST Hàng hóa - Sơ tuyển",
        "document_id": "MAU-04C-EHSMST-HH",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # E-HSMT Phi tư vấn (Mẫu 5)
    # =========================================================================
    "e37b0537-89c9-448c-a05e-8ad8888c6ff2": {
        "document_name": "Mẫu 5A: E-HSMT Phi tư vấn - 1 túi hồ sơ",
        "document_id": "MAU-05A-EHSMT-PTV-1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "dbb351d3-fe88-4ead-b50c-d295e2855071": {
        "document_name": "Mẫu 5B: E-HSMT Phi tư vấn - 2 túi hồ sơ",
        "document_id": "MAU-05B-EHSMT-PTV-2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "682b6595-33d5-483d-9efe-b0ffcd726d18": {
        "document_name": "Mẫu 5C: E-HSMST Phi tư vấn - Sơ tuyển",
        "document_id": "MAU-05C-EHSMST-PTV",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # E-HSMT Tư vấn (Mẫu 6)
    # =========================================================================
    "ac9fa3dd-31f3-4b02-9f15-71a00e11f8e6": {
        "document_name": "Mẫu 6A: E-HSMT Tư vấn",
        "document_id": "MAU-06A-EHSMT-TV",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "3e554244-814d-424f-a795-3442e70cb2bc": {
        "document_name": "Mẫu 6B: E-HSMQT Tư vấn",
        "document_id": "MAU-06B-EHSMQT-TV",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "013eacb5-8332-46bf-af34-ef84c341847e": {
        "document_name": "Mẫu 6C: E-TVCN Tư vấn cá nhân",
        "document_id": "MAU-06C-ETVCN",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # E-HSMT EP qua mạng (Mẫu 7)
    # =========================================================================
    "30573b07-10cc-4f32-86f7-6845c296b50d": {
        "document_name": "Mẫu 7A: E-HSMT EP qua mạng - 1 túi hồ sơ",
        "document_id": "MAU-07A-EHSMT-EP-1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "557509b5-5682-4222-843c-18845dc3bc85": {
        "document_name": "Mẫu 7B: E-HSMT EP qua mạng - 2 túi hồ sơ",
        "document_id": "MAU-07B-EHSMT-EP-2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "7e0f2b44-2d0e-469f-864b-c41b827fce5c": {
        "document_name": "Mẫu 7C: E-HSMST EP - Sơ tuyển",
        "document_id": "MAU-07C-EHSMST-EP",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # E-HSMT EC (Mẫu 8)
    # =========================================================================
    "ab05e7ec-c60c-447b-891e-c04584f3099a": {
        "document_name": "Mẫu 8A: E-HSMT EC - 1 túi hồ sơ",
        "document_id": "MAU-08A-EHSMT-EC-1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "b03fede3-8a4c-4e61-9397-d195990d6baf": {
        "document_name": "Mẫu 8B: E-HSMT EC - 2 túi hồ sơ",
        "document_id": "MAU-08B-EHSMT-EC-2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "535e924a-3fb5-4e01-b5cf-bc5805fae902": {
        "document_name": "Mẫu 8C: E-HSMST EC - Sơ tuyển",
        "document_id": "MAU-08C-EHSMST-EC",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # E-HSMT PC (Mẫu 9)
    # =========================================================================
    "196dbebb-b691-498f-b2ad-fb60c94fa828": {
        "document_name": "Mẫu 9A: E-HSMT PC - 1 túi hồ sơ",
        "document_id": "MAU-09A-EHSMT-PC-1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "55fb2600-50c8-4209-be9a-d8cadb3d0edb": {
        "document_name": "Mẫu 9B: E-HSMT PC - 2 túi hồ sơ",
        "document_id": "MAU-09B-EHSMT-PC-2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "21693be4-62fe-46a5-8141-bad12f7af1d1": {
        "document_name": "Mẫu 9C: E-HSMST PC - Sơ tuyển",
        "document_id": "MAU-09C-EHSMST-PC",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # E-HSMT EPC (Mẫu 10)
    # =========================================================================
    "39bd0512-3031-4328-97e4-c4e1644a1fac": {
        "document_name": "Mẫu 10A: E-HSMT EPC - 1 túi hồ sơ",
        "document_id": "MAU-10A-EHSMT-EPC-1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "12116ad7-8303-4705-a1f6-3cfb40f66538": {
        "document_name": "Mẫu 10B: E-HSMT EPC - 2 túi hồ sơ",
        "document_id": "MAU-10B-EHSMT-EPC-2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "5fa0925e-292e-43e6-aa2e-d9f9a373aba7": {
        "document_name": "Mẫu 10C: E-HSMST EPC - Sơ tuyển",
        "document_id": "MAU-10C-EHSMST-EPC",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # E-HSMT Máy đặt máy mượn (Mẫu 11)
    # =========================================================================
    "e08e9e44-5988-4ecb-887a-2bd864045fd2": {
        "document_name": "Mẫu 11A: E-HSMT Máy đặt máy mượn - 1 túi hồ sơ",
        "document_id": "MAU-11A-EHSMT-MDMM-1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "57403184-fd16-454b-9d7a-e2662db8239f": {
        "document_name": "Mẫu 11B: E-HSMT Máy đặt máy mượn - 2 túi hồ sơ",
        "document_id": "MAU-11B-EHSMT-MDMM-2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # CGTT Rút gọn (Mẫu 12)
    # =========================================================================
    "fa4ff155-2ea4-47f2-a7aa-35281e4290ac": {
        "document_name": "Mẫu 12C: CGTT Hàng hóa - Rút gọn",
        "document_id": "MAU-12C-CGTT-HH-RG",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "463c589a-dbe4-4886-955d-633c7ffbba07": {
        "document_name": "Mẫu 12D: CGTT Phi tư vấn - Rút gọn",
        "document_id": "MAU-12D-CGTT-PTV-RG",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "b1379de0-3b35-49a7-b6d9-f8e982b06a50": {
        "document_name": "Mẫu 12E: CGTT Xây lắp - Rút gọn",
        "document_id": "MAU-12E-CGTT-XL-RG",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "f21f23c2-1c3b-4482-b79f-08e82fdd349d": {
        "document_name": "Mẫu 12G: CGTT Rút gọn - Xử lý tình huống",
        "document_id": "MAU-12G-CGTT-XLTH",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # Mua sắm trực tuyến (Mẫu 13)
    # =========================================================================
    "893adf06-985b-4637-a181-3337de3a8628": {
        "document_name": "Mẫu 13: Mua sắm trực tuyến",
        "document_id": "MAU-13-MSTT",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # BCĐG TBYT (Mẫu 14)
    # =========================================================================
    "df1833be-4682-4c11-8b18-66bdbd337b50": {
        "document_name": "Mẫu 14A: BCĐG PTV/HH/XL/TBYT - CGTT quy trình 1, 1 túi",
        "document_id": "MAU-14A-BCDG-TBYT-1T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "c1202618-e8f2-401a-af57-7f1524babb6e": {
        "document_name": "Mẫu 14B: BCĐG PTV/HH/TBYT - Quy trình 2, 1 túi",
        "document_id": "MAU-14B-BCDG-TBYT-QT2",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "095609d9-ce48-4b18-b917-9582c745ce8c": {
        "document_name": "Mẫu 14C: BCĐG HH/XL/PTV/TBYT - 2 túi hồ sơ",
        "document_id": "MAU-14C-BCDG-TBYT-2T",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    "85e0dc80-ea6d-4e99-b553-e0c9e1293957": {
        "document_name": "Mẫu 14D: BCĐG Tư vấn",
        "document_id": "MAU-14D-BCDG-TV",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # Phụ lục (Mẫu 15)
    # =========================================================================
    "0f9cb0a9-9f7a-41aa-93a9-1be825065c64": {
        "document_name": "Phụ lục 15: Các mẫu tờ trình và biên bản",
        "document_id": "PHU-LUC-15",
        "document_type": "bidding",
        "category": "Mẫu biểu đấu thầu",
    },
    # =========================================================================
    # TEST DATA - Batch 1 (có thể xóa sau khi cleanup)
    # Đây là dữ liệu test với document_type = file extension
    # =========================================================================
    "bcbd8dea-86a7-452f-8d05-76c18266dfd4": {
        "document_name": "[TEST] Nghị định mẫu 1",
        "document_id": "TEST-ND-001",
        "document_type": "decree",
        "category": "Nghị định",
        "filename": "test_decree_1.pdf",
        "_is_test_data": True,
    },
    "78379d25-3ea7-4791-bc64-69125d57ba04": {
        "document_name": "[TEST] Thông tư mẫu 2",
        "document_id": "TEST-TT-002",
        "document_type": "circular",
        "category": "Thông tư",
        "filename": "test_circular_2.pdf",
        "_is_test_data": True,
    },
    "d4ade997-041e-4092-abba-a52aff9f51d8": {
        "document_name": "[TEST] Nghị định mẫu 3",
        "document_id": "TEST-ND-003",
        "document_type": "decree",
        "category": "Nghị định",
        "filename": "test_decree_3.pdf",
        "_is_test_data": True,
    },
    "ec21facc-55cf-496a-807a-5eea15dee784": {
        "document_name": "[TEST] Thông tư mẫu 4",
        "document_id": "TEST-TT-004",
        "document_type": "circular",
        "category": "Thông tư",
        "filename": "test_circular_4.pdf",
        "_is_test_data": True,
    },
    "f4f936c2-cec3-4fec-a038-fdbb4e87e7ce": {
        "document_name": "[TEST] Nghị định mẫu 5",
        "document_id": "TEST-ND-005",
        "document_type": "decree",
        "category": "Nghị định",
        "filename": "test_decree_5.pdf",
        "_is_test_data": True,
    },
    "8bbbae1c-92e4-4ee6-8d84-3a5feee7dec6": {
        "document_name": "[TEST] Luật mẫu 6",
        "document_id": "TEST-LUAT-006",
        "document_type": "law",
        "category": "Luật chính",
        "filename": "test_law_6.pdf",
        "_is_test_data": True,
    },
    "efbd31fb-d760-4860-a122-396c3277c6ad": {
        "document_name": "[TEST] Nghị định mẫu 7",
        "document_id": "TEST-ND-007",
        "document_type": "decree",
        "category": "Nghị định",
        "filename": "test_decree_7.pdf",
        "_is_test_data": True,
    },
    "1756a678-8a18-4684-aed9-846fc6a844e2": {
        "document_name": "[TEST] Mẫu báo cáo 8",
        "document_id": "TEST-BC-008",
        "document_type": "template",
        "category": "Mẫu báo cáo",
        "filename": "test_report_8.pdf",
        "_is_test_data": True,
    },
    "551af345-d720-4f6c-bc95-4ae28ddc57b1": {
        "document_name": "[TEST] Mẫu báo cáo 9",
        "document_id": "TEST-BC-009",
        "document_type": "template",
        "category": "Mẫu báo cáo",
        "filename": "test_report_9.pdf",
        "_is_test_data": True,
    },
    "91e64b05-e0a5-40a9-b3c0-50d0c6501b95": {
        "document_name": "[TEST] Nghị định mẫu 10",
        "document_id": "TEST-ND-010",
        "document_type": "decree",
        "category": "Nghị định",
        "filename": "test_decree_10.pdf",
        "_is_test_data": True,
    },
    "275227ac-2a33-4a92-a117-f9ac927f8cdb": {
        "document_name": "[TEST] Mẫu báo cáo 11",
        "document_id": "TEST-BC-011",
        "document_type": "template",
        "category": "Mẫu báo cáo",
        "filename": "test_report_11.pdf",
        "_is_test_data": True,
    },
    "fc7c4f36-b198-4520-a15e-7afa92e2122c": {
        "document_name": "[TEST] Mẫu báo cáo 12",
        "document_id": "TEST-BC-012",
        "document_type": "template",
        "category": "Mẫu báo cáo",
        "filename": "test_report_12.pdf",
        "_is_test_data": True,
    },
    "54681373-89c6-40c4-8351-9b2a340aa81d": {
        "document_name": "[TEST] Luật mẫu 13",
        "document_id": "TEST-LUAT-013",
        "document_type": "law",
        "category": "Luật chính",
        "filename": "test_law_13.pdf",
        "_is_test_data": True,
    },
    "08b7bffa-287e-4a7c-9ea8-7115f35c9535": {
        "document_name": "[TEST] Luật mẫu 14",
        "document_id": "TEST-LUAT-014",
        "document_type": "law",
        "category": "Luật chính",
        "filename": "test_law_14.pdf",
        "_is_test_data": True,
    },
    "ac692764-1717-4035-9810-b9ef0e875dbd": {
        "document_name": "[TEST] Thông tư mẫu 15",
        "document_id": "TEST-TT-015",
        "document_type": "circular",
        "category": "Thông tư",
        "filename": "test_circular_15.pdf",
        "_is_test_data": True,
    },
    # =========================================================================
    # TEST DATA - Batch 2 (duplicates with different UUIDs)
    # =========================================================================
    "caf7dc6d-34f5-44a9-b511-e89cab6ba88a": {
        "document_name": "[TEST] Nghị định mẫu 1B",
        "document_id": "TEST-ND-001B",
        "document_type": "decree",
        "category": "Nghị định",
        "filename": "test_decree_1b.pdf",
        "_is_test_data": True,
    },
    "fe661b25-2b18-45e2-896a-06d8847cf9f4": {
        "document_name": "[TEST] Luật mẫu 2B",
        "document_id": "TEST-LUAT-002B",
        "document_type": "law",
        "category": "Luật chính",
        "filename": "test_law_2b.pdf",
        "_is_test_data": True,
    },
    "4f9bc77e-d960-4f5c-a7e5-e16b07db1195": {
        "document_name": "[TEST] Thông tư mẫu 3B",
        "document_id": "TEST-TT-003B",
        "document_type": "circular",
        "category": "Thông tư",
        "filename": "test_circular_3b.pdf",
        "_is_test_data": True,
    },
    "3c300c13-3441-45c8-b5a2-52513d79a63c": {
        "document_name": "[TEST] Luật mẫu 4B",
        "document_id": "TEST-LUAT-004B",
        "document_type": "law",
        "category": "Luật chính",
        "filename": "test_law_4b.pdf",
        "_is_test_data": True,
    },
    "772d4402-1bcf-4bd0-8232-c3b625b47028": {
        "document_name": "[TEST] Mẫu báo cáo 5B",
        "document_id": "TEST-BC-005B",
        "document_type": "template",
        "category": "Mẫu báo cáo",
        "filename": "test_report_5b.pdf",
        "_is_test_data": True,
    },
    "11f652af-e7ff-49ad-8b66-bd3125560924": {
        "document_name": "[TEST] Quyết định mẫu 6B",
        "document_id": "TEST-QD-006B",
        "document_type": "decision",
        "category": "Quyết định",
        "filename": "test_decision_6b.pdf",
        "_is_test_data": True,
    },
    "6b7f8a7a-db51-4d1a-9867-9ab3144ea768": {
        "document_name": "[TEST] Quyết định mẫu 7B",
        "document_id": "TEST-QD-007B",
        "document_type": "decision",
        "category": "Quyết định",
        "filename": "test_decision_7b.pdf",
        "_is_test_data": True,
    },
    "832f8586-fa7c-4155-a25d-8b9bb28e7f06": {
        "document_name": "[TEST] Luật mẫu 8B",
        "document_id": "TEST-LUAT-008B",
        "document_type": "law",
        "category": "Luật chính",
        "filename": "test_law_8b.pdf",
        "_is_test_data": True,
    },
    "c172a74b-11f0-433d-9c3d-dba691a45380": {
        "document_name": "[TEST] Quyết định mẫu 9B",
        "document_id": "TEST-QD-009B",
        "document_type": "decision",
        "category": "Quyết định",
        "filename": "test_decision_9b.pdf",
        "_is_test_data": True,
    },
    "9b841135-1927-468a-ace9-87142b28599a": {
        "document_name": "[TEST] Thông tư mẫu 10B",
        "document_id": "TEST-TT-010B",
        "document_type": "circular",
        "category": "Thông tư",
        "filename": "test_circular_10b.pdf",
        "_is_test_data": True,
    },
    "c63d5b69-32aa-4ed3-8bb5-1d06fbc565f1": {
        "document_name": "[TEST] Quyết định mẫu 11B",
        "document_id": "TEST-QD-011B",
        "document_type": "decision",
        "category": "Quyết định",
        "filename": "test_decision_11b.pdf",
        "_is_test_data": True,
    },
    "0681f17a-df70-46e4-9f3e-bd54bcb0aa58": {
        "document_name": "[TEST] Nghị định mẫu 12B",
        "document_id": "TEST-ND-012B",
        "document_type": "decree",
        "category": "Nghị định",
        "filename": "test_decree_12b.pdf",
        "_is_test_data": True,
    },
    "1eb44fc1-827b-4f25-9314-97f79bd7b1c1": {
        "document_name": "[TEST] Quyết định mẫu 13B",
        "document_id": "TEST-QD-013B",
        "document_type": "decision",
        "category": "Quyết định",
        "filename": "test_decision_13b.pdf",
        "_is_test_data": True,
    },
    "18b9121c-8f3d-4a9a-856f-01811e5ee1d2": {
        "document_name": "[TEST] Luật mẫu 14B",
        "document_id": "TEST-LUAT-014B",
        "document_type": "law",
        "category": "Luật chính",
        "filename": "test_law_14b.pdf",
        "_is_test_data": True,
    },
    "86d19913-b0ca-4cdc-b4ba-2b9d874d46e8": {
        "document_name": "[TEST] Quyết định mẫu 15B",
        "document_id": "TEST-QD-015B",
        "document_type": "decision",
        "category": "Quyết định",
        "filename": "test_decision_15b.pdf",
        "_is_test_data": True,
    },
}


def get_document_metadata(doc_id: str) -> dict:
    """
    Get the correct metadata for a document by its UUID.

    Args:
        doc_id: Document UUID string

    Returns:
        Dictionary with correct metadata, or None if not found
    """
    return DOCUMENT_NAME_MAP.get(doc_id)


def get_all_mapped_ids() -> list:
    """Get list of all document IDs that have manual mappings."""
    return list(DOCUMENT_NAME_MAP.keys())


# Statistics
if __name__ == "__main__":
    print(f"Total documents mapped: {len(DOCUMENT_NAME_MAP)}")

    # Count by type
    by_type = {}
    for doc_id, meta in DOCUMENT_NAME_MAP.items():
        t = meta.get("document_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    print("\nBy document type:")
    for t, count in sorted(by_type.items()):
        print(f"  {t}: {count}")
